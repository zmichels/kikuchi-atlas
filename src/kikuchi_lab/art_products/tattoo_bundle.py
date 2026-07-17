"""Strict preflight and atomic publication of the primary Ice tattoo bundle."""

from __future__ import annotations

import errno
import hashlib
import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
    _write_bytes,
    _write_json,
)
from kikuchi_lab.model.identity import plain_data, stable_id

from .catalog_bundle import _validate_catalog_members
from .contracts import ArtBandCatalog, TattooGeometry
from .frozen_selection import FrozenTattooSelection, bind_frozen_tattoo_selection
from .tattoo_recipe import TattooRecipe
from .tattoo_selection import TattooSelection, select_tattoo_paths
from .tattoo_vector import (
    _endpoint_to_polyline_distance,
    _paths_cross,
    _polyline_distance,
    _STROKE_CLIP_ID,
    _stroke_clip_evidence,
    build_tattoo_geometry,
    render_primary_tattoo,
    validate_tattoo_geometry,
)


DISCLAIMER_TEXT = (
    "This science-art is not medical guidance or a skin-approved stencil and "
    "requires qualified tattoo-artist review before any use on skin.\n"
)
_PRIMARY_RENDER_NAMES = {
    "primary.svg": "ice-ih-tattoo-primary.svg",
    "primary.pdf": "ice-ih-tattoo-primary.pdf",
    "mockup.png": "ice-ih-tattoo-mockup.png",
    "stencil.png": "ice-ih-tattoo-stencil.png",
}
_PAYLOAD_ORDER = (
    "ice-ih-tattoo-primary.svg",
    "ice-ih-tattoo-primary.pdf",
    "ice-ih-tattoo-mockup.png",
    "ice-ih-tattoo-stencil.png",
    "tattoo-recipe.json",
    "art-band-catalog.json",
    "band-selection-ledger.json",
    "path-geometry.json",
    "stroke-gap-diagnostic.json",
    "tattoo-artist-review.txt",
)
_MIN_EDGE_GAP_MM = 1.5
_MIN_ENDPOINT_CLEARANCE_MM = 2.0
_PDF_MEDIA_BOX = re.compile(
    rb"/MediaBox\s*\[\s*0(?:\.0+)?\s+0(?:\.0+)?\s+"
    rb"([0-9.]+)\s+([0-9.]+)\s*\]"
)
_PDF_DIMENSION_TOLERANCE_POINTS = 0.02 * 72.0 / 25.4


@dataclass(frozen=True)
class TattooBundleResult:
    """Published identity and location for one immutable tattoo bundle."""

    run_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class _ValidatedPayload:
    run_identity: dict[str, object]
    files: dict[str, bytes | object]
    payload_order: tuple[str, ...]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _selection_identity(selection: TattooSelection) -> str:
    return stable_id(
        "tattoo-selection",
        {
            "catalog_id": selection.catalog_id,
            "recipe_id": selection.recipe_id,
            "orientation_id": selection.orientation_id,
            "selected_paths": [
                path.identity_dict() for path in selection.selected_paths
            ],
        },
    )


def _selection_snapshot(selection: TattooSelection) -> dict[str, object]:
    return {
        "selection_id": selection.selection_id,
        "catalog_id": selection.catalog_id,
        "recipe_id": selection.recipe_id,
        "orientation_id": selection.orientation_id,
        "selected_paths": [
            {
                **path.identity_dict(),
                "normal_sample": path.normal_sample.tolist(),
                "center_trace": path.center_trace.tolist(),
            }
            for path in selection.selected_paths
        ],
        "ledger": plain_data(selection.ledger),
    }


def _geometry_identity(geometry: TattooGeometry) -> str:
    return stable_id("tattoo-geometry", geometry.to_dict())


def _validate_svg(payload: bytes, *, boundary_id: str) -> None:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        raise ValueError("primary SVG is not valid XML") from None
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("primary SVG root must be svg")
    children = list(root)
    definitions = [
        child for child in children if child.tag == "{http://www.w3.org/2000/svg}defs"
    ]
    if len(definitions) != 1 or children[0] is not definitions[0]:
        raise ValueError("primary SVG must place one stroke clip definition before artwork")
    definition_children = list(definitions[0])
    if len(definition_children) != 1:
        raise ValueError("primary SVG must contain one exact stroke clip definition")
    clip_path = definition_children[0]
    clip_children = list(clip_path)
    if (
        clip_path.tag != "{http://www.w3.org/2000/svg}clipPath"
        or clip_path.attrib
        != {
            "clipPathUnits": "userSpaceOnUse",
            "id": _STROKE_CLIP_ID,
        }
        or len(clip_children) != 1
        or clip_children[0].tag != "{http://www.w3.org/2000/svg}circle"
        or clip_children[0].attrib
        != {"cx": "72.500000", "cy": "72.500000", "r": "63.800000"}
    ):
        raise ValueError("primary SVG stroke clip does not match the exact 63.8 mm disc")

    artwork = children[1:]
    paths = artwork[:11]
    if (
        len(artwork) != 12
        or any(path.tag != "{http://www.w3.org/2000/svg}path" for path in paths)
        or artwork[-1].tag != "{http://www.w3.org/2000/svg}circle"
    ):
        raise ValueError(
            "primary SVG must contain exactly 11 paths followed by one boundary circle"
        )
    if any(
        element.attrib.get("stroke") != "#000000"
        or element.attrib.get("fill") != "none"
        for element in artwork
    ):
        raise ValueError("primary SVG must use only black ink")
    if artwork[-1].attrib.get("id") != boundary_id:
        raise ValueError("primary SVG boundary ID does not match geometry")
    if any(
        path.attrib.get("clip-path") != f"url(#{_STROKE_CLIP_ID})" for path in paths
    ):
        raise ValueError("every primary SVG path must use the canonical stroke clip")
    if any(
        path.attrib.get("stroke-linecap") != "round"
        or path.attrib.get("stroke-linejoin") != "round"
        for path in paths
    ):
        raise ValueError("primary SVG paths must use rounded caps and joins")


def _validate_pdf(payload: bytes) -> None:
    if not payload.startswith(b"%PDF-"):
        raise ValueError("primary PDF has an invalid file signature")
    match = _PDF_MEDIA_BOX.search(payload)
    if match is None:
        raise ValueError("primary PDF lacks a physical media box")
    expected_points = 145.0 * 72.0 / 25.4
    dimensions = (float(match.group(1)), float(match.group(2)))
    differences = [abs(value - expected_points) for value in dimensions]
    if any(
        difference > _PDF_DIMENSION_TOLERANCE_POINTS
        and not math.isclose(
            difference,
            _PDF_DIMENSION_TOLERANCE_POINTS,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        for difference in differences
    ):
        raise ValueError("primary PDF must have an exact 145 mm square page")


def _validate_png(
    payload: bytes,
    *,
    name: str,
    background: tuple[int, int, int],
) -> None:
    try:
        with Image.open(BytesIO(payload)) as source:
            source.load()
            if source.format != "PNG" or source.size != (1713, 1713):
                raise ValueError(f"{name} must be a 1713 px square PNG")
            dpi = source.info.get("dpi")
            if (
                not isinstance(dpi, tuple)
                or len(dpi) != 2
                or any(abs(float(value) - 300.0) > 0.01 for value in dpi)
            ):
                raise ValueError(f"{name} must record exact 300 dpi output")
            colors = source.convert("RGB").getcolors(maxcolors=3)
            pixels = np.asarray(source.convert("RGB"))
    except (OSError, ValueError) as error:
        if isinstance(error, ValueError):
            raise
        raise ValueError(f"{name} is not a readable PNG") from None
    expected_colors = {background, (0, 0, 0)}
    if colors is None or {color for _, color in colors} != expected_colors:
        raise ValueError(f"{name} palette must contain only black and its background")
    black_y, black_x = np.nonzero(np.all(pixels == 0, axis=2))
    if black_x.size == 0:
        raise ValueError(f"{name} must contain black tattoo geometry")
    scale = pixels.shape[1] / 145.0
    black_x_mm = (black_x.astype(np.float64) + 0.5) / scale
    black_y_mm = (black_y.astype(np.float64) + 0.5) / scale
    radial_extent_mm = float(
        np.max(np.hypot(black_x_mm - 72.5, black_y_mm - 72.5))
    )
    half_pixel_diagonal_mm = math.sqrt(2.0) / (2.0 * scale)
    if radial_extent_mm > 66.0 + half_pixel_diagonal_mm:
        raise ValueError(f"{name} black pixels escape the 66.0 mm outer radius")


def _validate_rendered(
    rendered: Mapping[str, bytes],
    expected: Mapping[str, bytes],
    *,
    boundary_id: str,
) -> dict[str, bytes]:
    if not isinstance(rendered, Mapping) or set(rendered) != set(_PRIMARY_RENDER_NAMES):
        raise ValueError("primary rendered artifacts differ from the exact inventory")
    copied: dict[str, bytes] = {}
    for name in _PRIMARY_RENDER_NAMES:
        payload = rendered[name]
        if not isinstance(payload, bytes) or not payload:
            raise ValueError(f"{name} must contain non-empty bytes")
        copied[name] = payload
    _validate_svg(copied["primary.svg"], boundary_id=boundary_id)
    _validate_pdf(copied["primary.pdf"])
    _validate_png(
        copied["mockup.png"],
        name="primary mockup",
        background=(216, 181, 154),
    )
    _validate_png(
        copied["stencil.png"],
        name="primary stencil",
        background=(255, 255, 255),
    )
    if copied != dict(expected):
        raise ValueError("rendered primary artifacts do not match rebuilt geometry")
    return copied


def _gap_diagnostic(geometry: TattooGeometry) -> dict[str, object]:
    stroke_clip = _stroke_clip_evidence(geometry)
    stroke_containment = (
        "passed"
        if stroke_clip["max_post_clip_stroke_radius_mm"]
        <= stroke_clip["outer_boundary_radius_mm"]
        else "failed"
    )
    if stroke_containment != "passed":
        raise ValueError("clipped stroke footprint escapes the projection boundary")
    noncrossing: list[dict[str, object]] = []
    for first_index, first in enumerate(geometry.paths):
        for second in geometry.paths[first_index + 1 :]:
            if _paths_cross(first.points_mm, second.points_mm):
                continue
            edge_gap = (
                _polyline_distance(first.points_mm, second.points_mm)
                - 0.5 * first.width_mm
                - 0.5 * second.width_mm
            )
            endpoint_clearances = [
                _endpoint_to_polyline_distance(endpoint, unrelated) - 0.5 * width
                for endpoint, unrelated, width in (
                    (first.points_mm[0], second.points_mm, second.width_mm),
                    (first.points_mm[-1], second.points_mm, second.width_mm),
                    (second.points_mm[0], first.points_mm, first.width_mm),
                    (second.points_mm[-1], first.points_mm, first.width_mm),
                )
            ]
            noncrossing.append(
                {
                    "member_ids": [first.member_id, second.member_id],
                    "edge_gap_mm": edge_gap,
                    "minimum_endpoint_clearance_mm": min(endpoint_clearances),
                }
            )
    content: dict[str, object] = {
        "schema_version": 1,
        "geometry_id": geometry.geometry_id,
        "boundary_id": geometry.boundary.boundary_id,
        "boundary": geometry.boundary.to_dict(),
        "validation": {
            "status": "passed",
            "minimum_noncrossing_edge_gap_mm": _MIN_EDGE_GAP_MM,
            "minimum_endpoint_clearance_mm": _MIN_ENDPOINT_CLEARANCE_MM,
            "complete_hemisphere_boundary": stroke_containment,
            "boundary_endpoint_contact": "passed",
            "stroke_containment": stroke_containment,
        },
        "stroke_clip": stroke_clip,
        "observed": {
            "noncrossing_pair_count": len(noncrossing),
            "minimum_noncrossing_edge_gap_mm": (
                min(record["edge_gap_mm"] for record in noncrossing)
                if noncrossing
                else None
            ),
            "minimum_endpoint_clearance_mm": (
                min(record["minimum_endpoint_clearance_mm"] for record in noncrossing)
                if noncrossing
                else None
            ),
        },
        "paths": [
            {
                "path_id": path.path_id,
                "member_id": path.member_id,
                "tier": path.tier,
                "width_mm": path.width_mm,
                "points_sha256": path.points_sha256,
            }
            for path in geometry.paths
        ],
        "noncrossing_pairs": noncrossing,
    }
    return {
        "diagnostic_id": stable_id("tattoo-stroke-gap-diagnostic", content),
        **content,
    }


def _validated_payload(
    *,
    catalog: ArtBandCatalog,
    recipe: TattooRecipe,
    selection: TattooSelection,
    geometry: TattooGeometry,
    rendered: Mapping[str, bytes],
    treatment: str,
    disclaimer: str,
    frozen_manifest: FrozenTattooSelection | None = None,
) -> _ValidatedPayload:
    for value, expected, name in (
        (catalog, ArtBandCatalog, "catalog"),
        (recipe, TattooRecipe, "recipe"),
        (selection, TattooSelection, "selection"),
        (geometry, TattooGeometry, "geometry"),
    ):
        if not isinstance(value, expected):
            raise TypeError(f"{name} must be a {expected.__name__}")
    if treatment != "primary":
        if treatment == "graywash":
            raise ValueError("graywash requires accepted primary geometry")
        raise ValueError("tattoo treatment must be primary")
    if disclaimer != DISCLAIMER_TEXT:
        raise ValueError(
            "tattoo-artist disclaimer is required and must match the approved text"
        )

    if catalog.catalog_id != stable_id("art-band-catalog", catalog.to_dict()):
        raise ValueError("catalog_id does not match catalog content")
    if catalog.eligibility_min_weight != 0.08:
        raise ValueError("tattoo catalog threshold must be exactly 0.08")
    _validate_catalog_members(catalog)

    if selection.selection_id != _selection_identity(selection):
        raise ValueError("selection_id does not match selection content")
    if selection.catalog_id != catalog.catalog_id:
        raise ValueError("selection catalog_id does not match the catalog")
    if selection.recipe_id != recipe.recipe_id:
        raise ValueError("selection recipe_id does not match the tattoo recipe")
    if selection.orientation_id != recipe.orientation.orientation_id:
        raise ValueError("selection orientation does not match the tattoo recipe")
    if len(selection.selected_paths) != 11:
        raise ValueError("tattoo selection must contain exactly 11 paths")

    if geometry.boundary.boundary_id != stable_id(
        "tattoo-boundary", geometry.boundary.identity_dict()
    ):
        raise ValueError("boundary_id does not match boundary content")
    if geometry.geometry_id != _geometry_identity(geometry):
        raise ValueError("geometry_id does not match geometry content")
    if geometry.catalog_id != catalog.catalog_id:
        raise ValueError("geometry catalog_id does not match the catalog")
    if geometry.orientation_id != recipe.orientation.orientation_id:
        raise ValueError("geometry orientation does not match the tattoo recipe")
    validate_tattoo_geometry(geometry)

    if frozen_manifest is None:
        expected_selection = select_tattoo_paths(catalog, recipe)
    else:
        expected_selection = bind_frozen_tattoo_selection(
            catalog,
            recipe,
            frozen_manifest,
        )
    if _selection_snapshot(selection) != _selection_snapshot(expected_selection):
        raise ValueError("selection content does not match strict catalog selection")
    expected_geometry = build_tattoo_geometry(expected_selection, recipe)
    if geometry.boundary.to_dict() != expected_geometry.boundary.to_dict():
        raise ValueError("projection boundary does not match rebuilt geometry")
    if [path.width_mm for path in geometry.paths] != [
        path.width_mm for path in expected_geometry.paths
    ]:
        raise ValueError("ordered path widths do not match rebuilt geometry")
    if [path.points_sha256 for path in geometry.paths] != [
        path.points_sha256 for path in expected_geometry.paths
    ]:
        raise ValueError("path coordinate hashes do not match rebuilt geometry")
    if geometry.to_dict() != expected_geometry.to_dict():
        raise ValueError("geometry content does not match rebuilt geometry")

    rendered_payloads = _validate_rendered(
        rendered,
        render_primary_tattoo(expected_geometry),
        boundary_id=expected_geometry.boundary.boundary_id,
    )
    recipe_snapshot = {"recipe_id": recipe.recipe_id, "content": recipe.to_dict()}
    catalog_snapshot = {"catalog_id": catalog.catalog_id, "content": catalog.to_dict()}
    selection_snapshot = _selection_snapshot(selection)
    geometry_snapshot = {
        "geometry_id": geometry.geometry_id,
        "content": geometry.to_dict(),
    }
    diagnostic = _gap_diagnostic(geometry)
    disclaimer_bytes = disclaimer.encode("utf-8")
    target_rendered = {
        target: rendered_payloads[source]
        for source, target in _PRIMARY_RENDER_NAMES.items()
    }
    run_identity = {
        "schema_version": 1,
        "catalog_id": catalog.catalog_id,
        "recipe_id": recipe.recipe_id,
        "selection_id": selection.selection_id,
        "geometry_id": geometry.geometry_id,
        "boundary_id": geometry.boundary.boundary_id,
        "treatment": treatment,
        "diagnostic_id": diagnostic["diagnostic_id"],
        "rendered_sha256": {
            name: _sha256_bytes(payload)
            for name, payload in target_rendered.items()
        },
        "disclaimer_sha256": _sha256_bytes(disclaimer_bytes),
    }
    if frozen_manifest is not None:
        run_identity["frozen_manifest_id"] = frozen_manifest.manifest_id
    files: dict[str, bytes | object] = {
        **target_rendered,
        "tattoo-recipe.json": recipe_snapshot,
        "art-band-catalog.json": catalog_snapshot,
    }
    if frozen_manifest is not None:
        files["frozen-selection-manifest.json"] = {
            "manifest_id": frozen_manifest.manifest_id,
            "content": frozen_manifest.to_dict(),
        }
    files.update(
        {
            "band-selection-ledger.json": selection_snapshot,
            "path-geometry.json": geometry_snapshot,
            "stroke-gap-diagnostic.json": diagnostic,
            "tattoo-artist-review.txt": disclaimer_bytes,
        }
    )
    payload_order = tuple(files)
    expected_order = (
        _PAYLOAD_ORDER
        if frozen_manifest is None
        else _PAYLOAD_ORDER[:6]
        + ("frozen-selection-manifest.json",)
        + _PAYLOAD_ORDER[6:]
    )
    if payload_order != expected_order:
        raise AssertionError("tattoo bundle payload order differs from the canonical inventory")
    return _ValidatedPayload(
        run_identity=run_identity,
        files=files,
        payload_order=payload_order,
    )


def _write_contents(
    root: Path,
    payload: _ValidatedPayload,
) -> dict[str, dict[str, object]]:
    for name, content in payload.files.items():
        path = root / name
        if isinstance(content, bytes):
            _write_bytes(path, content)
        else:
            _write_json(path, content)
    return {
        name: {
            "bytes": (root / name).stat().st_size,
            "sha256": _sha256(root / name),
        }
        for name in payload.payload_order
    }


def _publish_validated_payload(
    output_root: str | Path,
    *,
    run_id: str,
    payload: _ValidatedPayload,
) -> tuple[Path, str]:
    """Publish an already validated payload without replacing an existing run."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    ownership = root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}") from None
        raise PartialBundleError(
            f"same-run publication already in progress: {ownership}"
        ) from None

    try:
        _fsync_directory(root)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        existing_partials = sorted(root.glob(f".{run_id}.partial-*"))
        if existing_partials:
            raise PartialBundleError(
                f"partial bundle already exists: {existing_partials[0]}"
            )
        partial = root / f".{run_id}.partial-{uuid4().hex}"
        try:
            partial.mkdir()
        except FileExistsError:
            raise PartialBundleError(f"partial bundle already exists: {partial}") from None

        files = _write_contents(partial, payload)
        manifest_path = partial / "manifest.json"
        _write_json(
            manifest_path,
            {
                "schema_version": 1,
                "run_id": run_id,
                "run_identity": payload.run_identity,
                "files": files,
            },
        )
        manifest_sha256 = _sha256(manifest_path)
        _fsync_directory_tree(partial)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        try:
            _promote_directory_no_replace(partial, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise BundleExistsError(
                    f"completed bundle already exists: {completed}"
                ) from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return completed, manifest_sha256
    finally:
        ownership.rmdir()
        _fsync_directory(root)


def write_tattoo_bundle(
    output_root: str | Path,
    *,
    catalog: ArtBandCatalog,
    recipe: TattooRecipe,
    selection: TattooSelection,
    geometry: TattooGeometry,
    rendered: Mapping[str, bytes],
    treatment: str,
    disclaimer: str,
    frozen_manifest: FrozenTattooSelection | None = None,
) -> TattooBundleResult:
    """Preflight completely, then atomically publish one primary tattoo bundle."""
    payload = _validated_payload(
        catalog=catalog,
        recipe=recipe,
        selection=selection,
        geometry=geometry,
        rendered=rendered,
        treatment=treatment,
        disclaimer=disclaimer,
        frozen_manifest=frozen_manifest,
    )
    run_id = stable_id("ice-tattoo-run", payload.run_identity)
    completed, manifest_sha256 = _publish_validated_payload(
        output_root,
        run_id=run_id,
        payload=payload,
    )
    return TattooBundleResult(
        run_id=run_id,
        path=completed,
        manifest_sha256=manifest_sha256,
    )


__all__ = [
    "DISCLAIMER_TEXT",
    "TattooBundleResult",
    "write_tattoo_bundle",
]

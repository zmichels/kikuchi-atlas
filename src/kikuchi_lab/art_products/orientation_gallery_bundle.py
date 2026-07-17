"""Immutable, zero-master publication for one orientation-gallery cell."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.artifacts import BundleExistsError
from kikuchi_lab.model.identity import canonical_json, stable_id

from .catalog_bundle import _validate_catalog_members
from .contracts import ArtBandCatalog, TattooGeometry
from .hemisphere_recipe import HemisphereCompositionRecipe, HemisphereTreatment
from .orientation_gallery_recipe import OrientationGalleryVariant
from .tattoo_bundle import (
    _ValidatedPayload,
    _geometry_identity,
    _publish_validated_payload,
    _selection_identity,
    _selection_snapshot,
    _sha256_bytes,
    _validate_png,
    _validate_svg,
)
from .tattoo_selection import TattooSelection
from .tattoo_vector import build_tattoo_geometry, render_primary_tattoo, validate_tattoo_geometry
from kikuchi_lab.kinematical.reflector_parity import ReflectorParityReport


_PHASE_ORDER = ("ice-ih", "forsterite", "quartz", "zircon", "titanite")
_SCIENTIFIC_CLAIM = (
    "Scientific claim: presentation-only science art derived from retained "
    "orientation-independent direct-reflector evidence. This gallery rotates "
    "crystal normals into the recorded crystal_to_sample frame before drawing "
    "the stereographic geometry. No master-pattern simulation was calculated "
    "for this gallery cell; simulation_count is 0.\n"
)


@dataclass(frozen=True)
class OrientationGalleryCell:
    """One fully preflighted standard-width gallery cell and its evidence."""

    phase_slug: str
    variant: OrientationGalleryVariant
    treatment: HemisphereTreatment
    catalog: ArtBandCatalog
    composition: HemisphereCompositionRecipe
    selection: TattooSelection
    geometry: TattooGeometry
    parity_report: ReflectorParityReport
    frozen_reference_id: str | None = None

    def __post_init__(self) -> None:
        _validate_orientation_gallery_cell(self)

    @property
    def cell_id(self) -> str:
        return f"{self.variant.slug}:{self.phase_slug}"


def _validate_orientation_gallery_cell(cell: OrientationGalleryCell) -> None:
    """Revalidate a gallery cell before any downstream rendering or publication."""
    if not isinstance(cell, OrientationGalleryCell):
        raise TypeError("cell must be an OrientationGalleryCell")
    phase_slug = cell.phase_slug
    variant = cell.variant
    treatment = cell.treatment
    catalog = cell.catalog
    composition = cell.composition
    selection = cell.selection
    geometry = cell.geometry
    parity_report = cell.parity_report
    frozen_reference_id = cell.frozen_reference_id
    if frozen_reference_id is not None:
        raise ValueError(
            "orientation gallery cells cannot substitute a frozen Ice reference"
        )
    if phase_slug not in _PHASE_ORDER:
        raise ValueError("orientation gallery phase_slug is not in the approved order")
    for value, expected, name in (
        (variant, OrientationGalleryVariant, "variant"),
        (treatment, HemisphereTreatment, "treatment"),
        (catalog, ArtBandCatalog, "catalog"),
        (composition, HemisphereCompositionRecipe, "composition"),
        (selection, TattooSelection, "selection"),
        (geometry, TattooGeometry, "geometry"),
        (parity_report, ReflectorParityReport, "parity_report"),
    ):
        if not isinstance(value, expected):
            raise TypeError(f"{name} must be a {expected.__name__}")
    if phase_slug != composition.phase_slug:
        raise ValueError("gallery phase_slug does not match the composition")
    if variant.orientation != composition.orientation:
        raise ValueError("gallery variant orientation does not match the composition")
    if variant.orientation.frame != "crystal_to_sample":
        raise ValueError("gallery variant orientation must be crystal_to_sample")
    if treatment.name != "standard" or treatment.arc_width_scale != 1.0:
        raise ValueError("orientation gallery cells must use the standard treatment")

    if catalog.catalog_id != stable_id("art-band-catalog", catalog.to_dict()):
        raise ValueError("gallery catalog_id does not match catalog content")
    _validate_catalog_members(catalog)
    if selection.selection_id != _selection_identity(selection):
        raise ValueError("gallery selection_id does not match selection content")
    if selection.catalog_id != catalog.catalog_id:
        raise ValueError("gallery selection catalog_id does not match the catalog")
    if selection.recipe_id != composition.recipe_id:
        raise ValueError("gallery selection recipe_id does not match the composition")
    if selection.orientation_id != variant.orientation.orientation_id:
        raise ValueError("gallery selection orientation does not match the variant")
    if len(selection.selected_paths) != 11:
        raise ValueError("gallery selection must contain exactly 11 paths")
    if geometry.geometry_id != _geometry_identity(geometry):
        raise ValueError("gallery geometry_id does not match geometry content")
    if geometry.catalog_id != catalog.catalog_id:
        raise ValueError("gallery geometry catalog_id does not match the catalog")
    if geometry.orientation_id != variant.orientation.orientation_id:
        raise ValueError("gallery geometry orientation does not match the variant")
    validate_tattoo_geometry(geometry)
    expected_geometry = build_tattoo_geometry(
        selection,
        composition,
        width_scale=1.0,
    )
    if geometry.to_dict() != expected_geometry.to_dict():
        raise ValueError("gallery geometry does not match rebuilt standard geometry")

    parity_report.validate_for_publication()
    if parity_report.source_structure_id != catalog.source_structure_id:
        raise ValueError("gallery parity source does not match the catalog")
    if parity_report.source_structure_sha256 != catalog.source_structure_sha256:
        raise ValueError("gallery parity source SHA does not match the catalog")


@dataclass(frozen=True)
class OrientationGalleryCellBundleResult:
    """The content-identified location of a published gallery cell."""

    run_id: str
    path: Path
    svg: Path
    stencil: Path
    manifest_sha256: str


def _render_names(cell: OrientationGalleryCell) -> tuple[str, str]:
    prefix = f"{cell.phase_slug}-{cell.variant.slug}"
    return f"{prefix}.svg", f"{prefix}-stencil.png"


def _validated_cell_payload(cell: OrientationGalleryCell) -> _ValidatedPayload:
    _validate_orientation_gallery_cell(cell)
    svg_name, stencil_name = _render_names(cell)
    rendered = render_primary_tattoo(cell.geometry)
    svg = rendered["primary.svg"]
    stencil = rendered["stencil.png"]
    _validate_svg(svg, boundary_id=cell.geometry.boundary.boundary_id)
    _validate_png(
        stencil,
        name="gallery stencil",
        background=(255, 255, 255),
    )
    catalog_snapshot = {
        "catalog_id": cell.catalog.catalog_id,
        "content": cell.catalog.to_dict(),
    }
    composition_snapshot = {
        "recipe_id": cell.composition.recipe_id,
        "content": cell.composition.to_dict(),
    }
    treatment_orientation_snapshot = {
        "schema_version": 1,
        "treatment_id": cell.treatment.treatment_id,
        "treatment": cell.treatment.to_dict(),
        "variant_id": cell.variant.variant_id,
        "variant_slug": cell.variant.slug,
        "orientation_id": cell.variant.orientation.orientation_id,
        "orientation": cell.variant.orientation.to_dict(),
    }
    parity_snapshot = {
        "report_id": cell.parity_report.report_id,
        "run_id": cell.parity_report.run_id,
        "content": cell.parity_report.to_dict(),
    }
    geometry_snapshot = {
        "geometry_id": cell.geometry.geometry_id,
        "content": cell.geometry.to_dict(),
    }
    run_identity = {
        "schema_version": 1,
        "phase_slug": cell.phase_slug,
        "variant_id": cell.variant.variant_id,
        "variant_slug": cell.variant.slug,
        "euler_bunge_deg": list(cell.variant.orientation.euler_bunge_deg),
        "orientation_frame": cell.variant.orientation.frame,
        "orientation_id": cell.variant.orientation.orientation_id,
        "treatment_id": cell.treatment.treatment_id,
        "treatment": cell.treatment.name,
        "arc_width_scale": cell.treatment.arc_width_scale,
        "source_catalog_id": cell.catalog.catalog_id,
        "source_structure_id": cell.catalog.source_structure_id,
        "source_structure_sha256": cell.catalog.source_structure_sha256,
        "parity_report_id": cell.parity_report.report_id,
        "parity_run_id": cell.parity_report.run_id,
        "selection_id": cell.selection.selection_id,
        "geometry_id": cell.geometry.geometry_id,
        "boundary_id": cell.geometry.boundary.boundary_id,
        "simulation_count": 0,
        "rendered_sha256": {
            svg_name: _sha256_bytes(svg),
            stencil_name: _sha256_bytes(stencil),
        },
    }
    files: dict[str, bytes | object] = {
        svg_name: svg,
        stencil_name: stencil,
        "art-band-catalog.json": catalog_snapshot,
        "hemisphere-composition-recipe.json": composition_snapshot,
        "band-selection-ledger.json": _selection_snapshot(cell.selection),
        "path-geometry.json": geometry_snapshot,
        "gallery-treatment-orientation.json": treatment_orientation_snapshot,
        "reflector-parity-report.json": parity_snapshot,
        "scientific-claim.txt": _SCIENTIFIC_CLAIM.encode("utf-8"),
    }
    return _ValidatedPayload(
        run_identity=run_identity,
        files=files,
        payload_order=tuple(files),
    )


def _payload_checksums(payload: _ValidatedPayload) -> dict[str, dict[str, object]]:
    checksums: dict[str, dict[str, object]] = {}
    for name in payload.payload_order:
        content = payload.files[name]
        raw = content if isinstance(content, bytes) else canonical_json(content).encode("utf-8")
        checksums[name] = {"bytes": len(raw), "sha256": _sha256_bytes(raw)}
    return checksums


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_manifest_sha256(
    path: Path,
    *,
    run_id: str,
    payload: _ValidatedPayload,
) -> str | None:
    manifest_path = path / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    expected_checksums = _payload_checksums(payload)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("run_id") != run_id
        or manifest.get("run_identity") != payload.run_identity
        or manifest.get("files") != expected_checksums
    ):
        return None
    if {child.name for child in path.iterdir()} != set(expected_checksums) | {"manifest.json"}:
        return None
    for name, expected in expected_checksums.items():
        artifact = path / name
        if (
            not artifact.is_file()
            or artifact.stat().st_size != expected["bytes"]
            or _sha256_file(artifact) != expected["sha256"]
        ):
            return None
    return _sha256_file(manifest_path)


def _publish_idempotent_payload(
    output_root: str | Path,
    *,
    run_id: str,
    payload: _ValidatedPayload,
) -> tuple[Path, str]:
    """Return a checksum-valid existing bundle, otherwise promote once atomically."""
    root = Path(output_root)
    completed = root / run_id
    if completed.exists():
        manifest_sha256 = _existing_manifest_sha256(
            completed,
            run_id=run_id,
            payload=payload,
        )
        if manifest_sha256 is not None:
            return completed, manifest_sha256
        raise BundleExistsError(f"divergent completed bundle already exists: {completed}")
    try:
        return _publish_validated_payload(root, run_id=run_id, payload=payload)
    except BundleExistsError:
        manifest_sha256 = _existing_manifest_sha256(
            completed,
            run_id=run_id,
            payload=payload,
        )
        if manifest_sha256 is not None:
            return completed, manifest_sha256
        raise


def write_orientation_gallery_cell_bundle(
    output_root: str | Path,
    *,
    cell: OrientationGalleryCell,
) -> OrientationGalleryCellBundleResult:
    """Atomically publish one content-addressed standard-width gallery cell."""
    payload = _validated_cell_payload(cell)
    run_id = stable_id("orientation-gallery-cell", payload.run_identity)
    path, manifest_sha256 = _publish_idempotent_payload(
        output_root,
        run_id=run_id,
        payload=payload,
    )
    svg_name, stencil_name = _render_names(cell)
    return OrientationGalleryCellBundleResult(
        run_id=run_id,
        path=path,
        svg=path / svg_name,
        stencil=path / stencil_name,
        manifest_sha256=manifest_sha256,
    )


__all__ = [
    "OrientationGalleryCell",
    "OrientationGalleryCellBundleResult",
    "write_orientation_gallery_cell_bundle",
]

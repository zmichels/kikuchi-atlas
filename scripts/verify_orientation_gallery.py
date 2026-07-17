#!/usr/bin/env python3
"""Verify a retained five-phase standard orientation gallery without rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from kikuchi_lab.art_products.contracts import (
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)
from kikuchi_lab.art_products.tattoo_bundle import _validate_svg
from kikuchi_lab.art_products.tattoo_vector import validate_tattoo_geometry
from kikuchi_lab.kinematical.reflector_parity import ReflectorParityReport
from kikuchi_lab.model.identity import stable_id


_REPO_ROOT = Path(__file__).parents[1]
_DEFAULT_RECIPE = _REPO_ROOT / "recipes/art/five-phase-standard-orientation-gallery.yml"
_IDENTITY_FIELDS = (
    "phase_slug",
    "variant_slug",
    "orientation_id",
    "selection_id",
    "geometry_id",
    "parity_report_id",
    "source_catalog_id",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load JSON {path}: {error}") from error
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mapping(value: object, field: str) -> Mapping[str, object]:
    _require(isinstance(value, Mapping), f"{field} must be a mapping")
    return value


def _list(value: object, field: str) -> list[object]:
    _require(isinstance(value, list), f"{field} must be a list")
    return value


def _geometry_from_snapshot(snapshot: Mapping[str, object]) -> TattooGeometry:
    content = _mapping(snapshot.get("content"), "geometry content")
    boundary_data = dict(_mapping(content.get("boundary"), "geometry boundary"))
    expected_boundary_id = boundary_data.pop("boundary_id", None)
    boundary = TattooBoundary(**boundary_data)
    _require(
        boundary.boundary_id == expected_boundary_id,
        "geometry boundary ID differs from its content",
    )

    paths: list[TattooPath] = []
    for item in _list(content.get("paths"), "geometry paths"):
        path_data = _mapping(item, "geometry path")
        expected_path_id = path_data.get("path_id")
        expected_points_sha = path_data.get("points_sha256")
        path = TattooPath(
            member_id=str(path_data["member_id"]),
            tier=str(path_data["tier"]),
            width_mm=float(path_data["width_mm"]),
            points_mm=np.asarray(path_data["points_mm"], dtype=np.float64),
            score_components=_mapping(path_data["score_components"], "score components"),
            selection_reason=str(path_data["selection_reason"]),
        )
        _require(path.path_id == expected_path_id, "geometry path ID differs from content")
        _require(
            path.points_sha256 == expected_points_sha,
            "geometry path points SHA-256 differs from content",
        )
        paths.append(path)

    geometry = TattooGeometry(
        schema_version=int(content["schema_version"]),
        catalog_id=str(content["catalog_id"]),
        orientation_id=str(content["orientation_id"]),
        artboard_size_mm=float(content["artboard_size_mm"]),
        boundary=boundary,
        paths=tuple(paths),
        projection=str(content["projection"]),
    )
    _require(
        snapshot.get("geometry_id") == geometry.geometry_id,
        "geometry ID differs from its content",
    )
    validate_tattoo_geometry(geometry)
    return geometry


def _verify_manifest(bundle: Path) -> int:
    manifest = _load_json(bundle / "manifest.json")
    _require(manifest.get("run_id") == bundle.name, f"bundle ID mismatch: {bundle}")
    files = _mapping(manifest.get("files"), f"manifest files for {bundle}")
    _require(
        {path.name for path in bundle.iterdir()} == set(files) | {"manifest.json"},
        f"bundle inventory differs from manifest: {bundle}",
    )
    for name, recorded in files.items():
        artifact = bundle / name
        checksum = _mapping(recorded, f"checksum for {artifact}")
        _require(artifact.is_file(), f"missing artifact: {artifact}")
        _require(
            artifact.stat().st_size == checksum.get("bytes"),
            f"artifact byte count differs: {artifact}",
        )
        _require(
            _sha256(artifact) == checksum.get("sha256"),
            f"artifact SHA-256 differs: {artifact}",
        )
    return len(files)


def _load_recipe(recipe_path: Path) -> tuple[list[str], list[Mapping[str, object]]]:
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    recipe_mapping = _mapping(recipe, "orientation gallery recipe")
    series_name = recipe_mapping.get("source_series_recipe")
    _require(isinstance(series_name, str), "recipe source_series_recipe must be text")
    series = yaml.safe_load(
        (recipe_path.parent / series_name).read_text(encoding="utf-8")
    )
    series_mapping = _mapping(series, "source series recipe")
    phases = _list(series_mapping.get("phase_order"), "source series phase order")
    variants = _list(recipe_mapping.get("variants"), "orientation gallery variants")
    _require(all(isinstance(phase, str) for phase in phases), "phase order must be text")
    return list(phases), [_mapping(variant, "orientation variant") for variant in variants]


def _load_passed_reports(parity_root: Path) -> dict[str, ReflectorParityReport]:
    reports: dict[str, ReflectorParityReport] = {}
    for path in sorted(parity_root.rglob("reflector-parity-report.json")):
        report = ReflectorParityReport.from_json(path.read_text(encoding="utf-8"))
        report.validate_for_publication()
        _require(report.report_id not in reports, f"duplicate parity report: {report.report_id}")
        reports[report.report_id] = report
    _require(len(reports) == 5, "expected exactly five passed parity reports")
    return reports


def _verify_cell(
    bundle: Path,
    *,
    record: Mapping[str, object],
    expected_orientation: Mapping[str, object],
    reports: Mapping[str, ReflectorParityReport],
) -> None:
    manifest = _load_json(bundle / "manifest.json")
    identity = _mapping(manifest.get("run_identity"), f"cell identity for {bundle}")
    _require(
        manifest.get("run_id") == stable_id("orientation-gallery-cell", identity),
        f"content-addressed cell ID differs: {bundle}",
    )
    for field in _IDENTITY_FIELDS:
        _require(record.get(field) == identity.get(field), f"ledger mismatch: {field}")
    _require(
        identity.get("orientation_frame") == "crystal_to_sample",
        "cell orientation frame is not crystal_to_sample",
    )
    _require(
        identity.get("euler_bunge_deg") == expected_orientation.get("euler_bunge_deg"),
        "cell Euler orientation differs from approved recipe",
    )
    _require(
        identity.get("treatment") == "standard"
        and identity.get("arc_width_scale") == 1.0
        and identity.get("simulation_count") == 0,
        "cell is not standard-width, zero-master gallery evidence",
    )

    orientation = _load_json(bundle / "gallery-treatment-orientation.json")
    orientation_data = _mapping(orientation.get("orientation"), "cell orientation")
    _require(
        orientation.get("variant_slug") == identity.get("variant_slug")
        and orientation.get("orientation_id") == identity.get("orientation_id")
        and orientation_data.get("frame") == "crystal_to_sample"
        and orientation_data.get("euler_bunge_deg") == identity.get("euler_bunge_deg"),
        "retained orientation does not match cell identity",
    )
    _require(
        orientation.get("treatment") == {"name": "standard", "arc_width_scale": 1.0},
        "retained treatment is not standard width",
    )

    selection = _load_json(bundle / "band-selection-ledger.json")
    _require(
        selection.get("selection_id") == identity.get("selection_id")
        and selection.get("catalog_id") == identity.get("source_catalog_id")
        and selection.get("orientation_id") == identity.get("orientation_id"),
        "selection provenance does not match cell identity",
    )
    _require(
        len(_list(selection.get("selected_paths"), "selected paths")) == 11,
        "selection does not contain eleven paths",
    )
    selection_ledger = _mapping(selection.get("ledger"), "selection ledger")
    _require(
        "wide_clearance_search" not in selection_ledger,
        "selection contains wide-treatment evidence",
    )

    geometry = _geometry_from_snapshot(_load_json(bundle / "path-geometry.json"))
    _require(
        geometry.geometry_id == identity.get("geometry_id")
        and geometry.boundary.boundary_id == identity.get("boundary_id")
        and len(geometry.paths) == 11,
        "geometry provenance or complete boundary paths differ from cell identity",
    )
    svg_paths = list(bundle.glob("*.svg"))
    _require(len(svg_paths) == 1, f"expected one SVG: {bundle}")
    _validate_svg(svg_paths[0].read_bytes(), boundary_id=geometry.boundary.boundary_id)
    stencil_paths = list(bundle.glob("*-stencil.png"))
    _require(len(stencil_paths) == 1, f"expected one stencil: {bundle}")
    with Image.open(stencil_paths[0]) as stencil:
        _require(
            stencil.size == (1713, 1713)
            and stencil.mode == "RGB"
            and stencil.getpixel((0, 0)) == (255, 255, 255),
            "stencil dimensions or white background differ",
        )

    catalog = _load_json(bundle / "art-band-catalog.json")
    catalog_content = _mapping(catalog.get("content"), "catalog content")
    _require(
        catalog.get("catalog_id") == identity.get("source_catalog_id")
        and catalog.get("catalog_id")
        == stable_id("art-band-catalog", catalog_content),
        "catalog ID differs from its content or cell identity",
    )
    parity_snapshot = _load_json(bundle / "reflector-parity-report.json")
    parity_id = identity.get("parity_report_id")
    _require(isinstance(parity_id, str) and parity_id in reports, "unknown parity report")
    report = reports[parity_id]
    _require(
        parity_snapshot.get("report_id") == report.report_id
        and parity_snapshot.get("run_id") == report.run_id
        and parity_snapshot.get("content") == report.to_dict(),
        "retained parity snapshot differs from passed parity report",
    )
    _require(
        catalog_content.get("source_structure_id") == report.source_structure_id
        and catalog_content.get("source_structure_sha256")
        == report.source_structure_sha256,
        "catalog and parity source provenance differ",
    )


def verify_gallery(
    *, gallery_root: Path, parity_root: Path, recipe_path: Path
) -> tuple[int, int, int]:
    phases, variants = _load_recipe(recipe_path)
    expected_order = [
        f"{variant['slug']}:{phase}" for variant in variants for phase in phases
    ]
    _require(len(expected_order) == 15, "recipe must define fifteen gallery cells")
    expected_orientations = {
        str(variant["slug"]): _mapping(variant.get("orientation"), "variant orientation")
        for variant in variants
    }
    _require(len(expected_orientations) == 3, "recipe must define three orientations")
    _require(gallery_root.is_dir(), f"gallery root is not a directory: {gallery_root}")
    _require(parity_root.is_dir(), f"parity root is not a directory: {parity_root}")

    cell_bundles = sorted(gallery_root.glob("orientation-gallery-cell-*"))
    sheet_bundles = sorted(gallery_root.glob("orientation-gallery-sheet-*"))
    _require(
        len(cell_bundles) == 15 and len(sheet_bundles) == 1,
        "gallery must contain fifteen cells and one comparison sheet",
    )
    _require(
        {path.name for path in gallery_root.iterdir()}
        == {path.name for path in cell_bundles + sheet_bundles},
        "gallery root contains an unexpected bundle inventory",
    )

    sheet = sheet_bundles[0]
    ledger = _load_json(sheet / "orientation-gallery-comparison-ledger.json")
    sheet_manifest = _load_json(sheet / "manifest.json")
    ledger_records = _list(ledger.get("cells"), "comparison ledger cells")
    records = {
        str(_mapping(record, "comparison cell record").get("cell_id")): _mapping(
            record, "comparison cell record"
        )
        for record in ledger_records
    }
    _require(
        ledger.get("cell_order") == expected_order
        and len(records) == 15
        and set(records) == set(expected_order),
        "comparison ledger does not retain the approved phase-by-variant inventory",
    )
    _require(
        ledger.get("layout")
        == {
            "columns": 5,
            "rows": 3,
            "variant_row_order": list(expected_orientations),
        },
        "comparison ledger layout differs from the approved three-by-five grid",
    )
    _require(
        all(
            record.get("simulation_count") == 0
            and record.get("treatment") == "standard"
            and record.get("arc_width_scale") == 1.0
            for record in records.values()
        ),
        "comparison ledger contains nonstandard or simulated cells",
    )
    sheet_identity = _mapping(sheet_manifest.get("run_identity"), "sheet identity")
    _require(
        sheet_manifest.get("run_id")
        == sheet.name
        == stable_id("orientation-gallery-sheet", sheet_identity),
        "content-addressed comparison sheet ID differs",
    )
    _require(
        sheet_identity.get("ledger_id") == ledger.get("ledger_id")
        and sheet_identity.get("simulation_count") == 0,
        "comparison sheet identity differs from ledger or zero-master policy",
    )
    comparison = sheet / "orientation-gallery-comparison.png"
    with Image.open(comparison) as image:
        _require(
            image.size == (4500, 2700) and image.mode == "RGB",
            "comparison sheet dimensions or mode differ",
        )
    _require(
        sheet_identity.get("comparison_sha256") == _sha256(comparison),
        "comparison sheet SHA-256 differs from its identity",
    )

    reports = _load_passed_reports(parity_root)
    checked_artifacts = sum(_verify_manifest(bundle) for bundle in cell_bundles)
    checked_artifacts += _verify_manifest(sheet)
    for bundle in cell_bundles:
        manifest = _load_json(bundle / "manifest.json")
        identity = _mapping(manifest.get("run_identity"), f"cell identity for {bundle}")
        cell_id = f"{identity.get('variant_slug')}:{identity.get('phase_slug')}"
        variant_slug = identity.get("variant_slug")
        _require(
            isinstance(variant_slug, str) and variant_slug in expected_orientations,
            "cell variant is not an approved recipe variant",
        )
        _verify_cell(
            bundle,
            record=records[cell_id],
            expected_orientation=expected_orientations[variant_slug],
            reports=reports,
        )
    return len(cell_bundles), checked_artifacts, len(reports)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery-root", required=True, type=Path)
    parser.add_argument("--parity-root", required=True, type=Path)
    parser.add_argument("--recipe", type=Path, default=_DEFAULT_RECIPE)
    args = parser.parse_args(argv)
    try:
        cells, artifacts, reports = verify_gallery(
            gallery_root=args.gallery_root,
            parity_root=args.parity_root,
            recipe_path=args.recipe,
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"orientation gallery verification failed: {error}", file=sys.stderr)
        return 1
    print(
        "orientation-gallery-probe PASS "
        f"root={args.gallery_root} cells={cells} artifacts_checked={artifacts} "
        f"parity_reports={reports}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

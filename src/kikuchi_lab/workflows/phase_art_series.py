"""Parity-gated zero-master publication of the five-phase art series."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.clearance_selection import (
    select_clearance_valid_tattoo_paths,
)
from kikuchi_lab.art_products.contracts import ArtBandCatalog, TattooGeometry
from kikuchi_lab.art_products.frozen_selection import (
    FrozenTattooSelection,
    bind_frozen_tattoo_selection,
    load_frozen_tattoo_selection,
)
from kikuchi_lab.art_products.hemisphere_bundle import (
    PhaseHemisphereBundleResult,
    _validated_phase_payload,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    HemisphereCompositionRecipe,
    HemisphereSeriesRecipe,
    HemisphereTreatment,
    load_hemisphere_series_recipe,
)
from kikuchi_lab.art_products.series_sheet import (
    CELL_ORDER,
    SeriesSheetBundleResult,
    SeriesSheetCell,
    _validated_series_payload,
    render_series_sheet,
)
from kikuchi_lab.art_products.tattoo_bundle import (
    DISCLAIMER_TEXT,
    _ValidatedPayload,
    _publish_validated_payload,
    _selection_snapshot,
)
from kikuchi_lab.art_products.tattoo_selection import TattooSelection
from kikuchi_lab.art_products.tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
)
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    build_direct_reflector_evidence,
)
from kikuchi_lab.kinematical.reflector_evidence import (
    DirectReflectorEvidence,
    DirectReflectorRecipe,
    load_direct_reflector_recipe,
)
from kikuchi_lab.kinematical.reflector_parity import ReflectorParityReport
from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


_ICE_SELECTION_MANIFEST = "ice-ih-reviewed-selection-v2.yml"
_ResultT = TypeVar("_ResultT")


class IceStandardReferenceMismatch(ValueError):
    """The supplied reference is not the corrected reviewed Ice standard."""


class PhaseParityReportError(ValueError):
    """A phase lacks one unique, current, publication-valid parity report."""


@dataclass(frozen=True)
class PhaseArtSeriesResult:
    """Published series identity, ordered child bundles, and finite-work facts."""

    series_id: str
    path: Path
    new_bundles: tuple[PhaseHemisphereBundleResult, ...]
    comparison_sheet: Path
    simulation_count: int
    cell_order: tuple[str, ...]
    manifest_sha256: str


@dataclass(frozen=True)
class _DirectPhase:
    phase_slug: str
    recipe: DirectReflectorRecipe
    evidence: DirectReflectorEvidence
    catalog: ArtBandCatalog
    parity: ReflectorParityReport


@dataclass(frozen=True)
class _PreparedBundle:
    phase_slug: str
    treatment: str
    selection: TattooSelection
    geometry: TattooGeometry
    run_id: str
    payload: _ValidatedPayload


def _run_phase_step(
    operation: Callable[[], _ResultT],
    phase_diagnostics: Mapping[str, Mapping[str, object]],
) -> _ResultT:
    try:
        return operation()
    except Exception as error:
        setattr(error, "phase_diagnostics", plain_data(phase_diagnostics))
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_parity_reports(parity_root: str | Path) -> tuple[ReflectorParityReport, ...]:
    root = Path(parity_root)
    if not root.is_dir():
        raise PhaseParityReportError(f"parity root is not a directory: {root}")
    report_paths = sorted(root.rglob("reflector-parity-report.json"))
    if not report_paths:
        raise PhaseParityReportError(
            f"parity root contains no reflector-parity-report.json files: {root}"
        )
    reports: list[ReflectorParityReport] = []
    for path in report_paths:
        try:
            report = ReflectorParityReport.from_json(
                path.read_text(encoding="utf-8")
            ).with_path(path.parent)
            report.validate_for_publication()
        except (OSError, TypeError, ValueError) as error:
            raise PhaseParityReportError(
                f"malformed or failed reflector parity report {path}: {error}"
            ) from error
        reports.append(report)
    return tuple(reports)


def resolve_unique_passed_parity_report(
    reports: tuple[ReflectorParityReport, ...],
    *,
    phase_slug: str,
    evidence: DirectReflectorEvidence,
) -> ReflectorParityReport:
    """Resolve exactly one recursively discovered report and reject stale identity."""
    candidates = tuple(
        report
        for report in reports
        if report.source_structure_id == evidence.source_structure_id
    )
    if len(candidates) != 1:
        raise PhaseParityReportError(
            f"expected exactly one passed parity report for {phase_slug}; "
            f"found {len(candidates)}"
        )
    report = candidates[0]
    expected = {
        "source_structure_id": evidence.source_structure_id,
        "source_structure_sha256": evidence.source_structure_sha256,
        "calculation_id": evidence.calculation_id,
        "weighting_id": evidence.weighting_id,
        "direct_evidence_id": evidence.evidence_id,
    }
    stale = {
        field: {"expected": value, "observed": getattr(report, field)}
        for field, value in expected.items()
        if getattr(report, field) != value
    }
    if stale:
        raise PhaseParityReportError(
            f"stale reflector parity report for {phase_slug}: {stale}"
        )
    return report


def _build_direct_phase(
    *,
    recipe_file: Path,
    series: HemisphereSeriesRecipe,
    phase_slug: str,
    reports: tuple[ReflectorParityReport, ...],
) -> _DirectPhase:
    reflector_path = (
        recipe_file.parent / series.reflector_recipes[phase_slug]
    ).resolve()
    reflector_recipe = load_direct_reflector_recipe(reflector_path)
    source_path = (reflector_path.parent / reflector_recipe.source_record).resolve()
    if source_path.parent.name != phase_slug:
        raise ValueError(
            f"reflector source for {phase_slug} resolves to a different phase"
        )
    source = load_structure_record(source_path)
    verify_structure(source)
    evidence = build_direct_reflector_evidence(source, reflector_recipe)
    if evidence.ledger.get("simulation_count") != 0:
        raise ValueError(f"direct evidence for {phase_slug} is not zero-master")
    catalog = build_art_band_catalog_from_evidence(evidence)
    parity = resolve_unique_passed_parity_report(
        reports,
        phase_slug=phase_slug,
        evidence=evidence,
    )
    return _DirectPhase(
        phase_slug=phase_slug,
        recipe=reflector_recipe,
        evidence=evidence,
        catalog=catalog,
        parity=parity,
    )


def _prepare_bundle(
    *,
    phase_slug: str,
    treatment: HemisphereTreatment,
    catalog: ArtBandCatalog,
    composition: HemisphereCompositionRecipe,
    selection: TattooSelection,
    geometry: TattooGeometry,
    rendered: Mapping[str, bytes],
    frozen_manifest: FrozenTattooSelection | None,
) -> _PreparedBundle:
    payload = _validated_phase_payload(
        phase_slug=phase_slug,
        treatment=treatment,
        catalog=catalog,
        recipe=composition,
        selection=selection,
        geometry=geometry,
        rendered=rendered,
        disclaimer=DISCLAIMER_TEXT,
        frozen_manifest=frozen_manifest,
    )
    run_id = stable_id(
        f"{phase_slug}-hemisphere-{treatment.name}-run",
        payload.run_identity,
    )
    return _PreparedBundle(
        phase_slug=phase_slug,
        treatment=treatment.name,
        selection=selection,
        geometry=geometry,
        run_id=run_id,
        payload=payload,
    )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name} is not valid readable JSON") from error


def _validate_reference_inventory(
    reference: Path,
    *,
    expected_payload: _ValidatedPayload,
) -> dict[str, object]:
    if not reference.is_dir():
        raise ValueError("reference path is not a directory")
    manifest = _read_json(reference / "manifest.json")
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "run_id",
        "run_identity",
        "files",
    }:
        raise ValueError("reference manifest fields differ from the bundle schema")
    if manifest["schema_version"] != 1:
        raise ValueError("reference manifest schema_version must be 1")
    run_identity = manifest["run_identity"]
    files = manifest["files"]
    if not isinstance(run_identity, dict) or not isinstance(files, dict):
        raise ValueError("reference manifest identity and files must be mappings")
    expected_identity = plain_data(expected_payload.run_identity)
    if plain_data(run_identity) != expected_identity:
        raise ValueError("reference run identity differs from corrected standard")
    expected_names = set(expected_payload.files)
    if set(files) != expected_names:
        raise ValueError("reference manifest inventory differs from corrected standard")
    actual_names = {path.name for path in reference.iterdir()}
    if actual_names != expected_names | {"manifest.json"}:
        raise ValueError("reference directory inventory differs from its manifest")
    for name, record in files.items():
        path = reference / name
        if (
            not isinstance(record, dict)
            or set(record) != {"bytes", "sha256"}
            or type(record["bytes"]) is not int
            or record["bytes"] < 0
            or not isinstance(record["sha256"], str)
        ):
            raise ValueError(f"reference inventory record is invalid for {name}")
        if path.stat().st_size != record["bytes"] or _sha256(path) != record["sha256"]:
            raise ValueError(f"reference checksum inventory differs for {name}")
        expected_content = expected_payload.files[name]
        if isinstance(expected_content, bytes):
            if path.read_bytes() != expected_content:
                raise ValueError(f"reference {name} bytes differ from corrected content")
        elif _read_json(path) != plain_data(expected_content):
            raise ValueError(f"reference {name} differs from corrected content")
    expected_run_id = stable_id(
        "ice-ih-hemisphere-standard-run",
        expected_identity,
    )
    if manifest["run_id"] != expected_run_id or reference.name != expected_run_id:
        raise ValueError("reference run identity differs from its manifest or path")
    return manifest


def assert_reviewed_ice_reference(
    *,
    reference_path: str | Path,
    expected_payload: _ValidatedPayload,
    catalog: ArtBandCatalog,
    composition: HemisphereCompositionRecipe,
    selection: TattooSelection,
    standard_geometry: TattooGeometry,
    frozen_manifest: FrozenTattooSelection,
) -> str:
    """Lock the supplied standard to corrected evidence and the tracked review."""
    reference = Path(reference_path)
    try:
        manifest = _validate_reference_inventory(
            reference,
            expected_payload=expected_payload,
        )
        expected_snapshots = {
            "art-band-catalog.json": {
                "catalog_id": catalog.catalog_id,
                "content": catalog.to_dict(),
            },
            "hemisphere-composition-recipe.json": {
                "recipe_id": composition.recipe_id,
                "content": composition.to_dict(),
            },
            "hemisphere-treatment-recipe.json": expected_payload.files[
                "hemisphere-treatment-recipe.json"
            ],
            "frozen-selection-manifest.json": {
                "manifest_id": frozen_manifest.manifest_id,
                "content": frozen_manifest.to_dict(),
            },
            "band-selection-ledger.json": _selection_snapshot(selection),
            "path-geometry.json": {
                "geometry_id": standard_geometry.geometry_id,
                "content": standard_geometry.to_dict(),
            },
        }
        for name, expected in expected_snapshots.items():
            if _read_json(reference / name) != plain_data(expected):
                raise ValueError(f"reference {name} differs from corrected content")
        selected = _read_json(reference / "band-selection-ledger.json")
        selected_paths = selected["selected_paths"]
        if [path["member_id"] for path in selected_paths] != [
            path.member_id for path in selection.selected_paths
        ] or [path["center_trace_sha256"] for path in selected_paths] != [
            path.center_trace_sha256 for path in selection.selected_paths
        ]:
            raise ValueError("reference member order or center-trace hashes differ")
    except (KeyError, OSError, TypeError, ValueError) as error:
        if isinstance(error, IceStandardReferenceMismatch):
            raise
        raise IceStandardReferenceMismatch(
            f"reviewed Ice standard reference mismatch: {error}"
        ) from error
    return str(manifest["run_id"])


def _publish_prepared_bundle(
    output_root: str | Path,
    prepared: _PreparedBundle,
) -> PhaseHemisphereBundleResult:
    path, manifest_sha256 = _publish_validated_payload(
        output_root,
        run_id=prepared.run_id,
        payload=prepared.payload,
    )
    return PhaseHemisphereBundleResult(
        run_id=prepared.run_id,
        path=path,
        phase_slug=prepared.phase_slug,
        treatment=prepared.treatment,
        selection_id=prepared.selection.selection_id,
        geometry_id=prepared.geometry.geometry_id,
        manifest_sha256=manifest_sha256,
    )


def render_phase_art_series(
    recipe_path: str | Path,
    parity_root: str | Path,
    ice_standard_reference: str | Path,
    output_root: str | Path,
) -> PhaseArtSeriesResult:
    """Preflight all five phases, then publish nine bundles and one series."""
    recipe_file = Path(recipe_path).resolve()
    series = load_hemisphere_series_recipe(recipe_file)
    phase_diagnostics: dict[str, dict[str, object]] = {
        phase_slug: {"status": "incomplete"} for phase_slug in series.phase_order
    }
    reports = _run_phase_step(
        lambda: _load_parity_reports(parity_root),
        phase_diagnostics,
    )
    frozen_manifest = load_frozen_tattoo_selection(
        recipe_file.parent / _ICE_SELECTION_MANIFEST
    )

    prepared_bundles: list[_PreparedBundle] = []
    prepared_cells: dict[str, tuple[TattooSelection, TattooGeometry]] = {}
    reference_run_id: str | None = None
    for phase_slug in series.phase_order:
        direct = _run_phase_step(
            lambda: _build_direct_phase(
                recipe_file=recipe_file,
                series=series,
                phase_slug=phase_slug,
                reports=reports,
            ),
            phase_diagnostics,
        )
        composition = _run_phase_step(
            lambda: series.composition_for(phase_slug),
            phase_diagnostics,
        )
        phase_manifest = frozen_manifest if phase_slug == "ice-ih" else None
        if phase_manifest is not None:
            selection = _run_phase_step(
                lambda: bind_frozen_tattoo_selection(
                    direct.catalog,
                    composition,
                    phase_manifest,
                ),
                phase_diagnostics,
            )
        else:
            selection = _run_phase_step(
                lambda: select_clearance_valid_tattoo_paths(
                    direct.catalog,
                    composition,
                ),
                phase_diagnostics,
            )

        wide = _run_phase_step(
            lambda: build_tattoo_geometry(
                selection,
                composition,
                width_scale=1.15,
            ),
            phase_diagnostics,
        )
        standard = _run_phase_step(
            lambda: build_tattoo_geometry(
                selection,
                composition,
                width_scale=1.0,
            ),
            phase_diagnostics,
        )
        wide_rendered = _run_phase_step(
            lambda: dict(render_primary_tattoo(wide)),
            phase_diagnostics,
        )
        standard_rendered = _run_phase_step(
            lambda: dict(render_primary_tattoo(standard)),
            phase_diagnostics,
        )
        prepared_cells[f"{phase_slug}:standard"] = (selection, standard)
        prepared_cells[f"{phase_slug}:wide"] = (selection, wide)

        if phase_slug == "ice-ih":
            standard_payload = _run_phase_step(
                lambda: _validated_phase_payload(
                    phase_slug=phase_slug,
                    treatment=series.treatments["standard"],
                    catalog=direct.catalog,
                    recipe=composition,
                    selection=selection,
                    geometry=standard,
                    rendered=standard_rendered,
                    disclaimer=DISCLAIMER_TEXT,
                    frozen_manifest=phase_manifest,
                ),
                phase_diagnostics,
            )
            reference_run_id = _run_phase_step(
                lambda: assert_reviewed_ice_reference(
                    reference_path=ice_standard_reference,
                    expected_payload=standard_payload,
                    catalog=direct.catalog,
                    composition=composition,
                    selection=selection,
                    standard_geometry=standard,
                    frozen_manifest=phase_manifest,
                ),
                phase_diagnostics,
            )
            prepared_bundles.append(
                _run_phase_step(
                    lambda: _prepare_bundle(
                        phase_slug=phase_slug,
                        treatment=series.treatments["wide"],
                        catalog=direct.catalog,
                        composition=composition,
                        selection=selection,
                        geometry=wide,
                        rendered=wide_rendered,
                        frozen_manifest=phase_manifest,
                    ),
                    phase_diagnostics,
                )
            )
            phase_diagnostics[phase_slug] = {
                "status": "passed",
                "parity_report_id": direct.parity.report_id,
                "catalog_id": direct.catalog.catalog_id,
                "selection_id": selection.selection_id,
                "standard_geometry_id": standard.geometry_id,
                "wide_geometry_id": wide.geometry_id,
            }
            continue

        wide_bundle = _run_phase_step(
            lambda: _prepare_bundle(
                phase_slug=phase_slug,
                treatment=series.treatments["wide"],
                catalog=direct.catalog,
                composition=composition,
                selection=selection,
                geometry=wide,
                rendered=wide_rendered,
                frozen_manifest=None,
            ),
            phase_diagnostics,
        )
        standard_bundle = _run_phase_step(
            lambda: _prepare_bundle(
                phase_slug=phase_slug,
                treatment=series.treatments["standard"],
                catalog=direct.catalog,
                composition=composition,
                selection=selection,
                geometry=standard,
                rendered=standard_rendered,
                frozen_manifest=None,
            ),
            phase_diagnostics,
        )
        prepared_bundles.extend((standard_bundle, wide_bundle))
        phase_diagnostics[phase_slug] = {
            "status": "passed",
            "parity_report_id": direct.parity.report_id,
            "catalog_id": direct.catalog.catalog_id,
            "selection_id": selection.selection_id,
            "standard_geometry_id": standard.geometry_id,
            "wide_geometry_id": wide.geometry_id,
        }

    if reference_run_id is None:
        raise AssertionError("Ice reference was not validated")
    prepared_by_cell = {
        f"{bundle.phase_slug}:{bundle.treatment}": bundle
        for bundle in prepared_bundles
    }
    cells: list[SeriesSheetCell] = []
    for cell_id in CELL_ORDER:
        phase_slug, treatment = cell_id.split(":")
        selection, geometry = prepared_cells[cell_id]
        bundle_id = (
            reference_run_id
            if cell_id == "ice-ih:standard"
            else prepared_by_cell[cell_id].run_id
        )
        cells.append(
            SeriesSheetCell(
                phase_slug=phase_slug,
                treatment=treatment,
                geometry=geometry,
                bundle_id=bundle_id,
                selection_id=selection.selection_id,
                source_kind=(
                    "reference" if cell_id == "ice-ih:standard" else "bundle"
                ),
            )
        )
    rendered_sheet = render_series_sheet(cells)
    series_id, series_payload = _validated_series_payload(
        recipe_id=series.series_id,
        rendered=rendered_sheet,
    )

    published = tuple(
        _publish_prepared_bundle(output_root, prepared)
        for prepared in prepared_bundles
    )
    series_path, series_manifest_sha256 = _publish_validated_payload(
        output_root,
        run_id=series_id,
        payload=series_payload,
    )
    sheet_bundle = SeriesSheetBundleResult(
        series_id=series_id,
        path=series_path,
        comparison_sheet=series_path / "comparison.png",
        cell_order=rendered_sheet.cell_order,
        manifest_sha256=series_manifest_sha256,
    )
    return PhaseArtSeriesResult(
        series_id=sheet_bundle.series_id,
        path=sheet_bundle.path,
        new_bundles=published,
        comparison_sheet=sheet_bundle.comparison_sheet,
        simulation_count=0,
        cell_order=sheet_bundle.cell_order,
        manifest_sha256=sheet_bundle.manifest_sha256,
    )


__all__ = [
    "IceStandardReferenceMismatch",
    "PhaseArtSeriesResult",
    "PhaseParityReportError",
    "assert_reviewed_ice_reference",
    "render_phase_art_series",
    "resolve_unique_passed_parity_report",
]

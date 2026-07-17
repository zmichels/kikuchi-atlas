"""Reusable direct-reflector and parity preflight for phase art workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.contracts import ArtBandCatalog
from kikuchi_lab.art_products.hemisphere_recipe import HemisphereSeriesRecipe
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import (
    DirectReflectorEvidence,
    DirectReflectorRecipe,
    load_direct_reflector_recipe,
)
from kikuchi_lab.kinematical.reflector_parity import ReflectorParityReport
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


class PhaseParityReportError(ValueError):
    """A phase lacks one unique, current, publication-valid parity report."""


@dataclass(frozen=True)
class ParityGatedDirectPhase:
    """Rebuilt direct evidence matched to one current parity report."""

    phase_slug: str
    recipe: DirectReflectorRecipe
    evidence: DirectReflectorEvidence
    catalog: ArtBandCatalog
    parity: ReflectorParityReport


def load_passed_parity_reports(
    parity_root: str | Path,
) -> tuple[ReflectorParityReport, ...]:
    """Load every recursive report and retain only publication-valid evidence."""
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
    """Resolve exactly one report and reject stale direct-evidence identity."""
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


def build_parity_gated_direct_phase(
    *,
    recipe_file: Path,
    series: HemisphereSeriesRecipe,
    phase_slug: str,
    reports: tuple[ReflectorParityReport, ...],
) -> ParityGatedDirectPhase:
    """Rebuild one direct phase and bind it to a passed current parity report."""
    reflector_path = (recipe_file.parent / series.reflector_recipes[phase_slug]).resolve()
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
    return ParityGatedDirectPhase(
        phase_slug=phase_slug,
        recipe=reflector_recipe,
        evidence=evidence,
        catalog=catalog,
        parity=parity,
    )


__all__ = [
    "ParityGatedDirectPhase",
    "PhaseParityReportError",
    "build_parity_gated_direct_phase",
    "load_passed_parity_reports",
    "resolve_unique_passed_parity_report",
]

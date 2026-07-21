"""Generate the structural-source attribution audit used by public releases."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .catalog import load_phase_registry
from kikuchi_lab.sources import load_structure_record


@dataclass(frozen=True)
class StructuralSourceAuditResult:
    """Paths emitted by one deterministic source-attribution audit."""

    json_path: Path
    markdown_path: Path
    source_count: int


def _markdown(audit: dict[str, object]) -> str:
    sources = audit["sources"]
    assert isinstance(sources, list)
    rows = "\n".join(
        "| {phase} | [{identifier}]({page_uri}) | {license} | {policy} | {citation} |".format(
            phase=source["display_name"],
            identifier=source["identifier"],
            page_uri=source["page_uri"],
            license=source["license"],
            policy=source["copying_policy"],
            citation=source["citation"],
        )
        for source in sources
    )
    return (
        "# Kikuchi Atlas structural-source attribution\n\n"
        "This generated audit is the source-data attribution layer for a future public Atlas "
        "release. It identifies the exact CIF record used by each phase. It does not grant a "
        "project-wide code, media, or geometry license; those remain separate release decisions.\n\n"
        "| Phase | Structure record | License / notice | Copying policy | Citation |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{rows}\n\n"
        "The machine-readable companion, `STRUCTURAL_SOURCE_AUDIT.json`, records checksums, "
        "source URIs, exact records, and simulation settings for archival automation.\n"
    )


def build_structural_source_audit(
    *, registry_path: str | Path, output_directory: str | Path
) -> StructuralSourceAuditResult:
    """Write one auditable structural-source inventory from tracked phase records."""
    registry = Path(registry_path).resolve()
    root = registry.parents[2]
    phases = load_phase_registry(registry)
    sources: list[dict[str, object]] = []
    for phase in phases:
        if phase.source_status != "tracked-source" or phase.source_record is None:
            raise ValueError(f"public source audit requires a tracked source: {phase.slug}")
        record = load_structure_record(root / phase.source_record)
        sources.append(
            {
                "phase_slug": phase.slug,
                "display_name": phase.display_name,
                "identifier": record.identifier,
                "cif": record.cif_path.name,
                "sha256": record.sha256,
                "retrieved": record.retrieved,
                "uri": record.uri,
                "page_uri": record.page_uri,
                "license": record.license,
                "license_uri": record.license_uri,
                "copying_policy": record.copying_policy,
                "citation": record.citation,
                "source_record": phase.source_record,
                "simulation_setting": record.simulation_setting,
            }
        )
    audit: dict[str, object] = {
        "schema_version": 1,
        "title": "Kikuchi Atlas structural-source audit",
        "claim_boundary": (
            "Structure-source terms apply to the named CIF records. They do not determine the "
            "separate project-code, visual-media, or printable-geometry license."
        ),
        "source_count": len(sources),
        "sources": sources,
    }
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "STRUCTURAL_SOURCE_AUDIT.json"
    markdown_path = output / "STRUCTURAL_SOURCE_ATTRIBUTION.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(audit), encoding="utf-8")
    return StructuralSourceAuditResult(
        json_path=json_path,
        markdown_path=markdown_path,
        source_count=len(sources),
    )


__all__ = ["StructuralSourceAuditResult", "build_structural_source_audit"]

from __future__ import annotations

import json
from pathlib import Path

import yaml

from kikuchi_lab.atlas import build_structural_source_audit


ROOT = Path(__file__).parents[2]


def test_release_metadata_and_citation_are_aligned_but_do_not_invent_a_license() -> None:
    metadata = yaml.safe_load((ROOT / "docs/atlas/RELEASE_METADATA.yml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))

    assert metadata["schema_version"] == 1
    assert metadata["release"]["status"] == "prepublication"
    assert metadata["publication"]["repository_url"] == "https://github.com/zmichels/kikuchi-atlas"
    assert metadata["publication"]["static_site_url"] == "https://zmichels.github.io/kikuchi-atlas/"
    assert metadata["publication"]["archive_doi"] is None
    assert metadata["licenses"] == {
        "project_code": "MIT",
        "atlas_media_and_geometry": "CC-BY-4.0",
        "source_structures": "per-source; see STRUCTURAL_SOURCE_AUDIT.json",
    }
    assert citation["cff-version"] == "1.2.0"
    assert citation["title"] == metadata["release"]["title"]
    assert citation["version"] == metadata["release"]["version"]
    assert citation["authors"] == metadata["contributors"]
    assert citation["license"] == "MIT"
    assert zenodo["title"] == citation["title"]
    assert zenodo["version"] == citation["version"]
    assert zenodo["creators"] == [{"name": "Michels, Zachary"}]
    assert zenodo["license"] == "MIT"
    assert "CC BY 4.0" in (ROOT / "LICENSES/ATLAS_MEDIA_AND_GEOMETRY.md").read_text(
        encoding="utf-8"
    )


def test_structural_source_audit_has_one_exact_record_per_atlas_phase() -> None:
    audit = json.loads(
        (ROOT / "docs/atlas/STRUCTURAL_SOURCE_AUDIT.json").read_text(encoding="utf-8")
    )

    assert audit["schema_version"] == 1
    assert audit["source_count"] == 9
    assert {record["phase_slug"] for record in audit["sources"]} == {
        "forsterite",
        "ice-ih",
        "quartz",
        "zircon",
        "titanite",
        "diamond",
        "plagioclase-an52",
        "muscovite-2m1",
        "diopside",
    }
    assert sum(record["license"] == "CC0-1.0" for record in audit["sources"]) == 8
    muscovite = next(record for record in audit["sources"] if record["phase_slug"] == "muscovite-2m1")
    assert muscovite["identifier"] == "COD-9014960"
    assert muscovite["license"] == "COD attribution-use notice"
    assert all(record["sha256"] and record["citation"] for record in audit["sources"])


def test_structural_source_audit_builder_reproduces_the_nine_record_inventory(tmp_path: Path) -> None:
    result = build_structural_source_audit(
        registry_path=ROOT / "docs/atlas/PHASE_REGISTRY.yml", output_directory=tmp_path
    )

    assert result.source_count == 9
    assert result.markdown_path.is_file()
    regenerated = json.loads(result.json_path.read_text(encoding="utf-8"))
    tracked = json.loads((ROOT / "docs/atlas/STRUCTURAL_SOURCE_AUDIT.json").read_text(encoding="utf-8"))
    assert regenerated == tracked

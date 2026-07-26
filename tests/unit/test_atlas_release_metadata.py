from __future__ import annotations

import json
from pathlib import Path

import yaml

from kikuchi_lab.atlas import build_structural_source_audit


ROOT = Path(__file__).parents[2]


def test_release_metadata_and_citation_do_not_invent_publication_links_or_a_license() -> None:
    metadata = yaml.safe_load((ROOT / "docs/atlas/RELEASE_METADATA.yml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))

    assert metadata["schema_version"] == 1
    assert metadata["release"]["status"] == "prepublication"
    assert metadata["release"]["version"] == "0.2.0-draft"
    assert metadata["publication"]["repository_url"] == "https://github.com/zmichels/kikuchi-atlas"
    assert metadata["publication"]["static_site_url"] == "https://zmichels.github.io/kikuchi-atlas/"
    assert metadata["publication"]["google_drive_root_url"] is None
    assert metadata["publication"]["google_site_url"] is None
    assert metadata["publication"]["archive_doi"] is None
    assert metadata["licenses"] == {
        "project_code": "MIT",
        "atlas_media_and_geometry": "CC-BY-4.0",
        "source_structures": "per-source; see STRUCTURAL_SOURCE_AUDIT.json",
    }
    assert citation["cff-version"] == "1.2.0"
    assert citation["title"] == metadata["release"]["title"]
    assert citation["authors"] == metadata["contributors"]
    assert citation["license"] == "MIT"
    assert zenodo["title"] == citation["title"]
    assert zenodo["version"] == citation["version"]
    assert zenodo["creators"] == [{"name": "Michels, Zachary"}]
    assert zenodo["license"] == "MIT"
    assert "CC BY 4.0" in (ROOT / "LICENSES/ATLAS_MEDIA_AND_GEOMETRY.md").read_text(
        encoding="utf-8"
    )


def test_public_candidate_contains_125_bounded_products_without_local_references() -> None:
    site_root = ROOT / "dist/atlas-public/site"
    inventory = json.loads(
        (ROOT / "dist/atlas-public/release-inventory.json").read_text(encoding="utf-8")
    )

    assert len(inventory["products"]) == 125
    assert inventory["web_asset_limit_bytes"] == 26_214_400
    authoritative_movies = [
        product for product in inventory["products"] if product["format"] == "mov"
    ]
    assert len(authoritative_movies) == 3
    assert all(
        product["web"]["media_path"].endswith(".mp4")
        for product in authoritative_movies
    )

    declared_web_files = {
        site_root / path
        for product in inventory["products"]
        for field, path in product["web"].items()
        if field.endswith("_path") and path is not None
    }
    assert declared_web_files
    assert all(path.is_file() for path in declared_web_files)
    assert all(path.stat().st_size <= 26_214_400 for path in declared_web_files)

    forbidden_references = (b"local/", b"/Users/", b"file://")
    for path in site_root.rglob("*"):
        if path.is_file():
            contents = path.read_bytes()
            assert all(reference not in contents for reference in forbidden_references)


def test_structural_source_audit_has_one_exact_record_per_atlas_phase() -> None:
    audit = json.loads(
        (ROOT / "docs/atlas/STRUCTURAL_SOURCE_AUDIT.json").read_text(encoding="utf-8")
    )

    assert audit["schema_version"] == 1
    assert audit["source_count"] == 12
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
        "calcite",
        "enstatite",
        "pyrope",
    }
    assert sum(record["license"] == "CC0-1.0" for record in audit["sources"]) == 9
    muscovite = next(record for record in audit["sources"] if record["phase_slug"] == "muscovite-2m1")
    assert muscovite["identifier"] == "COD-9014960"
    assert muscovite["license"] == "COD attribution-use notice"
    assert all(record["sha256"] and record["citation"] for record in audit["sources"])


def test_structural_source_audit_builder_reproduces_the_twelve_record_inventory(tmp_path: Path) -> None:
    result = build_structural_source_audit(
        registry_path=ROOT / "docs/atlas/PHASE_REGISTRY.yml", output_directory=tmp_path
    )

    assert result.source_count == 12
    assert result.markdown_path.is_file()
    regenerated = json.loads(result.json_path.read_text(encoding="utf-8"))
    tracked = json.loads((ROOT / "docs/atlas/STRUCTURAL_SOURCE_AUDIT.json").read_text(encoding="utf-8"))
    assert regenerated == tracked

from __future__ import annotations

import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import yaml

from kikuchi_lab.atlas import build_structural_source_audit


ROOT = Path(__file__).parents[2]
EXPECTED_PHASE_SLUGS = {
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
        (site_root / "release-inventory.json").read_text(encoding="utf-8")
    )

    assert inventory["product_count"] == len(inventory["products"]) == 125
    assert set(inventory["phase_slugs"]) == EXPECTED_PHASE_SLUGS
    assert inventory["web_asset_limit_bytes"] == 26_214_400
    declared_assets = {asset["path"]: asset for asset in inventory["web_assets"]}
    present_assets = {
        path.relative_to(site_root).as_posix(): path
        for path in (site_root / "assets").rglob("*")
        if path.is_file()
    }
    assert inventory["web_asset_count"] == len(declared_assets) == 212
    assert set(declared_assets) == set(present_assets)
    assert all(
        asset["bytes"] == present_assets[relative].stat().st_size <= 26_214_400
        for relative, asset in declared_assets.items()
    )
    assert all(
        product["delivery"]["full_resolution_url"] is None
        for product in inventory["products"]
    )
    authoritative_movies = [
        product
        for product in inventory["products"]
        if product["delivery"]["authoritative_media_format"] == "mov"
    ]
    assert len(authoritative_movies) == 3
    assert all(
        product["web"]["media_path"].endswith(".mp4")
        for product in authoritative_movies
    )
    assert all(
        product["delivery"]["browser_media_type"] == "video/mp4"
        for product in authoritative_movies
    )

    inventory_text = json.dumps(inventory, sort_keys=True)
    assert '"archive"' not in inventory_text
    assert "source_media_path" not in inventory_text

    forbidden_references = (b"local/", b"/Users/", b"file://")
    for path in site_root.rglob("*"):
        if path.is_file():
            contents = path.read_bytes()
            assert all(reference not in contents for reference in forbidden_references)


def test_public_candidate_has_no_broken_internal_links() -> None:
    site_root = ROOT / "dist/atlas-public/site"
    link_pattern = re.compile(r'(?:href|src)="([^"]+)"')

    for page in sorted(site_root.rglob("*.html")):
        for raw_link in link_pattern.findall(page.read_text(encoding="utf-8")):
            parsed = urlsplit(raw_link)
            if parsed.scheme or parsed.netloc:
                continue
            relative_path = unquote(parsed.path)
            target = page if not relative_path else (page.parent / relative_path).resolve()
            assert target.is_relative_to(site_root.resolve()), (page, raw_link)
            assert target.is_file(), (page, raw_link)
            if parsed.fragment:
                target_text = target.read_text(encoding="utf-8")
                fragment = re.escape(unquote(parsed.fragment))
                assert re.search(rf'id=["\']{fragment}["\']', target_text), (
                    page,
                    raw_link,
                )


def test_public_candidate_renders_all_authoritative_movies_as_browser_mp4() -> None:
    quartz_page = (
        ROOT / "dist/atlas-public/site/phases/quartz.html"
    ).read_text(encoding="utf-8")
    movie_cards = re.findall(
        r'<article class="card product-card"[^>]+data-format="mov".*?</article>',
        quartz_page,
        flags=re.DOTALL,
    )

    assert len(movie_cards) == 3
    assert {
        match.group(1)
        for card in movie_cards
        if (match := re.search(r'<source src="[^"]+/([^"/]+\.mp4)"', card))
    } == {
        "quartz-x-axis-rotation-viewing-copy.mp4",
        "quartz-near-depth-identity-60fps-x-axis-rotation-web.mp4",
        "quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-web.mp4",
    }
    for card in movie_cards:
        assert re.search(r'<source src="[^"]+\.mp4" type="video/mp4">', card)
        assert ">open MP4</a>" in card
        assert "video/quicktime" not in card
        assert ">open MOV</a>" not in card


def test_archive_checksums_cover_all_artifacts_and_tracked_context() -> None:
    archive_root = ROOT / "dist/atlas-public/archive"
    artifacts = {
        path.relative_to(archive_root).as_posix()
        for path in (archive_root / "artifacts").rglob("*")
        if path.is_file()
    }
    tracked_context = {
        path.relative_to(archive_root).as_posix()
        for path in (archive_root / "tracked-context").rglob("*")
        if path.is_file()
    }
    checksummed = {
        line.split("  ", 1)[1]
        for line in (archive_root / "checksums.sha256")
        .read_text(encoding="utf-8")
        .splitlines()
    }

    assert len(artifacts) == 617
    assert len(tracked_context) == 87
    assert checksummed == artifacts | tracked_context
    assert len(checksummed) == 704


def test_pages_workflow_treats_dispatch_inputs_as_data_and_pins_actions() -> None:
    workflow_path = ROOT / ".github/workflows/deploy-atlas-pages.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)
    dispatch_inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    download_step = next(
        step
        for step in workflow["jobs"]["deploy"]["steps"]
        if step["name"] == "Download curated gallery payload"
    )

    assert download_step["env"]["RELEASE_TAG"] == "${{ inputs.release_tag }}"
    assert download_step["env"]["ASSET_GLOB"] == "${{ inputs.asset_glob }}"
    assert (
        download_step["env"]["EXPECTED_RELEASE_TAG"]
        == dispatch_inputs["release_tag"]["default"]
    )
    assert (
        download_step["env"]["EXPECTED_ASSET_GLOB"]
        == dispatch_inputs["asset_glob"]["default"]
    )
    assert (
        dispatch_inputs["release_tag"]["default"]
        == "atlas-gallery-web-0.2.0-draft.2"
    )
    assert (
        dispatch_inputs["asset_glob"]["default"]
        == "kikuchi-atlas-gallery-web-0.2.0-draft.2.zip.part-*"
    )
    assert "${{ inputs." not in download_step["run"]
    assert 'test "$RELEASE_TAG" = "$EXPECTED_RELEASE_TAG"' in download_step["run"]
    assert 'test "$ASSET_GLOB" = "$EXPECTED_ASSET_GLOB"' in download_step["run"]
    assert "set -euo pipefail" in download_step["run"]
    assert (
        '"d32d21494ae2b9b078d3e59dee7dd241c8474914ade76db7226cbb410875a514"'
        in download_step["run"]
    )
    assert (
        "uses: actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b"
        " # v5" in workflow_text
    )
    assert (
        "uses: actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda462b719fa"
        " # v3" in workflow_text
    )
    assert (
        "uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e"
        " # v4" in workflow_text
    )


def test_public_release_describes_the_125_product_site_as_pending() -> None:
    public_release = (
        ROOT / "docs/atlas/PUBLIC_RELEASE.md"
    ).read_text(encoding="utf-8").lower()

    assert "125-product candidate is pending" in public_release
    assert re.search(r"merge to\s+`master`", public_release)
    assert re.search(r"observed live\s+verification", public_release)


def test_structural_source_audit_has_one_exact_record_per_atlas_phase() -> None:
    audit = json.loads(
        (ROOT / "docs/atlas/STRUCTURAL_SOURCE_AUDIT.json").read_text(encoding="utf-8")
    )

    assert audit["schema_version"] == 1
    assert audit["source_count"] == 12
    assert {record["phase_slug"] for record in audit["sources"]} == EXPECTED_PHASE_SLUGS
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

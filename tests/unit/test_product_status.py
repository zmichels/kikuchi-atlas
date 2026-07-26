import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "product_status", ROOT / "scripts/product_status.py"
)
assert SPEC and SPEC.loader
PRODUCT_STATUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRODUCT_STATUS)
load_catalog = PRODUCT_STATUS.load_catalog


def test_product_catalog_has_unique_static_entries_and_tracked_inputs() -> None:
    entries = load_catalog(ROOT / "docs/products/ARTIFACT_CATALOG.yml")

    assert {entry["id"] for entry in entries} == {
        "forsterite-dynamical-master-x-axis",
        "forsterite-direct-reflector-depth-x-axis",
        "ice-ih-direct-reflector-depth-x-axis",
        "titanite-retained-near-depth-x-axis",
        "zircon-retained-near-depth-x-axis",
        "forsterite-reflector-ridge-globe",
        "forsterite-intensity-relief-globe",
        "five-phase-standard-vector-family",
        "quartz-direct-reflector-artist-master-x-axis",
        "quartz-near-depth-artist-master-identity-60fps",
        "quartz-near-depth-artist-master-oblique-17-31-43-60fps",
        "five-phase-orientation-gallery",
    }
    for entry in entries:
        assert (ROOT / entry["recipe"]).is_file()
        if entry["entrypoint"].startswith("scripts/"):
            assert (ROOT / entry["entrypoint"]).is_file()


def test_publishable_catalog_entries_use_canonical_packages() -> None:
    entries = load_catalog(ROOT / "docs/products/ARTIFACT_CATALOG.yml")
    by_id = {entry["id"]: entry for entry in entries}
    gallery = by_id.pop("five-phase-orientation-gallery")

    assert all(
        entry["artifact_path"] == "local/atlas/phases"
        or entry["artifact_path"].startswith("local/atlas/phases/")
        for entry in by_id.values()
    )
    assert gallery["classification"] == "historical-reproduction-evidence"
    assert gallery["state"] == "tracked-review-proof"
    assert "orientation-gallery" in gallery["artifact_path"]
    assert by_id["five-phase-standard-vector-family"]["files"] == [
        f"{phase}/products/{phase}-direct-standard/media/standard.svg"
        for phase in ("forsterite", "ice-ih", "quartz", "zircon", "titanite")
    ]
    assert by_id["quartz-direct-reflector-artist-master-x-axis"]["files"] == [
        "product-package.yml",
        "previews/preview.png",
        "media/quartz-x-axis-rotation-artist-master.mov",
        "web/quartz-x-axis-rotation-viewing-copy.mp4",
    ]
    assert by_id["quartz-near-depth-artist-master-identity-60fps"]["files"] == [
        "product-package.yml",
        "previews/preview.png",
        "media/quartz-near-depth-identity-60fps-x-axis-rotation-artist-master.mov",
        "web/quartz-near-depth-identity-60fps-x-axis-rotation-web.mp4",
    ]
    assert by_id[
        "quartz-near-depth-artist-master-oblique-17-31-43-60fps"
    ]["files"] == [
        "product-package.yml",
        "previews/preview.png",
        "media/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-artist-master.mov",
        "web/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-web.mp4",
    ]


def test_product_catalog_rejects_duplicate_identifiers(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.yml"
    catalog.write_text(
        """schema_version: 1
entries:
  - id: repeated
    tier: direct-reflector-art
    phase: ice-ih
    artifact_path: local/not-portable
    files: [preview.png]
    recipe: recipes/art/ice-ih-tattoo.yml
    entrypoint: scripts/render_phase_art_templates.py
    state: local-published
  - id: repeated
    tier: direct-reflector-art
    phase: ice-ih
    artifact_path: local/example
    files: [preview.png]
    recipe: recipes/art/ice-ih-tattoo.yml
    entrypoint: scripts/render_phase_art_templates.py
    state: local-published
"""
    )

    with pytest.raises(ValueError, match="unique non-empty strings"):
        load_catalog(catalog)


def test_product_catalog_rejects_absolute_paths(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.yml"
    catalog.write_text(
        """schema_version: 1
entries:
  - id: portable-only
    tier: direct-reflector-art
    phase: ice-ih
    artifact_path: /tmp/not-portable
    files: [preview.png]
    recipe: recipes/art/ice-ih-tattoo.yml
    entrypoint: scripts/render_phase_art_templates.py
    state: local-published
"""
    )

    with pytest.raises(ValueError, match="repository-relative"):
        load_catalog(catalog)

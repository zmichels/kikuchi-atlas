from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from kikuchi_lab.atlas.consolidation import MigrationLedger, build_migration_ledger


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for directory in (
        "docs/atlas",
        "docs/products",
        "phases/quartz",
        "recipes/demo",
        "local/legacy/frames",
    ):
        (repo / directory).mkdir(parents=True, exist_ok=True)
    (repo / "phases/quartz/source.yml").write_text("phase: quartz\n", encoding="utf-8")
    (repo / "recipes/demo/quartz.yml").write_text("phase: quartz\n", encoding="utf-8")
    (repo / "local/legacy/demo.svg").write_text("<svg>media</svg>\n", encoding="utf-8")
    (repo / "local/legacy/demo.png").write_bytes(b"png-preview")
    (repo / "local/legacy/demo.json").write_text('{"source": "fixture"}\n', encoding="utf-8")
    (repo / "local/legacy/artist.png").write_bytes(b"artist-preview")
    (repo / "local/legacy/artist.mp4").write_bytes(b"artist-web")
    (repo / "local/legacy/artist.json").write_text('{"artist": true}\n', encoding="utf-8")
    (repo / "local/legacy/frames/frame-0001.png").write_bytes(b"intermediate")

    (repo / "docs/atlas/PHASE_REGISTRY.yml").write_text(
        """\
schema_version: 1
title: Fixture phases
claim_boundary: Fixture-only registry.
phases:
  - slug: quartz
    display_name: Alpha quartz
    family: silica polymorph
    formula: SiO2
    crystal_system: trigonal
    source_status: tracked-source
    source_record: phases/quartz/source.yml
    candidate_reference:
    scope_note: Fixture quartz.
""",
        encoding="utf-8",
    )
    (repo / "docs/atlas/PRODUCT_REGISTRY.yml").write_text(
        """\
schema_version: 1
title: Fixture products
claim_boundary: Fixture-only product registry.
product_families:
  - id: demo-family
    label: Demo family
    coverage: core
    description: Fixture products.
    claim_boundary: Fixture only.
products:
  - id: quartz-a-demo
    title: Quartz demo
    phase_slugs: [quartz]
    families: [demo-family]
    format: svg
    media_path: local/legacy/demo.svg
    preview_path: local/legacy/demo.png
    bundle_path: local/legacy
    provenance_path: local/legacy/demo.json
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    tier: fixture
    state: local-published
    caption: Fixture product.
    orientation: identity
    hero: true
""",
        encoding="utf-8",
    )
    (repo / "docs/products/ARTIFACT_CATALOG.yml").write_text(
        """\
schema_version: 1
title: Fixture artifact catalog
claim_boundary: Fixture only.
entries:
  - id: quartz-artist
    tier: fixture
    phase: quartz
    artifact_path: local/legacy
    files: [artist.json, artist.png, demo.png, artist.mp4]
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    state: local-published
""",
        encoding="utf-8",
    )
    (repo / "docs/atlas/CONSOLIDATION.yml").write_text(
        """\
schema_version: 1
canonical_root: local/atlas/phases
legacy_roots:
  - local/legacy
extra_products:
  - id: quartz-artist
    title: Quartz artist master
    phase_slugs: [quartz]
    families: [demo-family]
    format: png
    media_source: local/legacy/demo.png
    preview_source: local/legacy/artist.png
    web_source: local/legacy/artist.mp4
    provenance_source: local/legacy/artist.json
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    tier: fixture
    state: local-published
    caption: Fixture intake product.
    orientation: identity
    hero: false
""",
        encoding="utf-8",
    )
    return repo


def _build_fixture_ledger(fixture_repo: Path) -> MigrationLedger:
    return build_migration_ledger(
        registry_path=fixture_repo / "docs/atlas/PHASE_REGISTRY.yml",
        product_registry_path=fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml",
        artifact_catalog_path=fixture_repo / "docs/products/ARTIFACT_CATALOG.yml",
        consolidation_path=fixture_repo / "docs/atlas/CONSOLIDATION.yml",
        source_commit="a" * 40,
    )


def test_plan_combines_registry_products_and_three_intake_products(fixture_repo: Path) -> None:
    ledger = _build_fixture_ledger(fixture_repo)
    assert ledger.phase_count == 1
    assert ledger.product_count == 2
    assert ledger.products[1].destination_root == (
        "local/atlas/phases/quartz/products/quartz-artist"
    )
    assert all(
        item.source_byte_count > 0 and len(item.source_sha256) == 64
        for item in ledger.files
    )


def test_plan_classifies_only_exact_publishable_files(fixture_repo: Path) -> None:
    ledger = _build_fixture_ledger(fixture_repo)
    paths = {item.source_path for item in ledger.files if item.source_path is not None}
    assert "local/legacy/frames/frame-0001.png" not in paths
    assert {item.role for item in ledger.files} == {
        "media", "preview", "provenance", "web"
    }
    assert all(item.cleanup_approved for item in ledger.files if item.kind == "copied")


def test_plan_rejects_same_destination_with_different_bytes(fixture_repo: Path) -> None:
    policy = fixture_repo / "docs/atlas/CONSOLIDATION.yml"
    payload = yaml.safe_load(policy.read_text(encoding="utf-8"))
    payload["extra_products"][0]["preview_destination"] = "media/demo.png"
    policy.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="destination collision"):
        _build_fixture_ledger(fixture_repo)

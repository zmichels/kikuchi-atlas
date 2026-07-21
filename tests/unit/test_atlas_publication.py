from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kikuchi_lab.atlas import build_public_atlas


def _write(path: Path, contents: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contents, bytes):
        path.write_bytes(contents)
    else:
        path.write_text(contents, encoding="utf-8")
    return path


def _fixture_repository(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    _write(root / "phases/demo/source.yml", "source: demo\n")
    _write(root / "recipes/demo.yml", "schema_version: 1\n")
    _write(root / "local/demo/line.svg", '<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    _write(root / "local/demo/preview.png", b"png-preview")
    _write(root / "local/demo/demo.stl", b"solid demo\nendsolid demo\n")
    _write(root / "local/demo/manifest.json", "{}\n")
    _write(root / "local/demo/products/canonical-kinematical-master.npz", b"master-field")
    _write(
        root / "docs/atlas/PHASE_REGISTRY.yml",
        """schema_version: 1
title: Demo Atlas
claim_boundary: demo only
phases:
  - slug: demo
    display_name: Demo
    family: demo family
    formula: X
    crystal_system: cubic
    source_status: tracked-source
    source_record: phases/demo/source.yml
    candidate_reference: null
    scope_note: a fixture phase
""",
    )
    _write(
        root / "docs/atlas/PRODUCT_REGISTRY.yml",
        """schema_version: 1
title: Demo products
claim_boundary: demo only
product_families:
  - id: direct-reflector-template
    label: Direct reflector
    coverage: core
    description: direct rendering
    claim_boundary: not a detector pattern
  - id: orientation-variation
    label: Orientation
    coverage: core
    description: orientation rendering
    claim_boundary: not a detector pattern
  - id: intensity-master
    label: Intensity master
    coverage: extension
    description: intensity-field rendering
    claim_boundary: not a detector pattern
products:
  - id: demo-line
    title: Demo line
    phase_slugs: [demo]
    families: [direct-reflector-template, orientation-variation, intensity-master]
    format: svg
    media_path: local/demo/line.svg
    preview_path: local/demo/preview.png
    bundle_path: local/demo
    provenance_path: local/demo/manifest.json
    recipe: recipes/demo.yml
    entrypoint: fixture
    tier: direct-reflector
    state: local-published
    caption: a display-safe line product
    orientation: canonical
    hero: true
  - id: demo-globe
    title: Demo globe
    phase_slugs: [demo]
    families: [direct-reflector-template]
    format: stl
    media_path: local/demo/demo.stl
    preview_path: local/demo/preview.png
    bundle_path: local/demo
    provenance_path: local/demo/manifest.json
    recipe: recipes/demo.yml
    entrypoint: fixture
    tier: reflector-ridge-globe
    state: local-published
    caption: a printable product retained for archival release
    orientation: canonical sphere
    hero: false
""",
    )
    _write(root / "docs/products/ARTIFACT_CATALOG.yml", "schema_version: 1\nentries: []\n")
    return (
        root / "docs/atlas/PHASE_REGISTRY.yml",
        root / "docs/atlas/PRODUCT_REGISTRY.yml",
        root / "docs/products/ARTIFACT_CATALOG.yml",
        root,
    )


def test_public_atlas_build_is_self_contained_and_has_an_archive_inventory(tmp_path: Path) -> None:
    registry, products, anchors, root = _fixture_repository(tmp_path)

    result = build_public_atlas(
        registry_path=registry,
        product_registry_path=products,
        anchor_catalog_path=anchors,
        output_root=root / "dist/atlas-public",
        stage_archive=True,
    )

    index = result.site_root / "index.html"
    assert index.is_file()
    assert "local/" not in index.read_text(encoding="utf-8")
    assert "/tmp/" not in index.read_text(encoding="utf-8")
    assert result.web_asset_count == 2
    assert result.archival_asset_count == 5
    assert all(path.suffix.lower() != ".stl" for path in result.web_assets)
    assert any(path.suffix.lower() == ".stl" for path in result.archive_assets)
    assert (result.site_root / "release-inventory.html").is_file()

    inventory = json.loads(result.inventory_path.read_text(encoding="utf-8"))
    products_by_id = {product["id"]: product for product in inventory["products"]}
    assert products_by_id["demo-line"]["web"]["media_path"]
    assert products_by_id["demo-globe"]["web"]["media_path"] is None
    assert products_by_id["demo-globe"]["archive"]["media_path"]
    staged_stl = result.archive_root / products_by_id["demo-globe"]["archive"]["media_path"]
    assert staged_stl.read_bytes() == b"solid demo\nendsolid demo\n"
    assert products_by_id["demo-globe"]["archive"]["media_sha256"] == hashlib.sha256(
        staged_stl.read_bytes()
    ).hexdigest()
    supplemental = products_by_id["demo-line"]["archive"]["supplemental"]
    master_digest = hashlib.sha256(b"master-field").hexdigest()
    assert supplemental == [
        {
            "path": f"artifacts/{master_digest[:16]}/canonical-kinematical-master.npz",
            "role": "canonical-kinematical-master",
            "sha256": master_digest,
        }
    ]

    stale = result.site_root / "assets/stale.txt"
    stale.write_text("stale build residue", encoding="utf-8")
    build_public_atlas(
        registry_path=registry,
        product_registry_path=products,
        anchor_catalog_path=anchors,
        output_root=result.output_root,
        stage_archive=True,
    )
    assert not stale.exists()

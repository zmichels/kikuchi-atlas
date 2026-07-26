from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

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
    package_root = root / "local/atlas/phases/demo/products/demo-movie"
    package_payloads = {
        "media/demo-master.mov": b"authoritative-mov",
        "previews/movie-preview.png": b"movie-preview",
        "web/demo-browser.mp4": b"browser-mp4",
        "provenance/original-provenance.json": b'{"source":"original"}\n',
        "provenance/scientific-fields/master-field.npz": b"scientific-field",
    }
    for relative, content in package_payloads.items():
        _write(package_root / relative, content)
    package_manifest = {
        "schema_version": 1,
        "phase_slug": "demo",
        "product_id": "demo-movie",
        "registry_id": "demo-movie",
        "source_commit": "1" * 40,
        "tracked_references": {"recipe": "recipes/demo.yml"},
        "files": [
            {
                "path": relative,
                "role": (
                    "preview"
                    if relative.startswith("previews/")
                    else relative.split("/", 1)[0]
                ),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "mime_type": "application/octet-stream",
                "destinations": ["google-drive"],
            }
            for relative, content in package_payloads.items()
        ],
    }
    _write(
        package_root / "product-package.yml",
        yaml.safe_dump(package_manifest, sort_keys=False),
    )
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
  - id: demo-movie
    title: Demo movie
    phase_slugs: [demo]
    families: [direct-reflector-template]
    format: mov
    media_path: local/atlas/phases/demo/products/demo-movie/media/demo-master.mov
    preview_path: local/atlas/phases/demo/products/demo-movie/previews/movie-preview.png
    web_path: local/atlas/phases/demo/products/demo-movie/web/demo-browser.mp4
    bundle_path: local/atlas/phases/demo/products/demo-movie
    provenance_path: local/atlas/phases/demo/products/demo-movie/product-package.yml
    recipe: recipes/demo.yml
    entrypoint: fixture
    tier: direct-reflector
    state: local-published
    caption: an authoritative movie with a browser proxy
    orientation: active
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
    assert result.web_asset_count == 4
    assert result.archival_asset_count == 11
    assert all(path.suffix.lower() != ".stl" for path in result.web_assets)
    assert any(path.suffix.lower() == ".stl" for path in result.archive_assets)
    assert all(path.suffix.lower() != ".mov" for path in result.web_assets)
    assert any(path.suffix.lower() == ".mov" for path in result.archive_assets)
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
    movie = products_by_id["demo-movie"]
    assert movie["web"]["media_path"].endswith("/demo-browser.mp4")
    assert movie["delivery"] == {
        "authoritative_media_format": "mov",
        "browser_media_path": movie["web"]["media_path"],
        "full_resolution_url": None,
    }
    package_files = {
        item["package_path"]: item for item in movie["archive"]["package_files"]
    }
    assert set(package_files) == {
        "product-package.yml",
        "media/demo-master.mov",
        "previews/movie-preview.png",
        "web/demo-browser.mp4",
        "provenance/original-provenance.json",
        "provenance/scientific-fields/master-field.npz",
    }
    assert all(item["path"] for item in package_files.values())
    assert all(
        "local/demo/products" not in path.as_posix()
        for path in result.archive_assets
    )
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


def test_public_atlas_emits_only_public_verified_full_resolution_urls(
    tmp_path: Path,
) -> None:
    registry, products, anchors, root = _fixture_repository(tmp_path)
    mirror = root / "docs/atlas/GOOGLE_MIRROR.yml"
    _write(
        mirror,
        yaml.safe_dump(
            {
                "schema_version": 1,
                "provider": "google-drive",
                "account": "zmichels@umn.edu",
                "local_mount": None,
                "transport": "undecided",
                "quota": {
                    "observed_at": None,
                    "total_bytes": None,
                    "used_bytes": None,
                    "free_bytes": None,
                    "required_headroom_bytes": 10737418240,
                },
                "root": {
                    "drive_id": None,
                    "url": None,
                    "access": "private",
                    "state": "planned",
                },
                "phases": {
                    "demo": {
                        "drive_id": None,
                        "url": None,
                        "access": "private",
                        "state": "planned",
                        "products": {
                            "demo-line": {
                                "drive_id": "private-id",
                                "url": "https://drive.google.com/drive/folders/private-id",
                                "access": "private",
                                "state": "uploaded",
                                "package_manifest_sha256": None,
                                "verified_at": None,
                            },
                            "demo-movie": {
                                "drive_id": "verified-id",
                                "url": "https://drive.google.com/drive/folders/verified-id",
                                "access": "public-link",
                                "state": "public-verified",
                                "package_manifest_sha256": None,
                                "verified_at": None,
                            },
                        },
                    }
                },
                "site": {
                    "draft_url": (
                        "https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test"
                    ),
                    "public_url": None,
                    "audience": "university-only",
                    "state": "draft",
                },
            },
            sort_keys=False,
        ),
    )

    result = build_public_atlas(
        registry_path=registry,
        product_registry_path=products,
        anchor_catalog_path=anchors,
        output_root=root / "dist/atlas-public",
        mirror_registry_path=mirror,
    )

    inventory_text = result.inventory_path.read_text(encoding="utf-8")
    inventory = json.loads(inventory_text)
    by_id = {item["id"]: item for item in inventory["products"]}
    assert by_id["demo-line"]["delivery"]["full_resolution_url"] is None
    assert (
        by_id["demo-movie"]["delivery"]["full_resolution_url"]
        == "https://drive.google.com/drive/folders/verified-id"
    )
    pages = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(result.site_root.rglob("*.html"))
    )
    assert "https://drive.google.com/drive/folders/private-id" not in pages
    assert "https://drive.google.com/drive/folders/private-id" not in inventory_text
    assert "https://drive.google.com/drive/folders/verified-id" in pages
    assert pages.count(">open full-resolution package<") == 2

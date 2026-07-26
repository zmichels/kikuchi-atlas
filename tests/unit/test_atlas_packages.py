from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.atlas.packages import (
    load_phase_package,
    load_product_package,
    validate_phase_package,
    validate_product_package,
)


def _write_product(root: Path, *, digest: str | None = None) -> Path:
    media = root / "media/demo.png"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"demo")
    manifest = {
        "schema_version": 1,
        "phase_slug": "quartz",
        "product_id": "quartz-demo",
        "registry_id": "quartz-demo",
        "source_commit": "a" * 40,
        "tracked_references": {
            "phase_source": "phases/quartz/source.yml",
            "recipe": "recipes/reflectors/quartz-art-bands.yml",
            "product_registry": "docs/atlas/PRODUCT_REGISTRY.yml",
        },
        "files": [{
            "path": "media/demo.png",
            "role": "media",
            "bytes": 4,
            "sha256": digest or sha256(b"demo").hexdigest(),
            "mime_type": "image/png",
            "destinations": ["google-drive"],
        }],
    }
    path = root / "product-package.yml"
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return path


def test_product_package_validates_exact_files_and_identity(tmp_path: Path) -> None:
    package = validate_product_package(_write_product(tmp_path / "quartz-demo"))
    assert package.product_id == "quartz-demo"
    assert package.files[0].role == "media"
    assert package.package_sha256


def test_product_package_rejects_tampered_bytes(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo", digest="0" * 64)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_product_package(path)


def test_product_package_rejects_absolute_escape_and_symlink(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["files"][0]["path"] = "/Users/Z/demo.png"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="relative"):
        validate_product_package(path)


def test_phase_package_binds_product_manifest_digest(tmp_path: Path) -> None:
    product_path = _write_product(tmp_path / "phase/products/quartz-demo")
    product = validate_product_package(product_path)
    phase_path = tmp_path / "phase/phase-package.yml"
    phase_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "phase_slug": "quartz",
        "source_record": "phases/quartz/source.yml",
        "products": [{
            "product_id": "quartz-demo",
            "manifest": "products/quartz-demo/product-package.yml",
            "manifest_sha256": product.package_sha256,
        }],
    }, sort_keys=False), encoding="utf-8")
    assert validate_phase_package(phase_path).product_ids == ("quartz-demo",)


def test_load_product_package_rejects_unknown_schema_keys(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["extra"] = "not allowed"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="top-level keys"):
        load_product_package(path)


def test_load_product_package_rejects_invalid_file_metadata(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["files"][0]["destinations"] = ["google-drive", "google-drive"]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate destinations"):
        load_product_package(path)


def test_validate_product_package_rejects_symlinks_and_hard_links(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo")
    media = path.parent / "media/demo.png"
    target = path.parent / "target.png"
    target.write_bytes(b"demo")
    media.unlink()
    media.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        validate_product_package(path)

    media.unlink()
    os.link(target, media)
    with pytest.raises(ValueError, match="hard link"):
        validate_product_package(path)


def test_validate_product_package_rejects_symlinked_package_directories(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo")
    media = path.parent / "media"
    (media / "demo.png").unlink()
    media.rmdir()
    external_media = tmp_path / "external-media"
    external_media.mkdir()
    (external_media / "demo.png").write_bytes(b"demo")
    media.symlink_to(external_media, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        validate_product_package(path)


def test_validate_product_package_rejects_symlinked_package_root(tmp_path: Path) -> None:
    actual_root = tmp_path / "actual-package"
    _write_product(actual_root)
    linked_root = tmp_path / "quartz-demo"
    linked_root.symlink_to(actual_root, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        validate_product_package(linked_root / "product-package.yml")


def test_validate_product_package_rejects_wrong_repo_layout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "pyproject.toml").parent.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    path = _write_product(repo / "quartz-demo")

    with pytest.raises(ValueError, match="canonical package directory"):
        validate_product_package(path)


def test_load_phase_package_requires_canonical_product_manifest_path(tmp_path: Path) -> None:
    product_path = _write_product(tmp_path / "phase/products/quartz-demo")
    product = validate_product_package(product_path)
    phase_path = tmp_path / "phase/phase-package.yml"
    phase_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "phase_slug": "quartz",
        "source_record": "phases/quartz/source.yml",
        "products": [{
            "product_id": "quartz-demo",
            "manifest": "products/not-quartz/product-package.yml",
            "manifest_sha256": product.package_sha256,
        }],
    }, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="must be"):
        load_phase_package(phase_path)


def test_validate_phase_package_rejects_identity_and_digest_mismatch(tmp_path: Path) -> None:
    product_path = _write_product(tmp_path / "phase/products/quartz-demo")
    product = validate_product_package(product_path)
    phase_path = tmp_path / "phase/phase-package.yml"
    phase_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "phase_slug": "quartz",
        "source_record": "phases/quartz/source.yml",
        "products": [{
            "product_id": "quartz-demo",
            "manifest": "products/quartz-demo/product-package.yml",
            "manifest_sha256": "0" * 64,
        }],
    }, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest SHA-256 mismatch"):
        validate_phase_package(phase_path)

    phase_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "phase_slug": "feldspar",
        "source_record": "phases/feldspar/source.yml",
        "products": [{
            "product_id": "quartz-demo",
            "manifest": "products/quartz-demo/product-package.yml",
            "manifest_sha256": product.package_sha256,
        }],
    }, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="phase slug mismatch"):
        validate_phase_package(phase_path)

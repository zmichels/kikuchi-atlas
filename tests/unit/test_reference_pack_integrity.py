from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from kikuchi_lab.reference_pack.integrity import (
    SourceInventoryManifest,
    load_source_inventory_manifest,
    verify_exact_source_inventory,
)


def _record(name: str, payload: bytes) -> dict[str, object]:
    return {
        "name": name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _manifest(files: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "unit-test-source-inventory",
        "source": {"license": "CC-BY-4.0"},
        "files": files,
    }


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_verifies_exact_inventory_with_bytes_and_sha256(tmp_path: Path) -> None:
    first = b"first source value\n"
    second = b"second source value\n"
    source_root = tmp_path / "source"
    _write(source_root / "first.dat", first)
    _write(source_root / "second.bmp", second)
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(_manifest([_record("first.dat", first), _record("second.bmp", second)])),
        encoding="utf-8",
    )

    manifest = load_source_inventory_manifest(manifest_path)
    result = verify_exact_source_inventory(source_root, manifest)

    assert isinstance(manifest, SourceInventoryManifest)
    assert result.file_count == 2
    assert result.total_bytes == len(first) + len(second)
    assert result.manifest_id == "unit-test-source-inventory"


def test_rejects_missing_unexpected_or_modified_sources(tmp_path: Path) -> None:
    expected = b"expected"
    source_root = tmp_path / "source"
    _write(source_root / "expected.dat", expected)
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(json.dumps(_manifest([_record("expected.dat", expected)])), encoding="utf-8")
    manifest = load_source_inventory_manifest(manifest_path)

    _write(source_root / "untracked.dat", b"extra")
    with pytest.raises(ValueError, match="unexpected"):
        verify_exact_source_inventory(source_root, manifest)

    (source_root / "untracked.dat").unlink()
    _write(source_root / "expected.dat", b"modified")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_exact_source_inventory(source_root, manifest)

    (source_root / "expected.dat").unlink()
    with pytest.raises(ValueError, match="missing"):
        verify_exact_source_inventory(source_root, manifest)


def test_rejects_duplicate_or_noncanonical_manifest_records(tmp_path: Path) -> None:
    payload = b"source"
    bad_manifest = _manifest([_record("one.dat", payload), _record("one.dat", payload)])
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_source_inventory_manifest(manifest_path)

    bad_manifest = _manifest([_record("nested/one.dat", payload)])
    manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="plain filenames"):
        load_source_inventory_manifest(manifest_path)

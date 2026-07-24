"""Strict, dependency-free verification for externally hosted source files."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePath
import re
from typing import Any, Mapping


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourceFileFingerprint:
    """One exact source file expected from an external data provider."""

    name: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceInventoryManifest:
    """Versioned source inventory retained without copying the source data."""

    manifest_id: str
    source: Mapping[str, object]
    files: tuple[SourceFileFingerprint, ...]


@dataclass(frozen=True)
class SourceInventoryVerification:
    """Successful exact-inventory verification result."""

    manifest_id: str
    source_root: Path
    file_count: int
    total_bytes: int


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a regular file without loading it at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _as_nonempty_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _parse_file_record(value: object) -> SourceFileFingerprint:
    record = _as_mapping(value, field="source inventory file record")
    name = _as_nonempty_string(record.get("name"), field="source inventory file name")
    if PurePath(name).name != name or name in {".", ".."}:
        raise ValueError("source inventory file names must be plain filenames")
    byte_count = record.get("bytes")
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
        raise ValueError("source inventory file bytes must be a non-negative integer")
    sha256 = _as_nonempty_string(record.get("sha256"), field="source inventory file sha256")
    if not _SHA256.fullmatch(sha256):
        raise ValueError("source inventory file sha256 must be a lowercase SHA-256 digest")
    return SourceFileFingerprint(name=name, bytes=byte_count, sha256=sha256)


def source_inventory_manifest_from_mapping(value: object) -> SourceInventoryManifest:
    """Validate and normalize the portable source-inventory JSON schema."""
    document = _as_mapping(value, field="source inventory manifest")
    if document.get("schema_version") != 1:
        raise ValueError("source inventory manifest must declare schema_version 1")
    manifest_id = _as_nonempty_string(document.get("id"), field="source inventory manifest id")
    source = _as_mapping(document.get("source"), field="source inventory manifest source")
    records = document.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("source inventory manifest files must be a non-empty list")
    files = tuple(_parse_file_record(record) for record in records)
    names = tuple(record.name for record in files)
    if len(names) != len(set(names)):
        raise ValueError("source inventory manifest contains duplicate file names")
    if names != tuple(sorted(names)):
        raise ValueError("source inventory manifest file names must be lexicographically sorted")
    return SourceInventoryManifest(manifest_id=manifest_id, source=dict(source), files=files)


def load_source_inventory_manifest(path: str | Path) -> SourceInventoryManifest:
    """Load and validate one source-inventory manifest from JSON."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"source inventory manifest is not valid JSON: {path}") from error
    return source_inventory_manifest_from_mapping(value)


def verify_exact_source_inventory(
    source_root: str | Path,
    manifest: SourceInventoryManifest,
) -> SourceInventoryVerification:
    """Require exact source names, byte sizes, and checksums at *source_root*."""
    root = Path(source_root)
    if not root.is_dir():
        raise ValueError(f"source inventory directory does not exist: {root}")
    actual_names = {path.name for path in root.iterdir() if path.is_file()}
    expected_names = {record.name for record in manifest.files}
    missing = sorted(expected_names - actual_names)
    if missing:
        raise ValueError(f"source inventory missing expected files: {', '.join(missing)}")
    unexpected = sorted(actual_names - expected_names)
    if unexpected:
        raise ValueError(f"source inventory contains unexpected files: {', '.join(unexpected)}")
    for record in manifest.files:
        path = root / record.name
        actual_bytes = path.stat().st_size
        if actual_bytes != record.bytes:
            raise ValueError(
                f"source inventory byte-size mismatch for {record.name}: "
                f"{actual_bytes} != {record.bytes}"
            )
        actual_sha256 = sha256_file(path)
        if actual_sha256 != record.sha256:
            raise ValueError(f"source inventory checksum mismatch for {record.name}")
    return SourceInventoryVerification(
        manifest_id=manifest.manifest_id,
        source_root=root.resolve(),
        file_count=len(manifest.files),
        total_bytes=sum(record.bytes for record in manifest.files),
    )

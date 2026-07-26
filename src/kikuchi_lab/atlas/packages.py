"""Immutable on-disk contracts for canonical Atlas product packages."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping

import yaml


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_ROLES = {"media", "preview", "web", "provenance"}
_ROLE_DIRECTORIES = {
    "media": "media",
    "preview": "previews",
    "web": "web",
    "provenance": "provenance",
}
_DESTINATIONS = {"github-pages", "google-drive"}
_PRODUCT_FIELDS = {
    "schema_version",
    "phase_slug",
    "product_id",
    "registry_id",
    "source_commit",
    "tracked_references",
    "files",
}
_PACKAGE_FILE_FIELDS = {"path", "role", "bytes", "sha256", "mime_type", "destinations"}
_PHASE_FIELDS = {"schema_version", "phase_slug", "source_record", "products"}
_PHASE_PRODUCT_FIELDS = {"product_id", "manifest", "manifest_sha256"}


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it all into memory."""
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mapping(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} top-level keys differ from the package schema")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _relative(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("file://"):
        raise ValueError(f"{label} must be a package-relative path")
    return path


def _digest(value: object, label: str) -> str:
    text = _text(value, label)
    if not _SHA256.fullmatch(text):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return text


def _manifest_path(path: str | Path) -> Path:
    return Path(path).resolve(strict=False)


def _read_yaml(path: Path, label: str) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"{label} cannot be read as YAML") from error


def _repository_root(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def _has_canonical_anchor(path: Path) -> bool:
    parts = path.parts
    return any(parts[index : index + 3] == ("local", "atlas", "phases") for index in range(len(parts)))


def _validate_product_location(manifest_path: Path, phase_slug: str, product_id: str) -> None:
    expected = ("local", "atlas", "phases", phase_slug, "products", product_id)
    root = _repository_root(manifest_path.parent)
    if root is not None:
        parent_parts = manifest_path.parent.relative_to(root).parts
    elif _has_canonical_anchor(manifest_path.parent):
        parent_parts = manifest_path.parent.parts[-len(expected) :]
    else:
        return
    if parent_parts != expected:
        raise ValueError("product manifest is not in the canonical package directory")


def _validate_phase_location(manifest_path: Path, phase_slug: str) -> None:
    expected = ("local", "atlas", "phases", phase_slug)
    root = _repository_root(manifest_path.parent)
    if root is not None:
        parent_parts = manifest_path.parent.relative_to(root).parts
    elif _has_canonical_anchor(manifest_path.parent):
        parent_parts = manifest_path.parent.parts[-len(expected) :]
    else:
        return
    if parent_parts != expected:
        raise ValueError("phase manifest is not in the canonical phase directory")


def _validate_regular_file(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    try:
        metadata = path.stat()
    except OSError as error:
        raise ValueError(f"{label} is missing") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label} must be a regular file")
    if metadata.st_nlink != 1:
        raise ValueError(f"{label} must not be a hard link")


def _validate_package_root(manifest_path: Path, label: str) -> None:
    package_root = manifest_path.absolute().parent
    if package_root != package_root.resolve(strict=False):
        raise ValueError(f"{label} must not traverse a symlink")


def _package_file_path(package_root: Path, relative_path: PurePosixPath) -> Path:
    path = package_root
    for component in relative_path.parts:
        path /= component
        if path.is_symlink():
            raise ValueError(f"package file {relative_path} must not traverse a symlink")
    return path


@dataclass(frozen=True)
class PackageFile:
    relative_path: PurePosixPath
    role: str
    byte_count: int
    sha256: str
    mime_type: str
    destinations: tuple[str, ...]


@dataclass(frozen=True)
class ProductPackage:
    manifest_path: Path
    phase_slug: str
    product_id: str
    registry_id: str
    source_commit: str
    tracked_references: Mapping[str, str]
    files: tuple[PackageFile, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "tracked_references", MappingProxyType(dict(self.tracked_references)))

    @property
    def package_sha256(self) -> str:
        identity = {
            "phase_slug": self.phase_slug,
            "product_id": self.product_id,
            "registry_id": self.registry_id,
            "source_commit": self.source_commit,
            "tracked_references": dict(self.tracked_references),
            "files": [
                {
                    "path": item.relative_path.as_posix(),
                    "role": item.role,
                    "bytes": item.byte_count,
                    "sha256": item.sha256,
                    "mime_type": item.mime_type,
                    "destinations": list(item.destinations),
                }
                for item in self.files
            ],
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PhasePackage:
    manifest_path: Path
    phase_slug: str
    source_record: str
    product_ids: tuple[str, ...]
    manifest_sha256_by_product: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "manifest_sha256_by_product",
            MappingProxyType(dict(self.manifest_sha256_by_product)),
        )


def _package_file(value: object) -> PackageFile:
    raw = _mapping(value, _PACKAGE_FILE_FIELDS, "package file")
    relative_path = _relative(raw["path"], "package file path")
    role = _text(raw["role"], "package file role")
    if role not in _ROLES:
        raise ValueError("package file role is unsupported")
    if not relative_path.parts or relative_path.parts[0] != _ROLE_DIRECTORIES[role]:
        raise ValueError("package file path does not match its role directory")
    byte_count = raw["bytes"]
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
        raise ValueError("package file bytes must be a non-negative integer")
    digest = _digest(raw["sha256"], "package file SHA-256")
    mime_type = _text(raw["mime_type"], "package file MIME type")
    raw_destinations = raw["destinations"]
    if not isinstance(raw_destinations, list) or not raw_destinations:
        raise ValueError("package file destinations must be a non-empty list")
    destinations = tuple(_text(item, "package file destination") for item in raw_destinations)
    if len(set(destinations)) != len(destinations):
        raise ValueError("package file destinations must not contain duplicate destinations")
    if set(destinations) - _DESTINATIONS:
        raise ValueError("package file destinations contain an unsupported destination")
    return PackageFile(
        relative_path=relative_path,
        role=role,
        byte_count=byte_count,
        sha256=digest,
        mime_type=mime_type,
        destinations=destinations,
    )


def load_product_package(path: str | Path) -> ProductPackage:
    """Parse a product manifest into an immutable package contract."""
    manifest_path = _manifest_path(path)
    if manifest_path.name != "product-package.yml":
        raise ValueError("product manifest filename must be product-package.yml")
    raw = _mapping(_read_yaml(manifest_path, "product manifest"), _PRODUCT_FIELDS, "product manifest")
    if raw["schema_version"] != 1:
        raise ValueError("unsupported product package schema")
    phase_slug = _text(raw["phase_slug"], "product phase_slug")
    product_id = _text(raw["product_id"], "product product_id")
    registry_id = _text(raw["registry_id"], "product registry_id")
    source_commit = _text(raw["source_commit"], "product source_commit")
    if not _COMMIT.fullmatch(source_commit):
        raise ValueError("product source_commit must be a lowercase Git commit")
    raw_references = raw["tracked_references"]
    if not isinstance(raw_references, dict) or not raw_references:
        raise ValueError("product tracked_references must be a non-empty mapping")
    tracked_references = {
        _text(key, "tracked reference name"): _relative(value, "tracked reference path").as_posix()
        for key, value in raw_references.items()
    }
    if len(tracked_references) != len(raw_references):
        raise ValueError("product tracked_references must not repeat names")
    raw_files = raw["files"]
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("product files must be a non-empty list")
    files = tuple(_package_file(item) for item in raw_files)
    paths = tuple(item.relative_path for item in files)
    path_roles = tuple((item.relative_path, item.role) for item in files)
    if len(set(path_roles)) != len(path_roles):
        raise ValueError("product files must not repeat roles for the same path")
    if len(set(paths)) != len(paths):
        raise ValueError("product files must not repeat paths")
    return ProductPackage(
        manifest_path=manifest_path,
        phase_slug=phase_slug,
        product_id=product_id,
        registry_id=registry_id,
        source_commit=source_commit,
        tracked_references=tracked_references,
        files=files,
    )


def validate_product_package(path: str | Path) -> ProductPackage:
    """Parse a product package and verify its package tree byte-for-byte."""
    source_path = Path(path)
    _validate_regular_file(source_path, "product manifest")
    _validate_package_root(source_path, "product manifest")
    package = load_product_package(source_path)
    _validate_product_location(package.manifest_path, package.phase_slug, package.product_id)
    for item in package.files:
        file_path = _package_file_path(package.manifest_path.parent, item.relative_path)
        _validate_regular_file(file_path, f"package file {item.relative_path}")
        if file_path.stat().st_size != item.byte_count:
            raise ValueError(f"byte-count mismatch for package file {item.relative_path}")
        if sha256_file(file_path) != item.sha256:
            raise ValueError(f"SHA-256 mismatch for package file {item.relative_path}")
    _validate_role_payload_inventory(package)
    return package


def _validate_role_payload_inventory(package: ProductPackage) -> None:
    package_root = package.manifest_path.parent
    declared_paths = {item.relative_path for item in package.files}
    for directory in _ROLE_DIRECTORIES.values():
        role_root = package_root / directory
        if not role_root.exists():
            continue
        if role_root.is_symlink():
            raise ValueError(f"package role directory {directory} must not be a symlink")
        for root, directories, filenames in os.walk(role_root, followlinks=False):
            current = Path(root)
            for name in directories:
                if (current / name).is_symlink():
                    raise ValueError(f"package role directory {directory} must not traverse a symlink")
            for name in filenames:
                payload = current / name
                if payload.is_symlink():
                    raise ValueError(f"package file {payload.relative_to(package_root)} must not be a symlink")
                if not payload.is_file():
                    raise ValueError(f"package file {payload.relative_to(package_root)} must be a regular file")
                relative_path = PurePosixPath(payload.relative_to(package_root).as_posix())
                if relative_path not in declared_paths:
                    raise ValueError(f"unmanifested payload: {relative_path}")


def load_phase_package(path: str | Path) -> PhasePackage:
    """Parse a phase package manifest and enforce its product-reference shape."""
    manifest_path = _manifest_path(path)
    if manifest_path.name != "phase-package.yml":
        raise ValueError("phase manifest filename must be phase-package.yml")
    raw = _mapping(_read_yaml(manifest_path, "phase manifest"), _PHASE_FIELDS, "phase manifest")
    if raw["schema_version"] != 1:
        raise ValueError("unsupported phase package schema")
    phase_slug = _text(raw["phase_slug"], "phase phase_slug")
    source_record = _relative(raw["source_record"], "phase source_record").as_posix()
    raw_products = raw["products"]
    if not isinstance(raw_products, list) or not raw_products:
        raise ValueError("phase products must be a non-empty list")
    product_ids: list[str] = []
    digests: dict[str, str] = {}
    for value in raw_products:
        product = _mapping(value, _PHASE_PRODUCT_FIELDS, "phase product")
        product_id = _text(product["product_id"], "phase product_id")
        manifest = _relative(product["manifest"], "phase product manifest")
        expected_manifest = PurePosixPath("products") / product_id / "product-package.yml"
        if manifest != expected_manifest:
            raise ValueError("phase product manifest must be products/<id>/product-package.yml")
        product_ids.append(product_id)
        digests[product_id] = _digest(product["manifest_sha256"], "phase product manifest_sha256")
    if len(set(product_ids)) != len(product_ids):
        raise ValueError("phase products must not repeat product IDs")
    return PhasePackage(
        manifest_path=manifest_path,
        phase_slug=phase_slug,
        source_record=source_record,
        product_ids=tuple(product_ids),
        manifest_sha256_by_product=digests,
    )


def validate_phase_package(path: str | Path) -> PhasePackage:
    """Verify all product packages bound into one phase package."""
    source_path = Path(path)
    _validate_regular_file(source_path, "phase manifest")
    _validate_package_root(source_path, "phase manifest")
    package = load_phase_package(source_path)
    _validate_phase_location(package.manifest_path, package.phase_slug)
    for product_id in package.product_ids:
        product_path = package.manifest_path.parent / "products" / product_id / "product-package.yml"
        product = validate_product_package(product_path)
        if product.phase_slug != package.phase_slug:
            raise ValueError(f"phase slug mismatch for product {product_id}")
        if product.product_id != product_id:
            raise ValueError(f"product ID mismatch for product {product_id}")
        if product.package_sha256 != package.manifest_sha256_by_product[product_id]:
            raise ValueError(f"manifest SHA-256 mismatch for product {product_id}")
    return package

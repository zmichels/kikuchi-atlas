"""Deterministically plan legacy Atlas artifacts into canonical packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import importlib.util
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
from typing import Any

import yaml

from .catalog import AtlasProduct, load_phase_registry, load_product_registry
from .packages import (
    ProductPackage,
    sha256_file,
    validate_phase_package,
    validate_product_package,
)
from .web_proxy import WEB_PROXY_PROFILE, build_web_proxy, validate_web_proxy


_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_POLICY_FIELDS = {"schema_version", "canonical_root", "legacy_roots", "extra_products"}
_LEDGER_FIELDS = {
    "schema_version",
    "state",
    "source_commit",
    "canonical_root",
    "retained_source_paths",
    "phase_count",
    "product_count",
    "products",
    "files",
}
_LEDGER_PRODUCT_FIELDS = {
    "product_id",
    "phase_slug",
    "destination_root",
    "registry_record",
}
_LEDGER_FILE_FIELDS = {
    "product_id",
    "phase_slug",
    "source_path",
    "destination_path",
    "role",
    "kind",
    "source_byte_count",
    "source_sha256",
    "destination_byte_count",
    "destination_sha256",
    "mime_type",
    "destinations",
    "cleanup_approved",
}
_CANONICAL_ROOT = PurePosixPath("local/atlas/phases")
_ROLE_DIRECTORIES = {
    "media": "media",
    "preview": "previews",
    "web": "web",
    "provenance": "provenance",
}
_EXTRA_REQUIRED_FIELDS = {
    "id",
    "title",
    "phase_slugs",
    "families",
    "format",
    "media_source",
    "preview_source",
    "provenance_source",
    "recipe",
    "entrypoint",
    "tier",
    "state",
    "caption",
    "orientation",
    "hero",
}
_EXTRA_OPTIONAL_FIELDS = {
    "media_destination",
    "preview_destination",
    "web_source",
    "web_destination",
    "web_transform",
    "provenance_destination",
}
_MIME_TYPES = {
    ".json": "application/json",
    ".md": "text/markdown",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
    ".npz": "application/octet-stream",
    ".png": "image/png",
    ".stl": "model/stl",
    ".svg": "image/svg+xml",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
}
_WEB_SUFFIXES = {".jpeg", ".jpg", ".mp4", ".png", ".svg"}
_MAX_WEB_BYTES = 25 * 1024 * 1024
_PUBLICATION_PATH_FIELDS = {
    "media_path",
    "preview_path",
    "web_path",
    "bundle_path",
    "provenance_path",
}
_ALLOWED_REFERENCE_CLASSIFICATIONS = {
    "nonpublishable-scientific-input",
    "historical-reproduction-evidence",
}
_REQUIRED_QUARTZ_INTAKE_IDS = {
    "quartz-direct-reflector-artist-master-x-axis",
    "quartz-near-depth-artist-master-identity-60fps",
    "quartz-near-depth-artist-master-oblique-17-31-43-60fps",
}


def _load_catalog(path: Path) -> list[dict[str, Any]]:
    """Load the standalone catalog validator without making scripts a package."""
    script = Path(__file__).resolve().parents[3] / "scripts/product_status.py"
    spec = importlib.util.spec_from_file_location("_kikuchi_product_status", script)
    if spec is None or spec.loader is None:
        raise ValueError("scripts.product_status.load_catalog is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_catalog(path)


@dataclass(frozen=True)
class MigrationFile:
    product_id: str
    phase_slug: str
    source_path: str | None
    destination_path: str
    role: str
    kind: str
    source_byte_count: int
    source_sha256: str
    destination_byte_count: int | None
    destination_sha256: str | None
    mime_type: str
    destinations: tuple[str, ...]
    cleanup_approved: bool


@dataclass(frozen=True)
class MigrationProduct:
    product_id: str
    phase_slug: str
    destination_root: str
    registry_record: dict[str, object]


@dataclass(frozen=True)
class MigrationLedger:
    state: str
    source_commit: str
    canonical_root: str
    retained_source_paths: tuple[str, ...]
    products: tuple[MigrationProduct, ...]
    files: tuple[MigrationFile, ...]

    @property
    def product_count(self) -> int:
        return len(self.products)

    @property
    def phase_count(self) -> int:
        return len({item.phase_slug for item in self.products})


@dataclass(frozen=True)
class CanonicalVerification:
    """Summary of an exact canonical-tree verification pass."""

    phase_count: int
    product_count: int
    missing_count: int
    mismatched_count: int
    symlink_count: int

    @property
    def valid(self) -> bool:
        return not (self.missing_count or self.mismatched_count or self.symlink_count)


@dataclass(frozen=True)
class RegistryRewriteResult:
    """Summary of one validated, atomic registry cutover."""

    product_count: int
    available_count: int
    legacy_path_count: int


@dataclass(frozen=True)
class LegacyPathAuditResult:
    """Summary of tracked legacy-path references after registry cutover."""

    publishable_legacy_reference_count: int
    allowed_reference_count: int


def _read_policy(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("consolidation policy cannot be read as YAML") from error
    if not isinstance(payload, dict) or set(payload) != _POLICY_FIELDS:
        raise ValueError("consolidation policy fields differ from schema")
    if payload["schema_version"] != 1:
        raise ValueError("unsupported consolidation policy schema")
    if not isinstance(payload["canonical_root"], str) or not payload["canonical_root"]:
        raise ValueError("canonical_root must be non-empty text")
    roots = payload["legacy_roots"]
    if (
        not isinstance(roots, list)
        or not roots
        or not all(isinstance(item, str) and item for item in roots)
        or len(set(roots)) != len(roots)
    ):
        raise ValueError("legacy_roots must contain unique non-empty paths")
    extras = payload["extra_products"]
    if not isinstance(extras, list):
        raise ValueError("extra_products must be a list")
    return payload


def _relative_path(value: str, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a repository-relative path")
    return path


def _source_path(
    root: Path,
    relative_value: str,
    *,
    approved_roots: tuple[tuple[PurePosixPath, Path], ...],
) -> Path:
    relative = _relative_path(relative_value, "migration source")
    if not any(
        relative == declared or relative.is_relative_to(declared)
        for declared, _ in approved_roots
    ):
        raise ValueError(f"source path is outside approved legacy roots: {relative_value}")
    source = root / relative
    if source.is_symlink():
        raise ValueError(f"migration source must not be a symlink: {relative_value}")
    try:
        resolved_source = source.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"migration source is missing: {relative_value}") from error
    if not resolved_source.is_file():
        raise ValueError(f"migration source is missing: {relative_value}")
    if not any(
        resolved_source == approved or resolved_source.is_relative_to(approved)
        for _, approved in approved_roots
    ):
        raise ValueError(f"source path is outside approved legacy roots: {relative_value}")
    return source


def _mime_type(path: PurePosixPath) -> str:
    known = _MIME_TYPES.get(path.suffix.lower())
    if known is not None:
        return known
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _destinations(role: str, source: Path | None) -> tuple[str, ...]:
    if role == "web":
        return ("github-pages", "google-drive")
    if (
        role in {"media", "preview"}
        and source is not None
        and source.suffix.lower() in _WEB_SUFFIXES
        and source.stat().st_size <= _MAX_WEB_BYTES
    ):
        return ("github-pages", "google-drive")
    return ("google-drive",)


def _registry_record(product: AtlasProduct, root: Path) -> dict[str, object]:
    def relative(path: Path | None) -> str | None:
        return path.relative_to(root).as_posix() if path is not None else None

    return {
        "id": product.identifier,
        "title": product.title,
        "phase_slugs": list(product.phase_slugs),
        "families": list(product.family_ids),
        "format": product.media_format,
        "media_path": relative(product.media_path),
        "preview_path": relative(product.preview_path),
        "web_path": relative(product.web_path),
        "bundle_path": relative(product.bundle_path),
        "provenance_path": relative(product.provenance_path),
        "recipe": product.recipe,
        "entrypoint": product.entrypoint,
        "tier": product.tier,
        "state": product.state,
        "caption": product.caption,
        "orientation": product.orientation,
        "hero": product.hero,
    }


def _extra_registry_record(extra: dict[str, Any]) -> dict[str, object]:
    media_source = str(extra["media_source"])
    web_source = extra.get("web_source")
    web_transform = extra.get("web_transform")
    web_path: str | None = str(web_source) if web_source is not None else None
    if web_transform is not None:
        web_path = str(web_transform["filename"])
    return {
        "id": extra["id"],
        "title": extra["title"],
        "phase_slugs": list(extra["phase_slugs"]),
        "families": list(extra["families"]),
        "format": extra["format"],
        "media_path": media_source,
        "preview_path": extra["preview_source"],
        "web_path": web_path,
        "bundle_path": PurePosixPath(media_source).parent.as_posix(),
        "provenance_path": extra["provenance_source"],
        "recipe": extra["recipe"],
        "entrypoint": extra["entrypoint"],
        "tier": extra["tier"],
        "state": extra["state"],
        "caption": extra["caption"],
        "orientation": extra["orientation"],
        "hero": extra["hero"],
    }


def _release_metadata(
    *,
    product_id: str,
    phase_slug: str,
    source_commit: str,
    registry_record: dict[str, object],
) -> bytes:
    payload = {
        "schema_version": 1,
        "product_id": product_id,
        "phase_slug": phase_slug,
        "source_commit": source_commit,
        "registry_record": registry_record,
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).encode("utf-8")


def _add_copy(
    files: list[MigrationFile],
    *,
    root: Path,
    approved_roots: tuple[tuple[PurePosixPath, Path], ...],
    product_id: str,
    phase_slug: str,
    destination_root: PurePosixPath,
    source_value: str,
    destination_relative: str,
    role: str,
) -> None:
    source = _source_path(root, source_value, approved_roots=approved_roots)
    relative_destination = _relative_path(destination_relative, "migration destination")
    destination = destination_root / relative_destination
    digest = sha256_file(source)
    size = source.stat().st_size
    files.append(
        MigrationFile(
            product_id=product_id,
            phase_slug=phase_slug,
            source_path=source_value,
            destination_path=destination.as_posix(),
            role=role,
            kind="copied",
            source_byte_count=size,
            source_sha256=digest,
            destination_byte_count=size,
            destination_sha256=digest,
            mime_type=_mime_type(PurePosixPath(source_value)),
            destinations=_destinations(role, source),
            cleanup_approved=True,
        )
    )


def _supplemental_sources(
    product: AtlasProduct,
    root: Path,
    bundle_value: str,
) -> tuple[tuple[str, str], ...]:
    sources: list[tuple[str, str]] = []
    bundle = _relative_path(bundle_value, "atlas product bundle_path")
    if "intensity-master" in product.family_ids:
        master_relative = bundle / "products/canonical-kinematical-master.npz"
        master = root / master_relative
        if master.is_file():
            sources.append(
                (
                    master_relative.as_posix(),
                    "provenance/scientific-fields/canonical-kinematical-master.npz",
                )
            )
    if "intensity-relief-globe" in product.family_ids:
        relief_relative = bundle / "relief-field.npz"
        relief = root / relief_relative
        if relief.is_file():
            sources.append(
                (
                    relief_relative.as_posix(),
                    "provenance/scientific-fields/relief-field.npz",
                )
            )
    return tuple(sources)


def _validate_extra(
    extra: object,
    *,
    phase_slugs: set[str],
    family_ids: set[str],
    catalog_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(extra, dict):
        raise ValueError("extra product must be a mapping")
    fields = set(extra)
    if not _EXTRA_REQUIRED_FIELDS <= fields or not fields <= _EXTRA_REQUIRED_FIELDS | _EXTRA_OPTIONAL_FIELDS:
        raise ValueError("extra product fields differ from schema")
    product_id = extra["id"]
    if not isinstance(product_id, str) or not product_id:
        raise ValueError("extra product id must be non-empty text")
    phases = extra["phase_slugs"]
    if not isinstance(phases, list) or len(phases) != 1 or phases[0] not in phase_slugs:
        raise ValueError(f"extra product {product_id!r} must name exactly one registered phase")
    families = extra["families"]
    if (
        not isinstance(families, list)
        or not families
        or not all(isinstance(item, str) and item in family_ids for item in families)
    ):
        raise ValueError(f"extra product {product_id!r} refers to unknown families")
    catalog = catalog_by_id.get(product_id)
    if catalog is None:
        raise ValueError(f"extra product {product_id!r} is absent from the artifact catalog")
    catalog_phases = catalog["phase"]
    if isinstance(catalog_phases, str):
        catalog_phases = [catalog_phases]
    if catalog_phases != phases:
        raise ValueError(f"extra product {product_id!r} phase differs from artifact catalog")
    if "web_source" in extra and "web_transform" in extra:
        raise ValueError(f"extra product {product_id!r} cannot declare two web outputs")
    transform = extra.get("web_transform")
    if transform is not None and (
        not isinstance(transform, dict)
        or set(transform) != {"profile", "filename"}
        or not all(isinstance(value, str) and value for value in transform.values())
    ):
        raise ValueError(f"extra product {product_id!r} has invalid web_transform")
    if not isinstance(extra["hero"], bool):
        raise ValueError(f"extra product {product_id!r} hero must be boolean")
    return extra


def _check_destination_collisions(files: list[MigrationFile]) -> None:
    by_destination: dict[str, str] = {}
    for item in files:
        existing = by_destination.get(item.destination_path)
        if existing is not None and existing != item.source_sha256:
            raise ValueError(f"destination collision with different bytes: {item.destination_path}")
        by_destination[item.destination_path] = item.source_sha256


def validate_migration_output_path(
    output_path: str | Path,
    consolidation_path: str | Path,
    registry_path: str | Path,
) -> None:
    """Reject plan output paths that could mutate the canonical package tree."""
    policy_path = Path(consolidation_path).resolve()
    policy = _read_policy(policy_path)
    repository_root = Path(registry_path).resolve().parents[2]
    canonical_root = (
        repository_root / _relative_path(policy["canonical_root"], "canonical_root")
    ).resolve(strict=False)
    resolved_output = Path(output_path).resolve(strict=False)
    if resolved_output == canonical_root or resolved_output.is_relative_to(canonical_root):
        raise ValueError(
            f"migration output must be outside the canonical root: {resolved_output}"
        )


def build_migration_ledger(
    registry_path: str | Path,
    product_registry_path: str | Path,
    artifact_catalog_path: str | Path,
    consolidation_path: str | Path,
    source_commit: str,
) -> MigrationLedger:
    """Build a frozen migration plan without creating canonical package files."""
    if not _COMMIT.fullmatch(source_commit):
        raise ValueError("source_commit must be a lowercase 40-character Git commit")
    registry = Path(registry_path).resolve()
    product_registry = Path(product_registry_path).resolve()
    root = registry.parents[2]
    if product_registry.parents[2] != root:
        raise ValueError("registry inputs must share a repository root")
    phases = load_phase_registry(registry)
    phase_slugs = {phase.slug for phase in phases}
    phase_source_by_slug = {phase.slug: phase.source_record for phase in phases}
    families, registry_products = load_product_registry(product_registry, phase_slugs=phase_slugs)
    raw_product_payload = yaml.safe_load(product_registry.read_text(encoding="utf-8"))
    raw_product_by_id = {
        item["id"]: item
        for item in raw_product_payload["products"]
    }
    family_ids = {family.identifier for family in families}
    catalog = _load_catalog(Path(artifact_catalog_path).resolve())
    catalog_by_id = {entry["id"]: entry for entry in catalog}
    policy = _read_policy(Path(consolidation_path).resolve())
    canonical_root = _relative_path(policy["canonical_root"], "canonical_root")
    approved_roots = tuple(
        (
            _relative_path(value, "legacy root"),
            (root / _relative_path(value, "legacy root")).resolve(strict=False),
        )
        for value in policy["legacy_roots"]
    )

    products: list[MigrationProduct] = []
    files: list[MigrationFile] = []
    seen_ids: set[str] = set()

    for product in registry_products:
        if len(product.phase_slugs) != 1:
            raise ValueError(
                f"product {product.identifier!r} must resolve to exactly one phase for package ownership"
            )
        product_id = product.identifier
        phase_slug = product.phase_slugs[0]
        raw_product = raw_product_by_id[product_id]
        seen_ids.add(product_id)
        destination_root = canonical_root / phase_slug / "products" / product_id
        record = _registry_record(product, root)
        products.append(
            MigrationProduct(
                product_id=product_id,
                phase_slug=phase_slug,
                destination_root=destination_root.as_posix(),
                registry_record=record,
            )
        )
        for role, source_field, directory in (
            ("media", "media_path", "media"),
            ("preview", "preview_path", "previews"),
            ("provenance", "provenance_path", "provenance"),
        ):
            source_value = raw_product.get(source_field)
            if source_value is not None:
                source_value = str(source_value)
                _add_copy(
                    files,
                    root=root,
                    approved_roots=approved_roots,
                    product_id=product_id,
                    phase_slug=phase_slug,
                    destination_root=destination_root,
                    source_value=source_value,
                    destination_relative=(
                        f"{directory}/{PurePosixPath(source_value).name}"
                    ),
                    role=role,
                )
        for source_value, destination_relative in _supplemental_sources(
            product,
            root,
            str(raw_product["bundle_path"]),
        ):
            _add_copy(
                files,
                root=root,
                approved_roots=approved_roots,
                product_id=product_id,
                phase_slug=phase_slug,
                destination_root=destination_root,
                source_value=source_value,
                destination_relative=destination_relative,
                role="provenance",
            )
        metadata = _release_metadata(
            product_id=product_id,
            phase_slug=phase_slug,
            source_commit=source_commit,
            registry_record=record,
        )
        metadata_digest = sha256(metadata).hexdigest()
        files.append(
            MigrationFile(
                product_id=product_id,
                phase_slug=phase_slug,
                source_path=None,
                destination_path=(
                    destination_root / "provenance/release-metadata.yml"
                ).as_posix(),
                role="provenance",
                kind="generated-metadata",
                source_byte_count=len(metadata),
                source_sha256=metadata_digest,
                destination_byte_count=len(metadata),
                destination_sha256=metadata_digest,
                mime_type="text/yaml",
                destinations=("google-drive",),
                cleanup_approved=False,
            )
        )

    extras = [
        _validate_extra(
            item,
            phase_slugs=phase_slugs,
            family_ids=family_ids,
            catalog_by_id=catalog_by_id,
        )
        for item in policy["extra_products"]
    ]
    for extra in extras:
        product_id = str(extra["id"])
        if product_id in seen_ids:
            raise ValueError(f"duplicate product id: {product_id}")
        seen_ids.add(product_id)
        phase_slug = str(extra["phase_slugs"][0])
        destination_root = canonical_root / phase_slug / "products" / product_id
        record = _extra_registry_record(extra)
        products.append(
            MigrationProduct(
                product_id=product_id,
                phase_slug=phase_slug,
                destination_root=destination_root.as_posix(),
                registry_record=record,
            )
        )
        for role, source_field, destination_field, directory in (
            ("media", "media_source", "media_destination", "media"),
            ("preview", "preview_source", "preview_destination", "previews"),
            ("provenance", "provenance_source", "provenance_destination", "provenance"),
            ("web", "web_source", "web_destination", "web"),
        ):
            source_value = extra.get(source_field)
            if source_value is None:
                continue
            source_name = PurePosixPath(str(source_value)).name
            destination_relative = str(extra.get(destination_field, f"{directory}/{source_name}"))
            _add_copy(
                files,
                root=root,
                approved_roots=approved_roots,
                product_id=product_id,
                phase_slug=phase_slug,
                destination_root=destination_root,
                source_value=str(source_value),
                destination_relative=destination_relative,
                role=role,
            )
        transform = extra.get("web_transform")
        if transform is not None:
            source_value = str(extra["media_source"])
            source = _source_path(root, source_value, approved_roots=approved_roots)
            digest = sha256_file(source)
            files.append(
                MigrationFile(
                    product_id=product_id,
                    phase_slug=phase_slug,
                    source_path=source_value,
                    destination_path=(
                        destination_root / "web" / str(transform["filename"])
                    ).as_posix(),
                    role="web",
                    kind="generated-proxy",
                    source_byte_count=source.stat().st_size,
                    source_sha256=digest,
                    destination_byte_count=None,
                    destination_sha256=None,
                    mime_type="video/mp4",
                    destinations=("github-pages", "google-drive"),
                    cleanup_approved=False,
                )
            )
        metadata = _release_metadata(
            product_id=product_id,
            phase_slug=phase_slug,
            source_commit=source_commit,
            registry_record=record,
        )
        metadata_digest = sha256(metadata).hexdigest()
        files.append(
            MigrationFile(
                product_id=product_id,
                phase_slug=phase_slug,
                source_path=None,
                destination_path=(
                    destination_root / "provenance/release-metadata.yml"
                ).as_posix(),
                role="provenance",
                kind="generated-metadata",
                source_byte_count=len(metadata),
                source_sha256=metadata_digest,
                destination_byte_count=len(metadata),
                destination_sha256=metadata_digest,
                mime_type="text/yaml",
                destinations=("google-drive",),
                cleanup_approved=False,
            )
        )

    _check_destination_collisions(files)
    sorted_products = tuple(sorted(products, key=lambda item: (item.phase_slug, item.product_id)))
    sorted_files = tuple(
        sorted(
            files,
            key=lambda item: (
                item.phase_slug,
                item.product_id,
                item.role,
                item.destination_path,
            ),
        )
    )
    if any(phase_source_by_slug[item.phase_slug] is None for item in sorted_products):
        raise ValueError("migration products require tracked phase source records")
    return MigrationLedger(
        state="planned",
        source_commit=source_commit,
        canonical_root=canonical_root.as_posix(),
        retained_source_paths=(),
        products=sorted_products,
        files=sorted_files,
    )


def write_migration_ledger(ledger: MigrationLedger, output_path: str | Path) -> None:
    """Write a deterministic YAML migration ledger."""
    product_by_id = {item.product_id: item for item in ledger.products}
    file_records: list[dict[str, object]] = []
    for item in ledger.files:
        record = asdict(item)
        record["destinations"] = list(item.destinations)
        if item.kind == "generated-metadata":
            product = product_by_id[item.product_id]
            content = _release_metadata(
                product_id=item.product_id,
                phase_slug=item.phase_slug,
                source_commit=ledger.source_commit,
                registry_record=product.registry_record,
            ).decode("utf-8")
            if sha256(content.encode("utf-8")).hexdigest() != item.source_sha256:
                raise ValueError("generated metadata no longer matches its planned SHA-256")
            record["generated_content"] = content
        file_records.append(record)
    payload = {
        "schema_version": 1,
        "state": ledger.state,
        "source_commit": ledger.source_commit,
        "canonical_root": ledger.canonical_root,
        "retained_source_paths": list(ledger.retained_source_paths),
        "phase_count": ledger.phase_count,
        "product_count": ledger.product_count,
        "products": [asdict(item) for item in ledger.products],
        "files": file_records,
    }
    output = Path(output_path)
    output.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _load_migration_ledger(path: Path) -> MigrationLedger:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("migration ledger cannot be read as YAML") from error
    if not isinstance(payload, dict) or set(payload) != _LEDGER_FIELDS:
        raise ValueError("migration ledger fields differ from schema")
    if payload["schema_version"] != 1:
        raise ValueError("unsupported migration ledger schema")
    if payload["state"] not in {"planned", "materialized"}:
        raise ValueError("migration ledger state must be planned or materialized")
    if not isinstance(payload["source_commit"], str) or not _COMMIT.fullmatch(
        payload["source_commit"]
    ):
        raise ValueError("migration ledger source_commit is invalid")
    canonical_root = _relative_path(payload["canonical_root"], "canonical_root")
    if canonical_root != _CANONICAL_ROOT:
        raise ValueError("migration ledger canonical_root must be local/atlas/phases")
    raw_retained_source_paths = payload["retained_source_paths"]
    if (
        not isinstance(raw_retained_source_paths, list)
        or not all(
            isinstance(item, str) and item for item in raw_retained_source_paths
        )
        or len(set(raw_retained_source_paths)) != len(raw_retained_source_paths)
    ):
        raise ValueError(
            "migration ledger retained_source_paths must contain unique paths"
        )
    retained_source_paths = tuple(
        _relative_path(value, "retained source path").as_posix()
        for value in raw_retained_source_paths
    )

    raw_products = payload["products"]
    if not isinstance(raw_products, list):
        raise ValueError("migration ledger products must be a list")
    products: list[MigrationProduct] = []
    for raw in raw_products:
        if not isinstance(raw, dict) or set(raw) != _LEDGER_PRODUCT_FIELDS:
            raise ValueError("migration ledger product fields differ from schema")
        if not isinstance(raw["registry_record"], dict):
            raise ValueError("migration ledger registry_record must be a mapping")
        products.append(
            MigrationProduct(
                product_id=str(raw["product_id"]),
                phase_slug=str(raw["phase_slug"]),
                destination_root=str(raw["destination_root"]),
                registry_record=dict(raw["registry_record"]),
            )
        )
    if len({item.product_id for item in products}) != len(products):
        raise ValueError("migration ledger products contain duplicate IDs")

    raw_files = payload["files"]
    if not isinstance(raw_files, list):
        raise ValueError("migration ledger files must be a list")
    files: list[MigrationFile] = []
    for raw in raw_files:
        if not isinstance(raw, dict):
            raise ValueError("migration ledger file must be a mapping")
        fields = set(raw)
        kind = raw.get("kind")
        expected_fields = set(_LEDGER_FILE_FIELDS)
        if kind == "generated-metadata":
            expected_fields.add("generated_content")
        if fields != expected_fields:
            raise ValueError("migration ledger file fields differ from schema")
        source_sha256 = raw["source_sha256"]
        destination_sha256 = raw["destination_sha256"]
        if not isinstance(source_sha256, str) or not _SHA256.fullmatch(source_sha256):
            raise ValueError("migration ledger source SHA-256 is invalid")
        if destination_sha256 is not None and (
            not isinstance(destination_sha256, str)
            or not _SHA256.fullmatch(destination_sha256)
        ):
            raise ValueError("migration ledger destination SHA-256 is invalid")
        destinations = raw["destinations"]
        if not isinstance(destinations, list) or not all(
            isinstance(item, str) for item in destinations
        ):
            raise ValueError("migration ledger destinations must be a list of text")
        files.append(
            MigrationFile(
                product_id=str(raw["product_id"]),
                phase_slug=str(raw["phase_slug"]),
                source_path=(
                    None if raw["source_path"] is None else str(raw["source_path"])
                ),
                destination_path=str(raw["destination_path"]),
                role=str(raw["role"]),
                kind=str(kind),
                source_byte_count=int(raw["source_byte_count"]),
                source_sha256=source_sha256,
                destination_byte_count=(
                    None
                    if raw["destination_byte_count"] is None
                    else int(raw["destination_byte_count"])
                ),
                destination_sha256=destination_sha256,
                mime_type=str(raw["mime_type"]),
                destinations=tuple(destinations),
                cleanup_approved=bool(raw["cleanup_approved"]),
            )
        )
        if kind == "generated-metadata":
            generated_content = raw["generated_content"]
            if not isinstance(generated_content, str):
                raise ValueError("generated metadata content must be text")
            if len(generated_content.encode("utf-8")) != int(raw["source_byte_count"]):
                raise ValueError("generated metadata byte count changed")
            if sha256(generated_content.encode("utf-8")).hexdigest() != source_sha256:
                raise ValueError("generated metadata SHA-256 changed")

    ledger = MigrationLedger(
        state=str(payload["state"]),
        source_commit=payload["source_commit"],
        canonical_root=canonical_root.as_posix(),
        retained_source_paths=retained_source_paths,
        products=tuple(products),
        files=tuple(files),
    )
    if payload["phase_count"] != ledger.phase_count:
        raise ValueError("migration ledger phase_count is inconsistent")
    if payload["product_count"] != ledger.product_count:
        raise ValueError("migration ledger product_count is inconsistent")
    product_ids = {item.product_id for item in ledger.products}
    if any(item.product_id not in product_ids for item in ledger.files):
        raise ValueError("migration ledger file refers to an unknown product")
    null_outputs = [
        item
        for item in ledger.files
        if item.destination_byte_count is None or item.destination_sha256 is None
    ]
    if any(
        item.kind != "generated-proxy"
        or item.destination_byte_count is not None
        or item.destination_sha256 is not None
        for item in null_outputs
    ):
        raise ValueError("only generated proxies may have null destination identity")
    if ledger.state == "materialized" and null_outputs:
        raise ValueError("materialized ledger contains a null destination identity")
    return ledger


def _assert_path_below(path: PurePosixPath, parent: PurePosixPath, label: str) -> None:
    if path == parent or not path.is_relative_to(parent):
        raise ValueError(f"{label} must be below {parent}")


def _assert_real_directory(path: Path, *, anchor: Path) -> None:
    relative = path.relative_to(anchor)
    current = anchor
    if current.is_symlink():
        raise ValueError(f"canonical directory must not be a symlink: {current}")
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise ValueError(f"canonical directory must not be a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"canonical directory path is not a directory: {current}")
        current.mkdir(exist_ok=True)


def _validate_source_identity(
    source: Path,
    *,
    expected_byte_count: int,
    expected_sha256: str,
) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"source must be a regular file: {source}")
    if source.stat().st_size != expected_byte_count:
        raise ValueError(f"source byte count changed since planning: {source}")
    if sha256_file(source) != expected_sha256:
        raise ValueError(f"source SHA-256 changed since planning: {source}")


def _clone_or_copy_verified(
    source: Path,
    destination: Path,
    expected_sha256: str,
) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"source must be a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if (
            destination.is_symlink()
            or not destination.is_file()
            or destination.stat().st_nlink != 1
            or sha256_file(destination) != expected_sha256
        ):
            raise ValueError(
                f"refusing to overwrite different destination: {destination}"
            )
        return
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists() or partial.is_symlink():
        if partial.is_symlink() or not partial.is_file():
            raise ValueError(f"unsafe partial destination: {partial}")
        partial.unlink()
    cloned = (
        subprocess.run(
            ["cp", "-c", str(source), str(partial)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    if not cloned:
        shutil.copy2(source, partial)
    if partial.is_symlink() or not partial.is_file() or partial.stat().st_nlink != 1:
        if partial.exists() and partial.is_file() and not partial.is_symlink():
            partial.unlink()
        raise ValueError(f"copy did not produce an independent regular file: {destination}")
    if partial.stat().st_size != source.stat().st_size:
        partial.unlink()
        raise ValueError(f"byte-count mismatch after copy: {destination}")
    if sha256_file(partial) != expected_sha256:
        partial.unlink()
        raise ValueError(f"SHA-256 mismatch after copy: {destination}")
    os.replace(partial, destination)


def _publish_bytes_verified(content: bytes, destination: Path) -> None:
    expected_sha256 = sha256(content).hexdigest()
    if destination.exists() or destination.is_symlink():
        if (
            destination.is_symlink()
            or not destination.is_file()
            or destination.stat().st_nlink != 1
            or destination.stat().st_size != len(content)
            or sha256_file(destination) != expected_sha256
        ):
            raise ValueError(
                f"refusing to overwrite different destination: {destination}"
            )
        return
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists() or partial.is_symlink():
        if partial.is_symlink() or not partial.is_file():
            raise ValueError(f"unsafe partial destination: {partial}")
        partial.unlink()
    partial.write_bytes(content)
    if (
        partial.is_symlink()
        or partial.stat().st_nlink != 1
        or partial.stat().st_size != len(content)
        or sha256_file(partial) != expected_sha256
    ):
        partial.unlink()
        raise ValueError(f"generated content verification failed: {destination}")
    os.replace(partial, destination)


def _product_manifest(
    ledger: MigrationLedger,
    product: MigrationProduct,
    files: tuple[MigrationFile, ...],
) -> bytes:
    destination_root = PurePosixPath(product.destination_root)
    records: list[dict[str, object]] = []
    for item in sorted(
        files,
        key=lambda value: (
            value.role,
            PurePosixPath(value.destination_path).relative_to(destination_root).as_posix(),
        ),
    ):
        relative_path = PurePosixPath(item.destination_path).relative_to(destination_root)
        if item.destination_byte_count is None or item.destination_sha256 is None:
            raise ValueError(f"destination identity is incomplete: {item.destination_path}")
        records.append(
            {
                "path": relative_path.as_posix(),
                "role": item.role,
                "bytes": item.destination_byte_count,
                "sha256": item.destination_sha256,
                "mime_type": item.mime_type,
                "destinations": list(item.destinations),
            }
        )
    recipe = product.registry_record.get("recipe")
    if not isinstance(recipe, str) or not recipe:
        raise ValueError(f"product recipe is missing: {product.product_id}")
    payload = {
        "schema_version": 1,
        "phase_slug": product.phase_slug,
        "product_id": product.product_id,
        "registry_id": product.product_id,
        "source_commit": ledger.source_commit,
        "tracked_references": {
            "phase_source": f"phases/{product.phase_slug}/source.yml",
            "recipe": recipe,
            "product_registry": "docs/atlas/PRODUCT_REGISTRY.yml",
        },
        "files": records,
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).encode("utf-8")


def _phase_manifest(
    phase_slug: str,
    products: tuple[ProductPackage, ...],
) -> bytes:
    payload = {
        "schema_version": 1,
        "phase_slug": phase_slug,
        "source_record": f"phases/{phase_slug}/source.yml",
        "products": [
            {
                "product_id": product.product_id,
                "manifest": f"products/{product.product_id}/product-package.yml",
                "manifest_sha256": product.package_sha256,
            }
            for product in sorted(products, key=lambda item: item.product_id)
        ],
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).encode("utf-8")


def _expected_tree(
    ledger: MigrationLedger,
    root: Path,
) -> tuple[set[Path], set[Path]]:
    canonical = root / ledger.canonical_root
    expected_directories = {canonical}
    expected_files: set[Path] = set()
    for product in ledger.products:
        product_root = root / product.destination_root
        phase_root = canonical / product.phase_slug
        expected_directories.update(
            {
                phase_root,
                phase_root / "products",
                product_root,
                *(product_root / directory for directory in _ROLE_DIRECTORIES.values()),
            }
        )
        expected_files.add(product_root / "product-package.yml")
        expected_files.add(phase_root / "phase-package.yml")
    for item in ledger.files:
        destination = root / item.destination_path
        expected_files.add(destination)
        parent = destination.parent
        while parent != canonical and parent.is_relative_to(canonical):
            expected_directories.add(parent)
            parent = parent.parent
    return expected_directories, expected_files


def _verify_canonical_tree(
    ledger: MigrationLedger,
    repository_root: Path,
) -> CanonicalVerification:
    canonical = repository_root / ledger.canonical_root
    expected_directories, expected_files = _expected_tree(ledger, repository_root)
    missing: set[Path] = set()
    mismatched: set[Path] = set()
    symlinks: set[Path] = set()

    if not canonical.exists():
        missing.update(expected_directories)
        missing.update(expected_files)
    else:
        actual_directories = {canonical}
        actual_files: set[Path] = set()
        for current_value, directory_names, filenames in os.walk(
            canonical,
            followlinks=False,
        ):
            current = Path(current_value)
            for name in directory_names:
                path = current / name
                if path.is_symlink():
                    symlinks.add(path)
                else:
                    actual_directories.add(path)
            for name in filenames:
                path = current / name
                if path.is_symlink():
                    symlinks.add(path)
                else:
                    actual_files.add(path)
                    try:
                        metadata = path.stat()
                    except OSError:
                        mismatched.add(path)
                    else:
                        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                            mismatched.add(path)
        missing.update(expected_directories - actual_directories)
        missing.update(expected_files - actual_files)
        mismatched.update(actual_directories - expected_directories)
        mismatched.update(actual_files - expected_files)

    files_by_product: dict[str, list[MigrationFile]] = {
        product.product_id: [] for product in ledger.products
    }
    for item in ledger.files:
        files_by_product[item.product_id].append(item)
    for product in ledger.products:
        manifest = repository_root / product.destination_root / "product-package.yml"
        if manifest not in expected_files or not manifest.is_file() or manifest.is_symlink():
            continue
        try:
            package = validate_product_package(manifest)
        except ValueError as error:
            if "symlink" in str(error):
                symlinks.add(manifest)
            else:
                mismatched.add(manifest)
            continue
        expected_file_identity = {
            (
                PurePosixPath(item.destination_path)
                .relative_to(PurePosixPath(product.destination_root))
                .as_posix(),
                item.role,
                item.destination_byte_count,
                item.destination_sha256,
                item.mime_type,
                item.destinations,
            )
            for item in files_by_product[product.product_id]
        }
        actual_file_identity = {
            (
                item.relative_path.as_posix(),
                item.role,
                item.byte_count,
                item.sha256,
                item.mime_type,
                item.destinations,
            )
            for item in package.files
        }
        if expected_file_identity != actual_file_identity:
            mismatched.add(manifest)
            continue
        if (
            package.phase_slug != product.phase_slug
            or package.product_id != product.product_id
            or package.registry_id != product.product_id
            or package.source_commit != ledger.source_commit
        ):
            mismatched.add(manifest)
            continue
    for phase_slug in sorted({item.phase_slug for item in ledger.products}):
        manifest = canonical / phase_slug / "phase-package.yml"
        if not manifest.is_file() or manifest.is_symlink():
            continue
        try:
            phase = validate_phase_package(manifest)
        except ValueError as error:
            if "symlink" in str(error):
                symlinks.add(manifest)
            else:
                mismatched.add(manifest)
            continue
        expected_ids = tuple(
            sorted(
                item.product_id
                for item in ledger.products
                if item.phase_slug == phase_slug
            )
        )
        if (
            phase.phase_slug != phase_slug
            or phase.source_record != f"phases/{phase_slug}/source.yml"
            or phase.product_ids != expected_ids
        ):
            mismatched.add(manifest)

    return CanonicalVerification(
        phase_count=ledger.phase_count,
        product_count=ledger.product_count,
        missing_count=len(missing),
        mismatched_count=len(mismatched),
        symlink_count=len(symlinks),
    )


def verify_canonical_tree(
    ledger_path: str | Path,
    repository_root: str | Path,
) -> CanonicalVerification:
    """Verify exact packages, manifests, bytes, links, and tree inventory."""
    ledger = _load_migration_ledger(Path(ledger_path))
    return _verify_canonical_tree(ledger, Path(repository_root).resolve())


def _load_yaml_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"{label} cannot be read as YAML") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a mapping")
    return payload


def _canonical_registry_record(
    product: MigrationProduct,
    files: tuple[MigrationFile, ...],
    source_record: dict[str, Any],
) -> dict[str, Any]:
    role_paths: dict[str, list[str]] = {}
    for item in files:
        role_paths.setdefault(item.role, []).append(item.destination_path)
    for role in role_paths:
        role_paths[role].sort()
    if len(role_paths.get("media", [])) != 1:
        raise ValueError(
            f"ledger product {product.product_id!r} must have exactly one authoritative media file"
        )
    if len(role_paths.get("preview", [])) > 1 or len(role_paths.get("web", [])) > 1:
        raise ValueError(
            f"ledger product {product.product_id!r} has ambiguous preview or web media"
        )

    record = dict(source_record)
    media_path = role_paths["media"][0]
    media_format = record.get("format")
    if media_format != PurePosixPath(media_path).suffix.lower().lstrip("."):
        raise ValueError(
            f"ledger product {product.product_id!r} format differs from authoritative media"
        )
    record["media_path"] = media_path
    if role_paths.get("preview"):
        record["preview_path"] = role_paths["preview"][0]
    else:
        record.pop("preview_path", None)
    web_paths = role_paths.get("web", [])
    if web_paths:
        if PurePosixPath(media_path).suffix.lower() in _WEB_SUFFIXES:
            raise ValueError(
                f"ledger product {product.product_id!r} declares a redundant web copy"
            )
        record["web_path"] = web_paths[0]
    else:
        record.pop("web_path", None)
    record["bundle_path"] = product.destination_root
    record["provenance_path"] = (
        PurePosixPath(product.destination_root) / "product-package.yml"
    ).as_posix()
    return record


def _publication_legacy_path_count(
    records: list[dict[str, Any]],
    legacy_roots: tuple[PurePosixPath, ...],
) -> int:
    count = 0
    for record in records:
        for field in _PUBLICATION_PATH_FIELDS:
            value = record.get(field)
            if value is None:
                continue
            path = _relative_path(str(value), f"atlas product {field}")
            if any(path == root or path.is_relative_to(root) for root in legacy_roots):
                count += 1
    return count


def _registry_cutover_order(
    original_ids: tuple[str, ...],
    ledger_ids: set[str],
    intake_ids: tuple[str, ...],
) -> tuple[str, ...]:
    original = set(original_ids)
    intake = set(intake_ids)
    present_intakes = original & intake
    if present_intakes and present_intakes != intake:
        raise ValueError("tracked registry contains a partially applied intake set")
    if present_intakes == intake:
        expected = original
        ordered = original_ids
    else:
        expected = original | intake
        ordered = original_ids + intake_ids
    if ledger_ids != expected:
        raise ValueError("ledger ids differ from the tracked registry plus intake products")
    return ordered


def rewrite_product_registry(
    *,
    ledger_path: str | Path,
    product_registry_path: str | Path,
    consolidation_path: str | Path,
    repository_root: str | Path,
) -> RegistryRewriteResult:
    """Validate all canonical packages before atomically cutting over the registry."""
    root = Path(repository_root).resolve()
    ledger = _load_migration_ledger(Path(ledger_path))
    if ledger.state != "materialized":
        raise ValueError("registry rewrite requires a materialized migration ledger")
    if ledger.canonical_root != _CANONICAL_ROOT.as_posix():
        raise ValueError("registry rewrite requires the canonical Atlas root")
    if ledger.phase_count != 12 or ledger.product_count != 125:
        raise ValueError("registry rewrite requires exactly 12 phases and 125 products")
    verification = _verify_canonical_tree(ledger, root)
    if not verification.valid:
        raise ValueError(
            "registry rewrite requires a verified canonical tree: "
            f"missing={verification.missing_count} "
            f"mismatched={verification.mismatched_count} "
            f"symlinks={verification.symlink_count}"
        )

    products_path = Path(product_registry_path).resolve()
    if products_path.parents[2] != root:
        raise ValueError("product registry must be rooted in the target repository")
    payload = _load_yaml_mapping(products_path, "atlas product registry")
    raw_products = payload.get("products")
    if not isinstance(raw_products, list) or not all(
        isinstance(item, dict) for item in raw_products
    ):
        raise ValueError("atlas product registry products must be mappings")
    original_by_id = {str(item.get("id")): item for item in raw_products}
    if len(original_by_id) != len(raw_products):
        raise ValueError("atlas product registry ids must be unique")

    policy = _read_policy(Path(consolidation_path).resolve())
    extras = policy["extra_products"]
    extra_ids = tuple(str(item.get("id")) for item in extras if isinstance(item, dict))
    if set(extra_ids) != _REQUIRED_QUARTZ_INTAKE_IDS or len(extra_ids) != 3:
        raise ValueError("registry rewrite requires the three quartz intake products")
    ledger_by_id = {item.product_id: item for item in ledger.products}
    ordered_ids = _registry_cutover_order(
        tuple(str(item["id"]) for item in raw_products),
        set(ledger_by_id),
        extra_ids,
    )

    files_by_product = {
        product_id: tuple(item for item in ledger.files if item.product_id == product_id)
        for product_id in ledger_by_id
    }
    rewritten_by_id: dict[str, dict[str, Any]] = {}
    for product_id, product in ledger_by_id.items():
        frozen_record = product.registry_record
        if product_id in original_by_id:
            source_record = original_by_id[product_id]
            for field, value in source_record.items():
                if field not in _PUBLICATION_PATH_FIELDS and frozen_record.get(field) != value:
                    raise ValueError(
                        f"ledger metadata differs from tracked product {product_id!r}: {field}"
                    )
        else:
            source_record = frozen_record
        record = _canonical_registry_record(
            product,
            files_by_product[product_id],
            source_record,
        )
        if record.get("id") != product_id:
            raise ValueError(f"ledger registry id differs from product id: {product_id}")
        rewritten_by_id[product_id] = record

    rewritten_products = [rewritten_by_id[product_id] for product_id in ordered_ids]
    legacy_roots = tuple(
        _relative_path(value, "legacy root") for value in policy["legacy_roots"]
    )
    legacy_path_count = _publication_legacy_path_count(
        rewritten_products,
        legacy_roots,
    )
    if legacy_path_count:
        raise ValueError(
            f"generated registry contains {legacy_path_count} legacy publication paths"
        )

    generated_payload = dict(payload)
    generated_payload["products"] = rewritten_products
    generated = products_path.with_name(products_path.name + ".generated")
    try:
        generated.write_text(
            yaml.safe_dump(generated_payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        phases = load_phase_registry(root / "docs/atlas/PHASE_REGISTRY.yml")
        _, products = load_product_registry(
            generated,
            phase_slugs={phase.slug for phase in phases},
        )
        available_count = sum(product.is_available() for product in products)
        if len(products) != 125 or available_count != 125:
            raise ValueError(
                "generated registry failed availability validation: "
                f"products={len(products)} available={available_count}"
            )
        mov_products = {
            product.identifier: product
            for product in products
            if product.media_format == "mov"
        }
        if set(mov_products) != _REQUIRED_QUARTZ_INTAKE_IDS or any(
            product.web_path is None
            or product.web_path.suffix.lower() != ".mp4"
            for product in mov_products.values()
        ):
            raise ValueError(
                "generated registry must expose the three quartz MOV products "
                "with MP4 web copies"
            )
        os.replace(generated, products_path)
    except Exception:
        generated.unlink(missing_ok=True)
        raise
    return RegistryRewriteResult(
        product_count=125,
        available_count=125,
        legacy_path_count=legacy_path_count,
    )


def _tracked_paths(root: Path) -> tuple[PurePosixPath, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return tuple(
        PurePosixPath(value.decode("utf-8"))
        for value in result.stdout.split(b"\0")
        if value
    )


def _is_audit_excluded(path: PurePosixPath, excluded_files: set[str]) -> bool:
    value = path.as_posix()
    return value in excluded_files or value.startswith(
        ("docs/superpowers/plans/", "docs/superpowers/specs/")
    )


def _audit_input_paths(root: Path) -> tuple[PurePosixPath, ...]:
    paths = set(_tracked_paths(root))
    generated_site = root / "docs/atlas/site"
    if generated_site.is_dir():
        paths.update(
            PurePosixPath(path.relative_to(root).as_posix())
            for path in generated_site.rglob("*")
            if path.is_file()
        )
    return tuple(sorted(paths))


def _legacy_roots_from_ledger(ledger: MigrationLedger) -> tuple[str, ...]:
    roots: set[str] = set()
    for item in ledger.files:
        if item.source_path is None:
            continue
        parts = PurePosixPath(item.source_path).parts
        if len(parts) >= 2 and parts[0] == "local":
            roots.add(PurePosixPath(*parts[:2]).as_posix())
    if not roots:
        raise ValueError("migration ledger does not identify any legacy roots")
    return tuple(sorted(roots, key=lambda value: (-len(value), value)))


def _line_legacy_paths(line: str, legacy_roots: tuple[str, ...]) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for root in legacy_roots:
        pattern = re.compile(re.escape(root) + r"[A-Za-z0-9._{}<>/\-]*")
        matches.extend(
            (match.start(), match.group(0).rstrip(".,;:"))
            for match in pattern.finditer(line)
        )
    return tuple(value for _, value in sorted(set(matches)))


def _allowed_reference(
    *,
    file: PurePosixPath,
    line_text: str,
    legacy_path: str,
    source_paths: tuple[PurePosixPath, ...],
    orientation_gallery_root: PurePosixPath | None,
) -> tuple[str, str] | None:
    value = file.as_posix()
    legacy = PurePosixPath(legacy_path)
    if (
        value.startswith("local/atlas/phases/")
        and "/products/" in value
        and "/provenance/" in value
        and file.name in {"manifest.json", "release-metadata.yml"}
    ):
        return (
            "historical-reproduction-evidence",
            "Canonical package provenance preserves the verified source-run path while publication resolves through canonical product paths.",
        )
    if value == "docs/products/ARTIFACT_CATALOG.yml":
        if orientation_gallery_root is not None and (
            legacy == orientation_gallery_root
            or legacy.is_relative_to(orientation_gallery_root)
        ):
            return (
                "historical-reproduction-evidence",
                "The review-only orientation gallery remains historical evidence and is not an Atlas product or cleanup target.",
            )
        return None
    if value == "docs/atlas/CONSOLIDATION.yml":
        return (
            "nonpublishable-scientific-input",
            "The migration policy retains verified legacy sources as nonpublishable package inputs.",
        )
    if value.startswith(("docs/acceptance/", "docs/work/", "tests/")):
        return (
            "historical-reproduction-evidence",
            "The reference records or tests preserve historical production and verification evidence.",
        )
    if value.startswith("scripts/"):
        if any(
            marker in line_text
            for marker in ("--output", "default=", "else ROOT /", "output_root")
        ):
            return None
        retained_input = any(
            source == legacy or legacy.is_relative_to(source) for source in source_paths
        )
        if retained_input:
            return (
                "nonpublishable-scientific-input",
                "The renderer consumes the retained selection bundle; the Atlas registry does not publish the bundle as an individual product.",
            )
        return None
    return None


def _orientation_gallery_root(root: Path) -> PurePosixPath | None:
    catalog_path = root / "docs/products/ARTIFACT_CATALOG.yml"
    if not catalog_path.is_file():
        return None
    payload = _load_yaml_mapping(catalog_path, "artifact catalog")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("artifact catalog entries must be a list")
    galleries = [
        item
        for item in entries
        if isinstance(item, dict) and item.get("id") == "five-phase-orientation-gallery"
    ]
    if len(galleries) != 1 or not isinstance(galleries[0].get("artifact_path"), str):
        return None
    return _relative_path(
        galleries[0]["artifact_path"],
        "orientation gallery artifact_path",
    )


def audit_legacy_paths(
    *,
    ledger_path: str | Path,
    repository_root: str | Path,
    output_path: str | Path,
) -> LegacyPathAuditResult:
    """Audit tracked current references without hiding publication paths."""
    root = Path(repository_root).resolve()
    ledger_file = Path(ledger_path).resolve()
    ledger = _load_migration_ledger(ledger_file)
    if ledger.state != "materialized":
        raise ValueError("legacy path audit requires a materialized migration ledger")
    legacy_roots = _legacy_roots_from_ledger(ledger)
    source_paths = tuple(
        sorted(
            {
                *(PurePosixPath(value) for value in ledger.retained_source_paths),
                *(
                    PurePosixPath(item.source_path)
                    for item in ledger.files
                    if item.source_path is not None
                ),
            }
        )
    )
    gallery_root = _orientation_gallery_root(root)
    output = Path(output_path).resolve()
    excluded = {
        "docs/atlas/ATLAS_MIGRATION.yml",
        "docs/atlas/LEGACY_PATH_AUDIT.yml",
        ledger_file.relative_to(root).as_posix(),
        output.relative_to(root).as_posix(),
    }
    allowed: list[dict[str, object]] = []
    publishable: list[dict[str, object]] = []

    for tracked in _audit_input_paths(root):
        value = tracked.as_posix()
        if _is_audit_excluded(tracked, excluded):
            continue
        path = root / tracked
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        generated_site = value.startswith("docs/atlas/site/")
        for line_number, line_text in enumerate(lines, start=1):
            for legacy_path in _line_legacy_paths(line_text, legacy_roots):
                record = {
                    "file": value,
                    "line": line_number,
                    "legacy_path": legacy_path,
                }
                if generated_site or value == "docs/atlas/PRODUCT_REGISTRY.yml":
                    publishable.append(record)
                    continue
                classification = _allowed_reference(
                    file=tracked,
                    line_text=line_text,
                    legacy_path=legacy_path,
                    source_paths=source_paths,
                    orientation_gallery_root=gallery_root,
                )
                if classification is None:
                    publishable.append(record)
                    continue
                kind, reason = classification
                if kind not in _ALLOWED_REFERENCE_CLASSIFICATIONS:
                    raise ValueError(f"unsupported legacy reference classification: {kind}")
                allowed.append(
                    {
                        **record,
                        "classification": kind,
                        "reason": reason,
                    }
                )

    allowed.sort(
        key=lambda item: (
            str(item["file"]),
            int(item["line"]),
            str(item["legacy_path"]),
        )
    )
    payload = {
        "schema_version": 1,
        "publishable_legacy_reference_count": len(publishable),
        "allowed_references": allowed,
    }
    generated = output.with_name(output.name + ".generated")
    try:
        generated.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        os.replace(generated, output)
    except Exception:
        generated.unlink(missing_ok=True)
        raise
    if publishable:
        first = publishable[0]
        raise ValueError(
            f"publishable legacy references={len(publishable)}; "
            f"first={first['file']}:{first['line']}"
        )
    return LegacyPathAuditResult(
        publishable_legacy_reference_count=0,
        allowed_reference_count=len(allowed),
    )


def materialize_ledger(
    ledger_path: str | Path,
    repository_root: str | Path,
) -> MigrationLedger:
    """Safely materialize and validate every package before advancing ledger state."""
    ledger_file = Path(ledger_path)
    ledger = _load_migration_ledger(ledger_file)
    root = Path(repository_root).resolve()
    canonical = root / ledger.canonical_root
    _assert_real_directory(canonical, anchor=root)

    product_by_id = {item.product_id: item for item in ledger.products}
    for product in ledger.products:
        destination_root = _relative_path(
            product.destination_root,
            "product destination root",
        )
        expected_root = _CANONICAL_ROOT / product.phase_slug / "products" / product.product_id
        if destination_root != expected_root:
            raise ValueError(
                f"product destination root differs from canonical layout: {product.product_id}"
            )
        product_root = root / destination_root
        for directory in _ROLE_DIRECTORIES.values():
            _assert_real_directory(product_root / directory, anchor=root)

    updated_files: list[MigrationFile] = []
    for item in ledger.files:
        destination_relative = _relative_path(
            item.destination_path,
            "migration destination",
        )
        _assert_path_below(destination_relative, _CANONICAL_ROOT, "migration destination")
        product = product_by_id[item.product_id]
        product_root = _relative_path(product.destination_root, "product destination root")
        _assert_path_below(destination_relative, product_root, "migration destination")
        destination = root / destination_relative
        _assert_real_directory(destination.parent, anchor=root)

        if item.kind == "generated-metadata":
            content = _release_metadata(
                product_id=item.product_id,
                phase_slug=item.phase_slug,
                source_commit=ledger.source_commit,
                registry_record=product.registry_record,
            )
            if len(content) != item.source_byte_count:
                raise ValueError(f"generated metadata byte count changed: {destination}")
            if sha256(content).hexdigest() != item.source_sha256:
                raise ValueError(f"generated metadata SHA-256 changed: {destination}")
            _publish_bytes_verified(content, destination)
            updated_files.append(item)
            continue

        if item.source_path is None:
            raise ValueError(f"migration source is missing from ledger: {destination}")
        source_relative = _relative_path(item.source_path, "migration source")
        source = root / source_relative
        try:
            resolved_source = source.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ValueError(f"migration source is missing: {source}") from error
        if not resolved_source.is_relative_to(root):
            raise ValueError(f"migration source escapes repository root: {source}")
        _validate_source_identity(
            source,
            expected_byte_count=item.source_byte_count,
            expected_sha256=item.source_sha256,
        )

        if item.kind == "copied":
            if (
                item.destination_byte_count != item.source_byte_count
                or item.destination_sha256 != item.source_sha256
            ):
                raise ValueError(f"copied destination identity is invalid: {destination}")
            _clone_or_copy_verified(source, destination, item.source_sha256)
            updated_files.append(item)
            continue
        if item.kind != "generated-proxy":
            raise ValueError(f"unsupported migration file kind: {item.kind}")

        if destination.exists() or destination.is_symlink():
            proxy = validate_web_proxy(destination, WEB_PROXY_PROFILE)
        else:
            proxy = build_web_proxy(source, destination, WEB_PROXY_PROFILE)
        if item.destination_byte_count is not None and (
            proxy.byte_count != item.destination_byte_count
            or proxy.sha256 != item.destination_sha256
        ):
            raise ValueError(
                f"refusing to overwrite different destination: {destination}"
            )
        updated_files.append(
            replace(
                item,
                destination_byte_count=proxy.byte_count,
                destination_sha256=proxy.sha256,
            )
        )

    updated_ledger = replace(ledger, files=tuple(updated_files))
    files_by_product: dict[str, tuple[MigrationFile, ...]] = {
        product.product_id: tuple(
            item for item in updated_ledger.files if item.product_id == product.product_id
        )
        for product in updated_ledger.products
    }
    validated_by_phase: dict[str, list[ProductPackage]] = {}
    for product in updated_ledger.products:
        product_root = root / product.destination_root
        manifest = product_root / "product-package.yml"
        _publish_bytes_verified(
            _product_manifest(
                updated_ledger,
                product,
                files_by_product[product.product_id],
            ),
            manifest,
        )
        package = validate_product_package(manifest)
        validated_by_phase.setdefault(product.phase_slug, []).append(package)

    for phase_slug, products in sorted(validated_by_phase.items()):
        phase_manifest = canonical / phase_slug / "phase-package.yml"
        _publish_bytes_verified(
            _phase_manifest(phase_slug, tuple(products)),
            phase_manifest,
        )
        validate_phase_package(phase_manifest)

    verification = _verify_canonical_tree(updated_ledger, root)
    if not verification.valid:
        raise ValueError(
            "canonical verification failed: "
            f"missing={verification.missing_count} "
            f"mismatched={verification.mismatched_count} "
            f"symlinks={verification.symlink_count}"
        )
    materialized = replace(updated_ledger, state="materialized")
    write_migration_ledger(materialized, ledger_file)
    final_verification = _verify_canonical_tree(
        _load_migration_ledger(ledger_file),
        root,
    )
    if not final_verification.valid:
        raise ValueError("canonical verification failed after ledger publication")
    return materialized


__all__ = [
    "CanonicalVerification",
    "LegacyPathAuditResult",
    "MigrationFile",
    "MigrationLedger",
    "MigrationProduct",
    "RegistryRewriteResult",
    "audit_legacy_paths",
    "build_migration_ledger",
    "materialize_ledger",
    "rewrite_product_registry",
    "validate_migration_output_path",
    "verify_canonical_tree",
    "write_migration_ledger",
]

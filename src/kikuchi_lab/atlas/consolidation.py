"""Deterministically plan legacy Atlas artifacts into canonical packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib.util
import mimetypes
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml

from .catalog import AtlasProduct, load_phase_registry, load_product_registry
from .packages import sha256_file


_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_POLICY_FIELDS = {"schema_version", "canonical_root", "legacy_roots", "extra_products"}
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
    products: tuple[MigrationProduct, ...]
    files: tuple[MigrationFile, ...]

    @property
    def product_count(self) -> int:
        return len(self.products)

    @property
    def phase_count(self) -> int:
        return len({item.phase_slug for item in self.products})


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
        products=sorted_products,
        files=sorted_files,
    )


def write_migration_ledger(ledger: MigrationLedger, output_path: str | Path) -> None:
    """Write a deterministic YAML migration ledger without materializing products."""
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


__all__ = [
    "MigrationFile",
    "MigrationLedger",
    "MigrationProduct",
    "build_migration_ledger",
    "validate_migration_output_path",
    "write_migration_ledger",
]

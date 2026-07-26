"""Local contracts for the Atlas Google Drive mirror and Google Site copy.

This module never talks to Google.  It validates locally recorded opaque
identities, exposes only independently public-verified product URLs, compares
downloaded package trees byte-for-byte, and generates reviewable Markdown for
the later Google Sites workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit

import yaml

from .catalog import AtlasPhase, AtlasProduct, load_phase_registry, load_product_registry
from .packages import sha256_file, validate_phase_package, validate_product_package


_ACCOUNT = "zmichels@umn.edu"
_WRONG_MOUNT_MARKER = "GoogleDrive-mich0201@umn.edu"
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "provider",
    "account",
    "local_mount",
    "transport",
    "quota",
    "root",
    "phases",
    "site",
}
_QUOTA_FIELDS = {
    "observed_at",
    "total_bytes",
    "used_bytes",
    "free_bytes",
    "required_headroom_bytes",
}
_ROOT_FIELDS = {"drive_id", "url", "access", "state"}
_PHASE_FIELDS = {"drive_id", "url", "access", "state", "products"}
_PRODUCT_FIELDS = {
    "drive_id",
    "url",
    "access",
    "state",
    "package_manifest_sha256",
    "verified_at",
}
_SITE_FIELDS = {"draft_url", "public_url", "audience", "state"}
_TRANSPORTS = {"undecided", "drive-for-desktop", "chrome-folder-upload"}
_ACCESS_STATES = {"private", "public-link"}
_COMPLETE_STATES = {"complete", "complete-private", "public-verified"}
_PUBLIC_STATE = "public-verified"
_EXPECTED_COMPLETE_PHASES = 12
_EXPECTED_COMPLETE_PRODUCTS = 125


@dataclass(frozen=True)
class MirrorProduct:
    """One remotely addressed product folder."""

    identifier: str
    drive_id: str | None
    url: str | None
    access: str
    state: str
    package_manifest_sha256: str | None
    verified_at: str | None


@dataclass(frozen=True)
class MirrorPhase:
    """One phase folder and its product-folder records."""

    slug: str
    drive_id: str | None
    url: str | None
    access: str
    state: str
    products: Mapping[str, MirrorProduct]

    def __post_init__(self) -> None:
        object.__setattr__(self, "products", MappingProxyType(dict(self.products)))


@dataclass(frozen=True)
class MirrorLedger:
    """Validated local record of mutable Google Drive and Sites identities."""

    path: Path
    provider: str
    account: str
    local_mount: str | None
    transport: str
    quota: Mapping[str, object]
    root_drive_id: str | None
    root_url: str | None
    root_access: str
    root_state: str
    phases: Mapping[str, MirrorPhase]
    site_draft_url: str
    site_public_url: str | None
    site_audience: str
    site_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "quota", MappingProxyType(dict(self.quota)))
        object.__setattr__(self, "phases", MappingProxyType(dict(self.phases)))

    @property
    def phase_count(self) -> int:
        return len(self.phases)

    @property
    def product_count(self) -> int:
        return sum(len(phase.products) for phase in self.phases.values())

    @property
    def public_product_count(self) -> int:
        return sum(
            product.state == _PUBLIC_STATE and product.url is not None
            for phase in self.phases.values()
            for product in phase.products.values()
        )


@dataclass(frozen=True)
class DownloadReconciliation:
    """Exact downloaded-phase comparison against canonical package inventories."""

    expected_files: int
    verified_files: int
    missing: tuple[str, ...]
    mismatched: tuple[str, ...]
    unexpected: tuple[str, ...]

    @property
    def extra(self) -> tuple[str, ...]:
        """Alias for callers that describe unexpected downloaded files as extra."""
        return self.unexpected

    @property
    def is_exact(self) -> bool:
        return (
            self.expected_files == self.verified_files
            and not self.missing
            and not self.mismatched
            and not self.unexpected
        )


@dataclass(frozen=True)
class GoogleSiteSourceResult:
    """Generated Markdown and machine-readable inventory for a Google Site draft."""

    output_root: Path
    index_path: Path
    about_path: Path
    phase_pages: tuple[Path, ...]
    inventory_path: Path


def _mapping(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} fields differ from the mirror schema")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _opaque_id(value: object, label: str) -> str | None:
    opaque = _optional_text(value, label)
    if opaque is not None and not _OPAQUE_ID.fullmatch(opaque):
        raise ValueError(f"{label} must be an opaque Google Drive ID")
    return opaque


def _drive_folder_url(value: object, label: str) -> str | None:
    url = _optional_text(value, label)
    if url is None:
        return None
    parsed = urlsplit(url)
    parts = tuple(part for part in parsed.path.split("/") if part)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "drive.google.com"
        or parsed.username is not None
        or parsed.password is not None
        or len(parts) != 3
        or parts[:2] != ("drive", "folders")
        or not _OPAQUE_ID.fullmatch(parts[2])
        or parsed.fragment
    ):
        raise ValueError(f"{label} must be a Google Drive folder URL")
    return url


def _sites_url(value: object, label: str, *, allow_none: bool) -> str | None:
    url = _optional_text(value, label)
    if url is None:
        if allow_none:
            return None
        raise ValueError(f"{label} must be non-empty text")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "sites.google.com"
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith("/umn.edu/")
        or parsed.fragment
    ):
        raise ValueError(f"{label} must be a UMN Google Sites URL")
    return url


def _access(value: object, label: str) -> str:
    access = _text(value, label)
    if access not in _ACCESS_STATES:
        raise ValueError(f"{label} is unsupported")
    return access


def _state(value: object, label: str) -> str:
    return _text(value, label)


def _optional_digest(value: object, label: str) -> str | None:
    digest = _optional_text(value, label)
    if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _validate_quota(value: object) -> Mapping[str, object]:
    raw = _mapping(value, _QUOTA_FIELDS, "mirror quota")
    required = raw["required_headroom_bytes"]
    if (
        not isinstance(required, int)
        or isinstance(required, bool)
        or required != 10 * 1024**3
    ):
        raise ValueError("mirror quota required_headroom_bytes must be 10737418240")
    for field in ("total_bytes", "used_bytes", "free_bytes"):
        byte_count = raw[field]
        if byte_count is not None and (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
        ):
            raise ValueError(f"mirror quota {field} must be a non-negative integer or null")
    _optional_text(raw["observed_at"], "mirror quota observed_at")
    return MappingProxyType(dict(raw))


def _mirror_product(identifier: str, value: object) -> MirrorProduct:
    raw = _mapping(value, _PRODUCT_FIELDS, f"mirror product {identifier}")
    state = _state(raw["state"], f"mirror product {identifier} state")
    url = _drive_folder_url(raw["url"], f"mirror product {identifier} URL")
    access = _access(raw["access"], f"mirror product {identifier} access")
    drive_id = _opaque_id(
        raw["drive_id"], f"mirror product {identifier} drive_id"
    )
    if state == _PUBLIC_STATE and (
        drive_id is None or url is None or access != "public-link"
    ):
        raise ValueError(
            f"public-verified mirror product {identifier} requires an opaque ID "
            "and public-link folder URL"
        )
    return MirrorProduct(
        identifier=identifier,
        drive_id=drive_id,
        url=url,
        access=access,
        state=state,
        package_manifest_sha256=_optional_digest(
            raw["package_manifest_sha256"],
            f"mirror product {identifier} package_manifest_sha256",
        ),
        verified_at=_optional_text(
            raw["verified_at"], f"mirror product {identifier} verified_at"
        ),
    )


def _mirror_phase(slug: str, value: object) -> MirrorPhase:
    raw = _mapping(value, _PHASE_FIELDS, f"mirror phase {slug}")
    raw_products = raw["products"]
    if not isinstance(raw_products, dict):
        raise ValueError(f"mirror phase {slug} products must be a mapping")
    products = {
        _text(identifier, "mirror product ID"): _mirror_product(
            _text(identifier, "mirror product ID"), product
        )
        for identifier, product in raw_products.items()
    }
    drive_id = _opaque_id(raw["drive_id"], f"mirror phase {slug} drive_id")
    url = _drive_folder_url(raw["url"], f"mirror phase {slug} URL")
    access = _access(raw["access"], f"mirror phase {slug} access")
    state = _state(raw["state"], f"mirror phase {slug} state")
    if state == _PUBLIC_STATE and (
        drive_id is None or url is None or access != "public-link"
    ):
        raise ValueError(
            f"public-verified mirror phase {slug} requires an opaque ID "
            "and public-link folder URL"
        )
    return MirrorPhase(
        slug=slug,
        drive_id=drive_id,
        url=url,
        access=access,
        state=state,
        products=products,
    )


def load_mirror_ledger(path: str | Path) -> MirrorLedger:
    """Load and validate a local mirror ledger without deriving remote identities."""
    ledger_path = Path(path).resolve()
    try:
        parsed = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("mirror ledger cannot be read as YAML") from error
    raw = _mapping(parsed, _TOP_LEVEL_FIELDS, "mirror ledger")
    if raw["schema_version"] != 1:
        raise ValueError("unsupported mirror ledger schema")
    if raw["provider"] != "google-drive":
        raise ValueError("mirror provider must be google-drive")
    if raw["account"] != _ACCOUNT:
        raise ValueError(f"mirror account must be exactly {_ACCOUNT}")
    local_mount = _optional_text(raw["local_mount"], "mirror local_mount")
    if local_mount is not None:
        if _WRONG_MOUNT_MARKER in local_mount:
            raise ValueError("mirror local_mount must not use the mich0201 account")
        if "GoogleDrive-" in local_mount and "GoogleDrive-zmichels@umn.edu" not in local_mount:
            raise ValueError(f"mirror local_mount must use exactly {_ACCOUNT}")
    transport = _text(raw["transport"], "mirror transport")
    if transport not in _TRANSPORTS:
        raise ValueError("mirror transport is unsupported")

    root = _mapping(raw["root"], _ROOT_FIELDS, "mirror root")
    raw_phases = raw["phases"]
    if not isinstance(raw_phases, dict):
        raise ValueError("mirror phases must be a mapping")
    phases = {
        _text(slug, "mirror phase slug"): _mirror_phase(
            _text(slug, "mirror phase slug"), phase
        )
        for slug, phase in raw_phases.items()
    }
    product_ids = [
        product_id for phase in phases.values() for product_id in phase.products
    ]
    if len(set(product_ids)) != len(product_ids):
        raise ValueError("mirror product IDs must be unique across phases")
    site = _mapping(raw["site"], _SITE_FIELDS, "mirror site")
    root_drive_id = _opaque_id(root["drive_id"], "mirror root drive_id")
    root_url = _drive_folder_url(root["url"], "mirror root URL")
    root_access = _access(root["access"], "mirror root access")
    root_state = _state(root["state"], "mirror root state")
    if root_state == _PUBLIC_STATE and (
        root_drive_id is None
        or root_url is None
        or root_access != "public-link"
    ):
        raise ValueError(
            "public-verified mirror root requires an opaque ID and "
            "public-link folder URL"
        )
    ledger = MirrorLedger(
        path=ledger_path,
        provider="google-drive",
        account=_ACCOUNT,
        local_mount=local_mount,
        transport=transport,
        quota=_validate_quota(raw["quota"]),
        root_drive_id=root_drive_id,
        root_url=root_url,
        root_access=root_access,
        root_state=root_state,
        phases=phases,
        site_draft_url=_sites_url(
            site["draft_url"], "mirror site draft_url", allow_none=False
        )
        or "",
        site_public_url=_sites_url(
            site["public_url"], "mirror site public_url", allow_none=True
        ),
        site_audience=_text(site["audience"], "mirror site audience"),
        site_state=_state(site["state"], "mirror site state"),
    )
    if ledger.root_state in _COMPLETE_STATES and (
        ledger.phase_count != _EXPECTED_COMPLETE_PHASES
        or ledger.product_count != _EXPECTED_COMPLETE_PRODUCTS
    ):
        raise ValueError(
            "complete mirror state requires exactly 12 phases and 125 products"
        )
    return ledger


def public_product_urls(ledger: MirrorLedger) -> dict[str, str]:
    """Return only exact product-folder URLs with public-verified ledger state."""
    return {
        product.identifier: product.url
        for phase in ledger.phases.values()
        for product in phase.products.values()
        if product.state == _PUBLIC_STATE and product.url is not None
    }


def _initial_product() -> dict[str, object]:
    return {
        "drive_id": None,
        "url": None,
        "access": "private",
        "state": "planned",
        "package_manifest_sha256": None,
        "verified_at": None,
    }


def initialize_mirror_ledger(
    *,
    registry_path: str | Path,
    product_registry_path: str | Path,
    output_path: str | Path,
) -> MirrorLedger:
    """Write the planned 12-phase/125-product private mirror skeleton."""
    phases = load_phase_registry(registry_path)
    _, products = load_product_registry(
        product_registry_path,
        phase_slugs={phase.slug for phase in phases},
    )
    by_phase: dict[str, list[AtlasProduct]] = {phase.slug: [] for phase in phases}
    for product in products:
        for slug in product.phase_slugs:
            by_phase[slug].append(product)
    raw = {
        "schema_version": 1,
        "provider": "google-drive",
        "account": _ACCOUNT,
        "local_mount": None,
        "transport": "undecided",
        "quota": {
            "observed_at": None,
            "total_bytes": None,
            "used_bytes": None,
            "free_bytes": None,
            "required_headroom_bytes": 10 * 1024**3,
        },
        "root": {
            "drive_id": None,
            "url": None,
            "access": "private",
            "state": "planned",
        },
        "phases": {
            phase.slug: {
                "drive_id": None,
                "url": None,
                "access": "private",
                "state": "planned",
                "products": {
                    product.identifier: _initial_product()
                    for product in by_phase[phase.slug]
                },
            }
            for phase in phases
        },
        "site": {
            "draft_url": "https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test",
            "public_url": None,
            "audience": "university-only",
            "state": "draft",
        },
    }
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    ledger = load_mirror_ledger(output)
    if (
        ledger.phase_count != _EXPECTED_COMPLETE_PHASES
        or ledger.product_count != _EXPECTED_COMPLETE_PRODUCTS
    ):
        raise ValueError("mirror initialization requires exactly 12 phases and 125 products")
    return ledger


def _expected_phase_files(canonical_phase_root: Path) -> dict[str, str]:
    phase_manifest = canonical_phase_root / "phase-package.yml"
    phase_package = validate_phase_package(phase_manifest)
    expected = {"phase-package.yml": sha256_file(phase_manifest)}
    for product_id in phase_package.product_ids:
        manifest = (
            canonical_phase_root
            / "products"
            / product_id
            / "product-package.yml"
        )
        package = validate_product_package(manifest)
        manifest_relative = manifest.relative_to(canonical_phase_root).as_posix()
        expected[manifest_relative] = sha256_file(manifest)
        for item in package.files:
            path = manifest.parent.joinpath(*item.relative_path.parts)
            expected[path.relative_to(canonical_phase_root).as_posix()] = item.sha256
    return expected


def _downloaded_files(downloaded_phase_root: Path) -> set[str]:
    if downloaded_phase_root.is_symlink():
        raise ValueError("downloaded phase root must not be a symlink")
    if not downloaded_phase_root.is_dir():
        raise ValueError("downloaded phase root must be a real directory")
    files: set[str] = set()
    for root, directories, filenames in os.walk(
        downloaded_phase_root, followlinks=False
    ):
        current = Path(root)
        for name in directories:
            directory = current / name
            if directory.is_symlink():
                raise ValueError(
                    f"downloaded phase must not contain a symlink: "
                    f"{directory.relative_to(downloaded_phase_root)}"
                )
        for name in filenames:
            path = current / name
            relative = path.relative_to(downloaded_phase_root).as_posix()
            if path.is_symlink():
                raise ValueError(
                    f"downloaded phase must not contain a symlink: {relative}"
                )
            if not path.is_file():
                raise ValueError(
                    f"downloaded phase entry must be a regular file: {relative}"
                )
            files.add(relative)
    return files


def reconcile_downloaded_phase(
    canonical_phase_root: str | Path,
    downloaded_phase_root: str | Path,
) -> DownloadReconciliation:
    """Compare one downloaded phase with the exact canonical package inventory."""
    canonical = Path(canonical_phase_root).resolve()
    downloaded = Path(downloaded_phase_root).absolute()
    expected = _expected_phase_files(canonical)
    downloaded_files = _downloaded_files(downloaded)
    missing = tuple(sorted(set(expected) - downloaded_files))
    unexpected = tuple(sorted(downloaded_files - set(expected)))
    mismatched: list[str] = []
    verified = 0
    for relative, digest in sorted(expected.items()):
        path = downloaded.joinpath(*relative.split("/"))
        if relative in missing:
            continue
        if path.is_symlink():
            raise ValueError(
                f"downloaded phase must not contain a symlink: {relative}"
            )
        if not path.is_file() or sha256_file(path) != digest:
            mismatched.append(relative)
        else:
            verified += 1
    return DownloadReconciliation(
        expected_files=len(expected),
        verified_files=verified,
        missing=missing,
        mismatched=tuple(mismatched),
        unexpected=unexpected,
    )


def _mirror_status_text(ledger: MirrorLedger) -> str:
    if (
        ledger.root_state == _PUBLIC_STATE
        and ledger.site_state == _PUBLIC_STATE
        and ledger.public_product_count == ledger.product_count
    ):
        return "Public access has been independently verified."
    return (
        "This is planning and draft source; public access has not been verified. "
        "Folder identities and access state remain governed by the local mirror ledger."
    )


def _phase_page(
    *,
    phase: AtlasPhase,
    products: tuple[AtlasProduct, ...],
    mirror_phase: MirrorPhase | None,
    public_urls: Mapping[str, str],
    allow_private_links: bool,
) -> str:
    page_lines = [
        f"# {phase.display_name}",
        "",
        f"`{phase.formula}` | {phase.crystal_system} | {phase.family}",
        "",
        phase.scope_note,
        "",
        (
            f"[Open the primary GitHub Pages catalogue]"
            f"(https://zmichels.github.io/kikuchi-atlas/phases/{phase.slug}.html)"
        ),
    ]
    if mirror_phase is not None and mirror_phase.url is not None and (
        mirror_phase.state == _PUBLIC_STATE or allow_private_links
    ):
        link_label = (
            "Open the verified public Drive phase folder"
            if mirror_phase.state == _PUBLIC_STATE
            else "Open the restricted Drive phase folder for signed-in review"
        )
        page_lines.extend(("", f"[{link_label}]({mirror_phase.url})"))
    page_lines.extend(("", "## Products", ""))
    for product in products:
        page_lines.append(f"- **{product.title}** — {product.caption}")
        full_resolution = public_urls.get(product.identifier)
        if full_resolution is not None:
            page_lines.append(
                f"  - [Open full-resolution package]({full_resolution})"
            )
    page_lines.extend(
        (
            "",
            (
                "These products are modeled visualizations or printable geometry; "
                "they are not acquired EBSD patterns."
            ),
            "",
        )
    )
    return "\n".join(page_lines)


def _reset_site_source(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.md", "about.md", "site-inventory.json"):
        path = output / name
        if path.exists():
            path.unlink()
    phases = output / "phases"
    if phases.is_dir():
        shutil.rmtree(phases)
    elif phases.exists():
        phases.unlink()


def build_google_site_source(
    *,
    registry_path: str | Path,
    product_registry_path: str | Path,
    mirror_registry_path: str | Path,
    output_root: str | Path,
    allow_private_links: bool = False,
) -> GoogleSiteSourceResult:
    """Generate landing, provenance, and phase Markdown without external writes."""
    phases = load_phase_registry(registry_path)
    _, products = load_product_registry(
        product_registry_path,
        phase_slugs={phase.slug for phase in phases},
    )
    ledger = load_mirror_ledger(mirror_registry_path)
    if set(ledger.phases) != {phase.slug for phase in phases}:
        raise ValueError("mirror phase inventory differs from the phase registry")
    registry_product_ids = {product.identifier for product in products}
    mirror_product_ids = {
        product_id
        for phase in ledger.phases.values()
        for product_id in phase.products
    }
    if mirror_product_ids != registry_product_ids:
        raise ValueError("mirror product inventory differs from the product registry")

    output = Path(output_root).resolve()
    _reset_site_source(output)
    phase_directory = output / "phases"
    phase_directory.mkdir(parents=True, exist_ok=True)
    status = _mirror_status_text(ledger)
    index = output / "index.md"
    index.write_text(
        "\n".join(
            (
                "# Kikuchi Atlas",
                "",
                (
                    f"A provenance-first catalogue of {len(phases)} phases and "
                    f"{len(products)} products."
                ),
                "",
                (
                    "The Atlas distributes modeled Kikuchi visualizations, scientific "
                    "fields, motion studies, and printable geometry."
                ),
                "",
                status,
                "",
                "## Browse by phase",
                "",
                *(
                    f"- [{phase.display_name}](phases/{phase.slug}.md)"
                    for phase in phases
                ),
                "",
                "[About and provenance](about.md)",
                "",
            )
        ),
        encoding="utf-8",
    )
    about = output / "about.md"
    about.write_text(
        "\n".join(
            (
                "# About and provenance",
                "",
                (
                    "Kikuchi Atlas products are generated from tracked structural "
                    "sources, explicit recipes, package manifests, byte counts, and "
                    "SHA-256 checksums."
                ),
                "",
                (
                    "They are modeled visualizations and printable geometry, not "
                    "acquired EBSD patterns, not experimental detector acquisitions, "
                    "and not a validated dictionary-indexing dataset."
                ),
                "",
                (
                    "Licenses and source attribution remain product-specific; a mirror "
                    "location does not change scientific identity or claim scope."
                ),
                "",
                status,
                "",
            )
        ),
        encoding="utf-8",
    )
    public_urls = public_product_urls(ledger)
    phase_pages: list[Path] = []
    for phase in phases:
        page = phase_directory / f"{phase.slug}.md"
        phase_products = tuple(
            product for product in products if phase.slug in product.phase_slugs
        )
        page.write_text(
            _phase_page(
                phase=phase,
                products=phase_products,
                mirror_phase=ledger.phases.get(phase.slug),
                public_urls=public_urls,
                allow_private_links=allow_private_links,
            ),
            encoding="utf-8",
        )
        phase_pages.append(page)

    inventory = {
        "schema_version": 1,
        "phase_count": len(phases),
        "product_count": len(products),
        "mirror": {
            "provider": ledger.provider,
            "account": ledger.account,
            "root_state": ledger.root_state,
            "site_state": ledger.site_state,
            "product_urls": public_urls,
        },
        "pages": {
            "index": "index.md",
            "about": "about.md",
            "phases": [path.relative_to(output).as_posix() for path in phase_pages],
        },
        "phases": [
            {
                "slug": phase.slug,
                "display_name": phase.display_name,
                "mirror_state": ledger.phases[phase.slug].state,
                "mirror_url": (
                    ledger.phases[phase.slug].url
                    if ledger.phases[phase.slug].state == _PUBLIC_STATE
                    or allow_private_links
                    else None
                ),
                "product_ids": [
                    product.identifier
                    for product in products
                    if phase.slug in product.phase_slugs
                ],
            }
            for phase in phases
        ],
        "products": [
            {
                "id": product.identifier,
                "phase_slugs": list(product.phase_slugs),
                "delivery": {
                    "full_resolution_url": public_urls.get(product.identifier)
                },
            }
            for product in products
        ],
    }
    inventory_path = output / "site-inventory.json"
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return GoogleSiteSourceResult(
        output_root=output,
        index_path=index,
        about_path=about,
        phase_pages=tuple(phase_pages),
        inventory_path=inventory_path,
    )


__all__ = [
    "DownloadReconciliation",
    "GoogleSiteSourceResult",
    "MirrorLedger",
    "MirrorPhase",
    "MirrorProduct",
    "build_google_site_source",
    "initialize_mirror_ledger",
    "load_mirror_ledger",
    "public_product_urls",
    "reconcile_downloaded_phase",
]

"""Local contracts for the Atlas Google Drive mirror and Google Site copy.

This module never talks to Google.  It validates locally recorded opaque
identities, exposes only independently public-verified product URLs, compares
downloaded package trees byte-for-byte, and generates reviewable Markdown for
the later Google Sites workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

import yaml

from .catalog import AtlasPhase, AtlasProduct, load_phase_registry, load_product_registry
from .packages import (
    load_product_package,
    sha256_file,
    validate_phase_package,
    validate_product_package,
)


_ACCOUNT = "zmichels@umn.edu"
_WRONG_MOUNT_MARKER = "GoogleDrive-mich0201@umn.edu"
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_LEGACY_TOP_LEVEL_FIELDS = {
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
_SCHEMA_2_TOP_LEVEL_FIELDS = _LEGACY_TOP_LEVEL_FIELDS | {"upload_acceptance"}
_SCHEMA_3_TOP_LEVEL_FIELDS = _SCHEMA_2_TOP_LEVEL_FIELDS | {"public_verification"}
_LEGACY_QUOTA_FIELDS = {
    "observed_at",
    "total_bytes",
    "used_bytes",
    "free_bytes",
    "required_headroom_bytes",
}
_QUOTA_FIELDS = _LEGACY_QUOTA_FIELDS | {
    "canonical_upload_bytes",
    "canonical_upload_bytes_basis",
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
_UPLOAD_ACCEPTANCE_FIELDS = {
    "upload_observation",
    "hierarchy_reconciliation",
    "privacy_verification",
    "round_trip_verification",
}
_UPLOAD_OBSERVATION_FIELDS = {
    "observed_at",
    "completed_files",
    "total_files",
    "completion_signal",
    "failure_signal",
    "canonical_upload_bytes",
    "canonical_upload_bytes_basis",
}
_HIERARCHY_RECONCILIATION_FIELDS = {
    "root_phases_folder_count",
    "phase_count",
    "product_count",
    "missing_identities",
    "duplicate_drive_ids",
    "duplicate_urls",
}
_PRIVACY_VERIFICATION_FIELDS = {
    "observed_at",
    "root_private",
    "phases_private",
    "product_folder_samples_private",
    "leaf_file_samples_private",
    "inherited_public_link_removed",
    "sample_leaf_files",
}
_ROUND_TRIP_VERIFICATION_FIELDS = {
    "status",
    "disposition",
    "waived_at",
    "reason",
    "downloaded_phase_archives",
    "sha256_compared_files",
}
_PUBLIC_VERIFICATION_FIELDS = {
    "observed_at",
    "transport",
    "site",
    "github",
    "drive",
    "representatives",
    "streaming",
    "retained_temp_files",
    "exceptions",
}
_PUBLIC_SITE_FIELDS = {
    "public_url",
    "pages_checked",
    "status_200",
    "exact_final_urls",
    "phase_pages_with_exact_targets",
    "exceptions",
}
_PUBLIC_GITHUB_FIELDS = {
    "pages_checked",
    "status_200",
    "exact_final_urls",
    "registry_titles_visible",
    "exceptions",
}
_PUBLIC_DRIVE_FIELDS = {
    "root_url",
    "roots_checked",
    "phases_checked",
    "products_checked",
    "status_200",
    "exact_final_urls",
    "identities_visible",
    "inventory_markers_visible",
    "denied_signals",
    "exceptions",
}
_PUBLIC_REPRESENTATIVE_FIELDS = {
    "kind",
    "product_id",
    "relative_path",
    "url",
    "final_url",
    "status",
    "content_type",
    "content_disposition",
    "expected_bytes",
    "observed_bytes",
    "expected_sha256",
    "observed_sha256",
    "retained_temp_files",
}
_TRANSPORTS = {"undecided", "drive-for-desktop", "chrome-folder-upload"}
_ACCESS_STATES = {"private", "public-link"}
_COMPLETE_STATES = {"complete", "complete-private", "public-verified"}
_INVENTORY_COMPLETE_STATES = _COMPLETE_STATES | {"uploaded-private"}
_PUBLIC_STATE = "public-verified"
_EXPECTED_COMPLETE_PHASES = 12
_EXPECTED_COMPLETE_PRODUCTS = 125
_EXPECTED_PRIVATE_DRIVE_IDENTITIES = 138
_CANONICAL_UPLOAD_BYTES_BASIS = "exact-regular-file-sum"
_PUBLIC_FILE_KINDS = {"png", "svg", "mp4", "mov", "stl", "yml", "npz"}
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_PHASE_REGISTRY = _REPOSITORY_ROOT / "docs/atlas/PHASE_REGISTRY.yml"
_PRODUCT_REGISTRY = _REPOSITORY_ROOT / "docs/atlas/PRODUCT_REGISTRY.yml"


def _deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_thaw(item) for item in value]
    return value


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
    upload_acceptance: Mapping[str, object] | None
    public_verification: Mapping[str, object] | None
    phases: Mapping[str, MirrorPhase]
    site_draft_url: str
    site_public_url: str | None
    site_audience: str
    site_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "quota", MappingProxyType(dict(self.quota)))
        if self.upload_acceptance is not None:
            object.__setattr__(
                self,
                "upload_acceptance",
                MappingProxyType(dict(self.upload_acceptance)),
            )
        if self.public_verification is not None:
            object.__setattr__(
                self,
                "public_verification",
                _deep_freeze(self.public_verification),
            )
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
class MirrorReconciliation:
    """Completed whole-mirror byte reconciliation and resulting ledger."""

    ledger: MirrorLedger
    phase_count: int
    product_count: int
    expected_files: int
    verified_files: int
    missing: int
    mismatched: int
    unexpected: int


@dataclass(frozen=True)
class MirrorValidation:
    """Strict requested-state validation summary."""

    ledger: MirrorLedger
    verified_private_products: int


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
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{label} must be a Google Drive folder URL")
    return url


def _drive_folder_url_token(url: str) -> str:
    parts = tuple(part for part in urlsplit(url).path.split("/") if part)
    return parts[2]


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


def _sites_editor_url(value: object, label: str) -> str:
    url = _optional_text(value, label)
    if url is None:
        raise ValueError(f"{label} must be non-empty text")
    parsed = urlsplit(url)
    parts = tuple(part for part in parsed.path.split("/") if part)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "sites.google.com"
        or parsed.username is not None
        or parsed.password is not None
        or len(parts) != 5
        or parts[0] != "d"
        or parts[2] != "p"
        or parts[4] != "edit"
        or not _OPAQUE_ID.fullmatch(parts[1])
        or not _OPAQUE_ID.fullmatch(parts[3])
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{label} must be an exact Google Sites editor URL")
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


def _non_negative_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _iso_timestamp(
    value: object,
    label: str,
    *,
    allow_none: bool,
    require_utc: bool = False,
) -> str | None:
    timestamp = _optional_text(value, label)
    if timestamp is None:
        if allow_none:
            return None
        raise ValueError(f"{label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    if require_utc and parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be ISO-8601 UTC")
    return timestamp


def _validate_upload_acceptance(value: object) -> Mapping[str, object]:
    raw = _mapping(
        value,
        _UPLOAD_ACCEPTANCE_FIELDS,
        "mirror upload_acceptance",
    )
    upload = _mapping(
        raw["upload_observation"],
        _UPLOAD_OBSERVATION_FIELDS,
        "mirror upload observation",
    )
    _iso_timestamp(
        upload["observed_at"],
        "mirror upload observation observed_at",
        allow_none=True,
        require_utc=True,
    )
    completed_files = _non_negative_integer(
        upload["completed_files"],
        "mirror upload observation completed_files",
    )
    total_files = _non_negative_integer(
        upload["total_files"],
        "mirror upload observation total_files",
    )
    if completed_files != 1212 or total_files != 1212:
        raise ValueError("uploaded-private mirror requires the observed 1212/1212 upload")
    if (
        _text(
            upload["completion_signal"],
            "mirror upload observation completion_signal",
        )
        != "1 upload complete"
    ):
        raise ValueError("uploaded-private mirror requires the observed completion signal")
    if (
        _text(
            upload["failure_signal"],
            "mirror upload observation failure_signal",
        )
        != "none-observed"
    ):
        raise ValueError("uploaded-private mirror requires the observed no-failure signal")
    canonical_upload_bytes = _non_negative_integer(
        upload["canonical_upload_bytes"],
        "mirror upload observation canonical_upload_bytes",
    )
    if canonical_upload_bytes == 0:
        raise ValueError("mirror upload observation canonical_upload_bytes must be positive")
    if (
        _text(
            upload["canonical_upload_bytes_basis"],
            "mirror upload observation canonical_upload_bytes_basis",
        )
        != _CANONICAL_UPLOAD_BYTES_BASIS
    ):
        raise ValueError("mirror upload observation canonical byte basis is unsupported")

    hierarchy = _mapping(
        raw["hierarchy_reconciliation"],
        _HIERARCHY_RECONCILIATION_FIELDS,
        "mirror hierarchy reconciliation",
    )
    expected_hierarchy = {
        "root_phases_folder_count": 1,
        "phase_count": _EXPECTED_COMPLETE_PHASES,
        "product_count": _EXPECTED_COMPLETE_PRODUCTS,
        "missing_identities": 0,
        "duplicate_drive_ids": 0,
        "duplicate_urls": 0,
    }
    for field, expected in expected_hierarchy.items():
        observed = _non_negative_integer(
            hierarchy[field],
            f"mirror hierarchy reconciliation {field}",
        )
        if observed != expected:
            raise ValueError(
                "uploaded-private mirror requires exact 12-phase/125-product "
                "hierarchy and identity reconciliation"
            )

    privacy = _mapping(
        raw["privacy_verification"],
        _PRIVACY_VERIFICATION_FIELDS,
        "mirror privacy verification",
    )
    _iso_timestamp(
        privacy["observed_at"],
        "mirror privacy verification observed_at",
        allow_none=True,
        require_utc=True,
    )
    if privacy["root_private"] is not True:
        raise ValueError("uploaded-private mirror requires a private root")
    phases_private = _non_negative_integer(
        privacy["phases_private"],
        "mirror privacy verification phases_private",
    )
    if phases_private != _EXPECTED_COMPLETE_PHASES:
        raise ValueError("uploaded-private mirror requires 12 private phase folders")
    product_samples = _non_negative_integer(
        privacy["product_folder_samples_private"],
        "mirror privacy verification product_folder_samples_private",
    )
    if product_samples != _EXPECTED_COMPLETE_PHASES:
        raise ValueError(
            "uploaded-private mirror requires one private product-folder sample per phase"
        )
    leaf_samples = _non_negative_integer(
        privacy["leaf_file_samples_private"],
        "mirror privacy verification leaf_file_samples_private",
    )
    if leaf_samples != 3:
        raise ValueError("uploaded-private mirror requires three private leaf-file samples")
    if privacy["inherited_public_link_removed"] is not True:
        raise ValueError("uploaded-private mirror requires the inherited public link repair")
    sample_leaf_files = privacy["sample_leaf_files"]
    if (
        not isinstance(sample_leaf_files, list)
        or len(sample_leaf_files) != leaf_samples
        or len(set(sample_leaf_files)) != leaf_samples
        or any(not isinstance(sample, str) or not sample.strip() for sample in sample_leaf_files)
    ):
        raise ValueError(
            "mirror privacy verification sample_leaf_files must name three unique leaf files"
        )

    round_trip = _mapping(
        raw["round_trip_verification"],
        _ROUND_TRIP_VERIFICATION_FIELDS,
        "mirror round-trip verification",
    )
    if (
        _text(
            round_trip["status"],
            "mirror round-trip verification status",
        )
        != "not-performed"
    ):
        raise ValueError(
            "uploaded-private mirror must record round-trip verification as not-performed"
        )
    if (
        _text(
            round_trip["disposition"],
            "mirror round-trip verification disposition",
        )
        != "waived-by-user"
    ):
        raise ValueError("uploaded-private mirror requires an explicit user waiver")
    _iso_timestamp(
        round_trip["waived_at"],
        "mirror round-trip verification waived_at",
        allow_none=False,
        require_utc=True,
    )
    _text(
        round_trip["reason"],
        "mirror round-trip verification reason",
    )
    for field in ("downloaded_phase_archives", "sha256_compared_files"):
        if (
            _non_negative_integer(
                round_trip[field],
                f"mirror round-trip verification {field}",
            )
            != 0
        ):
            raise ValueError(
                "not-performed round-trip verification requires zero "
                "downloads and SHA-256 comparisons"
            )
    return MappingProxyType(
        {
            "upload_observation": dict(upload),
            "hierarchy_reconciliation": dict(hierarchy),
            "privacy_verification": dict(privacy),
            "round_trip_verification": dict(round_trip),
        }
    )


def _empty_exceptions(value: object, label: str) -> list[object]:
    if not isinstance(value, list) or value:
        raise ValueError(f"{label} must be an empty list")
    return value


def _required_digest(value: object, label: str) -> str:
    digest = _optional_digest(value, label)
    if digest is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _drive_download_url(value: object, label: str) -> str:
    url = _text(value, label)
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "drive.usercontent.google.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != "/download"
        or parsed.fragment
        or set(query) != {"id", "export", "confirm"}
        or len(query["id"]) != 1
        or not _OPAQUE_ID.fullmatch(query["id"][0])
        or query["export"] != ["download"]
        or query["confirm"] != ["t"]
    ):
        raise ValueError(f"{label} must be an exact public Drive download URL")
    return url


def _canonical_public_file(
    *,
    phases: Mapping[str, MirrorPhase],
    product_id: str,
    relative_path: str,
) -> tuple[int, str]:
    matches = [slug for slug, phase in phases.items() if product_id in phase.products]
    if len(matches) != 1:
        raise ValueError("public representative product must resolve to one ledger product")
    phase_slug = matches[0]
    manifest = (
        _REPOSITORY_ROOT
        / "local/atlas/phases"
        / phase_slug
        / "products"
        / product_id
        / "product-package.yml"
    )
    package = load_product_package(manifest)
    file_records = [
        item for item in package.files if item.relative_path.as_posix() == relative_path
    ]
    if len(file_records) != 1:
        raise ValueError("public representative path must resolve to one canonical manifest file")
    file_record = file_records[0]
    return file_record.byte_count, file_record.sha256


def _validate_public_verification(
    value: object,
    *,
    root_url: str | None,
    site_public_url: str | None,
    phases: Mapping[str, MirrorPhase],
) -> Mapping[str, object]:
    raw = _mapping(
        value,
        _PUBLIC_VERIFICATION_FIELDS,
        "mirror public verification",
    )
    _iso_timestamp(
        raw["observed_at"],
        "mirror public verification observed_at",
        allow_none=False,
        require_utc=True,
    )
    if _text(raw["transport"], "mirror public verification transport") != "cookie-free-http":
        raise ValueError("mirror public verification transport must be cookie-free-http")
    if root_url is None or site_public_url is None:
        raise ValueError("public verification requires recorded root and Site public URLs")

    site = _mapping(
        raw["site"],
        _PUBLIC_SITE_FIELDS,
        "mirror public verification Site",
    )
    observed_site_url = _sites_url(
        site["public_url"],
        "mirror public verification Site public URL",
        allow_none=False,
    )
    if observed_site_url != site_public_url:
        raise ValueError("mirror public verification Site public URL differs from the ledger")
    expected_site_counts = {
        "pages_checked": 14,
        "status_200": 14,
        "exact_final_urls": 14,
        "phase_pages_with_exact_targets": 12,
    }
    if any(
        _non_negative_integer(
            site[field],
            f"mirror public verification Site {field}",
        )
        != expected
        for field, expected in expected_site_counts.items()
    ):
        raise ValueError("mirror public verification Site access counts are not exact")
    _empty_exceptions(
        site["exceptions"],
        "mirror public verification Site exceptions",
    )

    github = _mapping(
        raw["github"],
        _PUBLIC_GITHUB_FIELDS,
        "mirror public verification GitHub",
    )
    expected_github_counts = {
        "pages_checked": 12,
        "status_200": 12,
        "exact_final_urls": 12,
        "registry_titles_visible": 12,
    }
    if any(
        _non_negative_integer(
            github[field],
            f"mirror public verification GitHub {field}",
        )
        != expected
        for field, expected in expected_github_counts.items()
    ):
        raise ValueError("mirror public verification GitHub access counts are not exact")
    _empty_exceptions(
        github["exceptions"],
        "mirror public verification GitHub exceptions",
    )

    drive = _mapping(
        raw["drive"],
        _PUBLIC_DRIVE_FIELDS,
        "mirror public verification Drive",
    )
    observed_root_url = _drive_folder_url(
        drive["root_url"],
        "mirror public verification Drive root URL",
    )
    if observed_root_url != root_url:
        raise ValueError(
            "mirror public verification Drive root URL differs from the ledger root URL"
        )
    expected_drive_counts = {
        "roots_checked": 1,
        "phases_checked": _EXPECTED_COMPLETE_PHASES,
        "products_checked": _EXPECTED_COMPLETE_PRODUCTS,
        "status_200": _EXPECTED_PRIVATE_DRIVE_IDENTITIES,
        "exact_final_urls": _EXPECTED_PRIVATE_DRIVE_IDENTITIES,
        "identities_visible": _EXPECTED_PRIVATE_DRIVE_IDENTITIES,
        "inventory_markers_visible": _EXPECTED_PRIVATE_DRIVE_IDENTITIES,
        "denied_signals": 0,
    }
    if any(
        _non_negative_integer(
            drive[field],
            f"mirror public verification Drive {field}",
        )
        != expected
        for field, expected in expected_drive_counts.items()
    ):
        raise ValueError("mirror public verification Drive access counts are not exact")
    _empty_exceptions(
        drive["exceptions"],
        "mirror public verification Drive exceptions",
    )

    representatives = raw["representatives"]
    if not isinstance(representatives, list) or len(representatives) != len(_PUBLIC_FILE_KINDS):
        raise ValueError("mirror public verification requires exactly seven representatives")
    normalized_representatives: list[dict[str, object]] = []
    kinds: list[str] = []
    for index, value_record in enumerate(representatives):
        record = _mapping(
            value_record,
            _PUBLIC_REPRESENTATIVE_FIELDS,
            f"mirror public representative {index}",
        )
        kind = _text(record["kind"], f"mirror public representative {index} kind")
        kinds.append(kind)
        product_id = _text(
            record["product_id"],
            f"mirror public representative {index} product_id",
        )
        relative_path = _text(
            record["relative_path"],
            f"mirror public representative {index} relative_path",
        )
        parsed_path = PurePosixPath(relative_path)
        if parsed_path.is_absolute() or ".." in parsed_path.parts:
            raise ValueError("mirror public representative relative_path must be package-relative")
        url = _drive_download_url(
            record["url"],
            f"mirror public representative {index} URL",
        )
        final_url = _drive_download_url(
            record["final_url"],
            f"mirror public representative {index} final URL",
        )
        if final_url != url:
            raise ValueError(
                "mirror public representative final URL must exactly match its download URL"
            )
        if (
            _non_negative_integer(
                record["status"],
                f"mirror public representative {index} status",
            )
            != 200
        ):
            raise ValueError("mirror public representative HTTP status must be 200")
        _text(
            record["content_type"],
            f"mirror public representative {index} content_type",
        )
        _text(
            record["content_disposition"],
            f"mirror public representative {index} content_disposition",
        )
        if (
            _non_negative_integer(
                record["retained_temp_files"],
                f"mirror public representative {index} retained_temp_files",
            )
            != 0
        ):
            raise ValueError("mirror public verification retained temporary files must be zero")
        canonical_bytes, canonical_sha256 = _canonical_public_file(
            phases=phases,
            product_id=product_id,
            relative_path=relative_path,
        )
        expected_bytes = _non_negative_integer(
            record["expected_bytes"],
            f"mirror public representative {index} expected_bytes",
        )
        observed_bytes = _non_negative_integer(
            record["observed_bytes"],
            f"mirror public representative {index} observed_bytes",
        )
        expected_sha256 = _required_digest(
            record["expected_sha256"],
            f"mirror public representative {index} expected_sha256",
        )
        observed_sha256 = _required_digest(
            record["observed_sha256"],
            f"mirror public representative {index} observed_sha256",
        )
        if (
            expected_bytes != canonical_bytes
            or observed_bytes != canonical_bytes
            or expected_sha256 != canonical_sha256
            or observed_sha256 != canonical_sha256
        ):
            raise ValueError("mirror public representative differs from its canonical manifest")
        normalized_representatives.append(dict(record))
    if set(kinds) != _PUBLIC_FILE_KINDS or len(set(kinds)) != len(kinds):
        raise ValueError(
            "mirror public verification representative kinds must be exactly "
            "png, svg, mp4, mov, stl, yml, and npz"
        )
    if _text(raw["streaming"], "mirror public verification streaming") != "bounded-memory-chunks":
        raise ValueError("mirror public verification streaming must use bounded-memory-chunks")
    if (
        _non_negative_integer(
            raw["retained_temp_files"],
            "mirror public verification retained_temp_files",
        )
        != 0
    ):
        raise ValueError("mirror public verification retained temporary files must be zero")
    _empty_exceptions(
        raw["exceptions"],
        "mirror public verification exceptions",
    )
    return MappingProxyType(
        {
            "observed_at": raw["observed_at"],
            "transport": raw["transport"],
            "site": dict(site),
            "github": dict(github),
            "drive": dict(drive),
            "representatives": normalized_representatives,
            "streaming": raw["streaming"],
            "retained_temp_files": raw["retained_temp_files"],
            "exceptions": list(raw["exceptions"]),
        }
    )


def _validate_quota(
    value: object,
    *,
    schema_version: int,
) -> Mapping[str, object]:
    expected_fields = _LEGACY_QUOTA_FIELDS if schema_version == 1 else _QUOTA_FIELDS
    raw = _mapping(value, expected_fields, "mirror quota")
    required = raw["required_headroom_bytes"]
    if not isinstance(required, int) or isinstance(required, bool) or required != 10 * 1024**3:
        raise ValueError("mirror quota required_headroom_bytes must be 10737418240")
    for field in ("total_bytes", "used_bytes", "free_bytes"):
        byte_count = raw[field]
        if byte_count is not None and (
            not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0
        ):
            raise ValueError(f"mirror quota {field} must be a non-negative integer or null")
    _optional_text(raw["observed_at"], "mirror quota observed_at")
    if schema_version >= 2:
        canonical_upload_bytes = raw["canonical_upload_bytes"]
        if canonical_upload_bytes is not None and (
            not isinstance(canonical_upload_bytes, int)
            or isinstance(canonical_upload_bytes, bool)
            or canonical_upload_bytes <= 0
        ):
            raise ValueError(
                "mirror quota canonical_upload_bytes must be a positive integer or null"
            )
        canonical_basis = raw["canonical_upload_bytes_basis"]
        if canonical_basis not in {None, _CANONICAL_UPLOAD_BYTES_BASIS}:
            raise ValueError("mirror quota canonical_upload_bytes_basis is unsupported")
        if (canonical_upload_bytes is None) != (canonical_basis is None):
            raise ValueError("mirror quota canonical bytes and basis must be recorded together")
        recorded_values = (
            raw["observed_at"],
            raw["total_bytes"],
            raw["used_bytes"],
            raw["free_bytes"],
            canonical_upload_bytes,
            canonical_basis,
        )
        if any(value is not None for value in recorded_values):
            if any(value is None for value in recorded_values):
                raise ValueError("mirror quota observation fields must be recorded together")
            _iso_timestamp(
                raw["observed_at"],
                "mirror quota observed_at",
                allow_none=False,
                require_utc=True,
            )
            total_bytes = int(raw["total_bytes"])
            used_bytes = int(raw["used_bytes"])
            free_bytes = int(raw["free_bytes"])
            if total_bytes <= 0 or free_bytes <= 0:
                raise ValueError("mirror quota total_bytes and free_bytes must be positive")
            if total_bytes != used_bytes + free_bytes:
                raise ValueError("mirror quota total_bytes must equal used_bytes plus free_bytes")
            if int(canonical_upload_bytes) + int(required) > free_bytes:
                raise ValueError("mirror quota headroom gate failed")
    return MappingProxyType(dict(raw))


def _mirror_product(identifier: str, value: object) -> MirrorProduct:
    raw = _mapping(value, _PRODUCT_FIELDS, f"mirror product {identifier}")
    state = _state(raw["state"], f"mirror product {identifier} state")
    url = _drive_folder_url(raw["url"], f"mirror product {identifier} URL")
    access = _access(raw["access"], f"mirror product {identifier} access")
    drive_id = _opaque_id(raw["drive_id"], f"mirror product {identifier} drive_id")
    if state == _PUBLIC_STATE and (drive_id is None or url is None or access != "public-link"):
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
        verified_at=_optional_text(raw["verified_at"], f"mirror product {identifier} verified_at"),
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
    if state == _PUBLIC_STATE and (drive_id is None or url is None or access != "public-link"):
        raise ValueError(
            f"public-verified mirror phase {slug} requires an opaque ID and public-link folder URL"
        )
    return MirrorPhase(
        slug=slug,
        drive_id=drive_id,
        url=url,
        access=access,
        state=state,
        products=products,
    )


def _expected_registry_products_by_phase() -> dict[str, set[str]]:
    phases = load_phase_registry(_PHASE_REGISTRY)
    phase_slugs = {phase.slug for phase in phases}
    _, products = load_product_registry(
        _PRODUCT_REGISTRY,
        phase_slugs=phase_slugs,
    )
    by_phase = {slug: set() for slug in phase_slugs}
    for product in products:
        for slug in product.phase_slugs:
            by_phase[slug].add(product.identifier)
    return by_phase


def _validate_uploaded_private_terminal(ledger: MirrorLedger) -> None:
    expected_products = _expected_registry_products_by_phase()
    if set(ledger.phases) != set(expected_products) or any(
        set(ledger.phases[slug].products) != product_ids
        for slug, product_ids in expected_products.items()
    ):
        raise ValueError(
            "uploaded-private mirror phase/product registry set differs from "
            "the canonical registries"
        )
    if (
        ledger.root_drive_id is None
        or ledger.root_url is None
        or ledger.root_access != "private"
        or ledger.upload_acceptance is None
    ):
        raise ValueError(
            "uploaded-private mirror root requires a private ID, URL, and acceptance record"
        )

    identities: list[tuple[str, str, str]] = [
        ("mirror root", ledger.root_drive_id, ledger.root_url)
    ]
    for slug, phase in ledger.phases.items():
        if (
            phase.state != "uploaded"
            or phase.access != "private"
            or phase.drive_id is None
            or phase.url is None
        ):
            raise ValueError("uploaded-private mirror requires uploaded private phases")
        identities.append((f"mirror phase {slug}", phase.drive_id, phase.url))
        for product_id, product in phase.products.items():
            if (
                product.state != "uploaded"
                or product.access != "private"
                or product.drive_id is None
                or product.url is None
                or product.package_manifest_sha256 is not None
                or product.verified_at is not None
            ):
                raise ValueError(
                    "uploaded-private mirror requires uploaded, not verified-private, products"
                )
            identities.append(
                (
                    f"mirror product {product_id}",
                    product.drive_id,
                    product.url,
                )
            )

    if len(identities) != _EXPECTED_PRIVATE_DRIVE_IDENTITIES:
        raise ValueError("uploaded-private mirror requires exactly 138 Drive identities")
    drive_ids = [drive_id for _, drive_id, _ in identities]
    drive_urls = [url for _, _, url in identities]
    if len(set(drive_ids)) != len(drive_ids):
        raise ValueError("uploaded-private Drive IDs must be globally unique")
    if len(set(drive_urls)) != len(drive_urls):
        raise ValueError("uploaded-private Drive URLs must be globally unique")
    for label, drive_id, url in identities:
        if _drive_folder_url_token(url) != drive_id:
            raise ValueError(f"{label} URL token must match its recorded Drive ID")

    upload = ledger.upload_acceptance["upload_observation"]
    quota_bytes = ledger.quota["canonical_upload_bytes"]
    quota_basis = ledger.quota["canonical_upload_bytes_basis"]
    if (
        upload["canonical_upload_bytes"] != quota_bytes
        or upload["canonical_upload_bytes_basis"] != quota_basis
    ):
        raise ValueError(
            "uploaded-private canonical upload bytes differ between quota and upload evidence"
        )


def _validate_public_terminal(ledger: MirrorLedger) -> None:
    expected_products = _expected_registry_products_by_phase()
    if set(ledger.phases) != set(expected_products) or any(
        set(ledger.phases[slug].products) != product_ids
        for slug, product_ids in expected_products.items()
    ):
        raise ValueError(
            "public-verified mirror phase/product registry set differs from "
            "the canonical registries"
        )
    if (
        ledger.root_drive_id is None
        or ledger.root_url is None
        or ledger.root_access != "public-link"
        or ledger.upload_acceptance is None
        or ledger.public_verification is None
    ):
        raise ValueError(
            "public-verified mirror root requires a public identity and both acceptance records"
        )
    if (
        ledger.site_public_url is None
        or ledger.site_audience != "public"
        or ledger.site_state != "public-verified"
    ):
        raise ValueError("public-verified mirror requires a public, public-verified Site")

    identities: list[tuple[str, str, str]] = [
        ("mirror root", ledger.root_drive_id, ledger.root_url)
    ]
    for slug, phase in ledger.phases.items():
        if (
            phase.state != _PUBLIC_STATE
            or phase.access != "public-link"
            or phase.drive_id is None
            or phase.url is None
        ):
            raise ValueError("public-verified mirror requires public-verified public phases")
        identities.append((f"mirror phase {slug}", phase.drive_id, phase.url))
        for product_id, product in phase.products.items():
            if (
                product.state != _PUBLIC_STATE
                or product.access != "public-link"
                or product.drive_id is None
                or product.url is None
                or product.package_manifest_sha256 is not None
                or product.verified_at is not None
            ):
                raise ValueError(
                    "public-verified mirror requires public products without "
                    "waived full-round-trip digest claims"
                )
            identities.append(
                (
                    f"mirror product {product_id}",
                    product.drive_id,
                    product.url,
                )
            )
    if len(identities) != _EXPECTED_PRIVATE_DRIVE_IDENTITIES:
        raise ValueError("public-verified mirror requires exactly 138 Drive identities")
    drive_ids = [drive_id for _, drive_id, _ in identities]
    drive_urls = [url for _, _, url in identities]
    if len(set(drive_ids)) != len(drive_ids):
        raise ValueError("public-verified Drive IDs must be globally unique")
    if len(set(drive_urls)) != len(drive_urls):
        raise ValueError("public-verified Drive URLs must be globally unique")
    for label, drive_id, url in identities:
        if _drive_folder_url_token(url) != drive_id:
            raise ValueError(f"{label} URL token must match its recorded Drive ID")

    upload = ledger.upload_acceptance["upload_observation"]
    if (
        upload["canonical_upload_bytes"] != ledger.quota["canonical_upload_bytes"]
        or upload["canonical_upload_bytes_basis"] != ledger.quota["canonical_upload_bytes_basis"]
    ):
        raise ValueError(
            "public-verified canonical upload bytes differ between quota and upload evidence"
        )
    round_trip = ledger.upload_acceptance["round_trip_verification"]
    if round_trip["status"] != "not-performed" or round_trip["disposition"] != "waived-by-user":
        raise ValueError(
            "public-verified mirror must preserve the waived, not-performed round trip"
        )


def load_mirror_ledger(path: str | Path) -> MirrorLedger:
    """Load and validate a local mirror ledger without deriving remote identities."""
    ledger_path = Path(path).resolve()
    try:
        parsed = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("mirror ledger cannot be read as YAML") from error
    if not isinstance(parsed, dict):
        raise ValueError("mirror ledger fields differ from the mirror schema")
    schema_version = parsed.get("schema_version")
    if schema_version == 1:
        raw = _mapping(parsed, _LEGACY_TOP_LEVEL_FIELDS, "mirror ledger")
        upload_acceptance = None
        raw_public_verification = None
    elif schema_version == 2:
        raw = _mapping(parsed, _SCHEMA_2_TOP_LEVEL_FIELDS, "mirror ledger")
        upload_acceptance = (
            None
            if raw["upload_acceptance"] is None
            else _validate_upload_acceptance(raw["upload_acceptance"])
        )
        raw_public_verification = None
    elif schema_version == 3:
        raw = _mapping(parsed, _SCHEMA_3_TOP_LEVEL_FIELDS, "mirror ledger")
        upload_acceptance = (
            None
            if raw["upload_acceptance"] is None
            else _validate_upload_acceptance(raw["upload_acceptance"])
        )
        raw_public_verification = raw["public_verification"]
    else:
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
        _text(slug, "mirror phase slug"): _mirror_phase(_text(slug, "mirror phase slug"), phase)
        for slug, phase in raw_phases.items()
    }
    product_ids = [product_id for phase in phases.values() for product_id in phase.products]
    if len(set(product_ids)) != len(product_ids):
        raise ValueError("mirror product IDs must be unique across phases")
    site = _mapping(raw["site"], _SITE_FIELDS, "mirror site")
    root_drive_id = _opaque_id(root["drive_id"], "mirror root drive_id")
    root_url = _drive_folder_url(root["url"], "mirror root URL")
    root_access = _access(root["access"], "mirror root access")
    root_state = _state(root["state"], "mirror root state")
    if root_state == _PUBLIC_STATE and (
        root_drive_id is None or root_url is None or root_access != "public-link"
    ):
        raise ValueError(
            "public-verified mirror root requires an opaque ID and public-link folder URL"
        )
    site_public_url = _sites_url(
        site["public_url"],
        "mirror site public_url",
        allow_none=True,
    )
    public_verification = (
        None
        if raw_public_verification is None
        else _validate_public_verification(
            raw_public_verification,
            root_url=root_url,
            site_public_url=site_public_url,
            phases=phases,
        )
    )
    ledger = MirrorLedger(
        path=ledger_path,
        provider="google-drive",
        account=_ACCOUNT,
        local_mount=local_mount,
        transport=transport,
        quota=_validate_quota(raw["quota"], schema_version=schema_version),
        root_drive_id=root_drive_id,
        root_url=root_url,
        root_access=root_access,
        root_state=root_state,
        upload_acceptance=upload_acceptance,
        public_verification=public_verification,
        phases=phases,
        site_draft_url=(
            _sites_editor_url(site["draft_url"], "mirror site draft_url")
            if site["state"] in {"draft-complete", "public-verified"}
            else _sites_url(site["draft_url"], "mirror site draft_url", allow_none=False) or ""
        ),
        site_public_url=site_public_url,
        site_audience=_text(site["audience"], "mirror site audience"),
        site_state=_state(site["state"], "mirror site state"),
    )
    if ledger.root_state in _INVENTORY_COMPLETE_STATES and (
        ledger.phase_count != _EXPECTED_COMPLETE_PHASES
        or ledger.product_count != _EXPECTED_COMPLETE_PRODUCTS
    ):
        raise ValueError("complete mirror state requires exactly 12 phases and 125 products")
    if ledger.root_state == "complete-private":
        if (
            ledger.root_drive_id is None
            or ledger.root_url is None
            or ledger.root_access != "private"
        ):
            raise ValueError("complete-private mirror root requires a private ID and URL")
        for phase in ledger.phases.values():
            if (
                phase.state != "verified-private"
                or phase.access != "private"
                or phase.drive_id is None
                or phase.url is None
            ):
                raise ValueError("complete-private mirror requires verified private phases")
            for product in phase.products.values():
                if (
                    product.state != "verified-private"
                    or product.access != "private"
                    or product.drive_id is None
                    or product.url is None
                    or product.package_manifest_sha256 is None
                    or product.verified_at is None
                ):
                    raise ValueError("complete-private mirror requires verified private products")
    if ledger.root_state == "uploaded-private":
        _validate_uploaded_private_terminal(ledger)
    if schema_version == 3 and ledger.root_state != _PUBLIC_STATE:
        raise ValueError("schema-3 mirror ledger requires public-verified root state")
    if schema_version == 3:
        _validate_public_terminal(ledger)
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


def _reject_symlink_parents(path: Path, label: str) -> None:
    current = path.parent
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"{label} parent must not be a symlink")
        current = current.parent


def _write_new_mirror_mapping_atomic(
    path: Path,
    raw: Mapping[str, object],
) -> None:
    if path.is_symlink():
        raise ValueError("mirror initialization output must not be a symlink")
    if path.exists():
        raise ValueError("mirror initialization refuses an existing output")
    _reject_symlink_parents(path, "mirror initialization output")
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_parents(path, "mirror initialization output")
    partial: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".partial",
            delete=False,
        ) as handle:
            partial = Path(handle.name)
            yaml.safe_dump(dict(raw), handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        load_mirror_ledger(partial)
        try:
            os.link(partial, path, follow_symlinks=False)
        except FileExistsError as error:
            raise ValueError("mirror initialization refuses an existing output") from error
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if partial is not None and partial.exists():
            partial.unlink()


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
        "schema_version": 2,
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
            "canonical_upload_bytes": None,
            "canonical_upload_bytes_basis": None,
        },
        "root": {
            "drive_id": None,
            "url": None,
            "access": "private",
            "state": "planned",
        },
        "upload_acceptance": None,
        "phases": {
            phase.slug: {
                "drive_id": None,
                "url": None,
                "access": "private",
                "state": "planned",
                "products": {
                    product.identifier: _initial_product() for product in by_phase[phase.slug]
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
    output = Path(output_path).absolute()
    _write_new_mirror_mapping_atomic(output, raw)
    ledger = load_mirror_ledger(output)
    if (
        ledger.phase_count != _EXPECTED_COMPLETE_PHASES
        or ledger.product_count != _EXPECTED_COMPLETE_PRODUCTS
    ):
        raise ValueError("mirror initialization requires exactly 12 phases and 125 products")
    return ledger


def _write_mirror_mapping_atomic(path: Path, raw: Mapping[str, object]) -> None:
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".partial",
            delete=False,
        ) as handle:
            partial = Path(handle.name)
            yaml.safe_dump(dict(raw), handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(partial, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if partial is not None and partial.exists():
            partial.unlink()


def _validate_mirror_mapping_candidate(
    path: Path,
    raw: Mapping[str, object],
) -> None:
    candidate: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".validate",
            delete=False,
        ) as handle:
            candidate = Path(handle.name)
            yaml.safe_dump(dict(raw), handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        load_mirror_ledger(candidate)
    finally:
        if candidate is not None and candidate.exists():
            candidate.unlink()


def set_mirror_root(
    *,
    mirror_path: str | Path,
    transport: str,
    drive_id: str,
    url: str,
    access: str,
    state: str,
) -> MirrorLedger:
    """Atomically bind a planned private ledger to one exact Drive root."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    if transport not in {"drive-for-desktop", "chrome-folder-upload"}:
        raise ValueError("root transport must be an upload-capable transport")
    if access != "private" or state != "created":
        raise ValueError("new mirror roots must remain private and created")
    validated_id = _opaque_id(drive_id, "mirror root drive_id")
    validated_url = _drive_folder_url(url, "mirror root URL")
    if validated_id is None or validated_url is None:
        raise ValueError("mirror root requires an exact opaque ID and folder URL")
    if ledger.transport not in {"undecided", transport}:
        raise ValueError("set-root refuses to replace the recorded transport")
    if ledger.root_state not in {"planned", "created"}:
        raise ValueError("set-root refuses to replace a progressed root state")
    if ledger.root_drive_id not in {None, validated_id}:
        raise ValueError("set-root refuses to replace the recorded root identity")
    if ledger.root_url not in {None, validated_url}:
        raise ValueError("set-root refuses to replace the recorded root URL")
    if (
        ledger.transport == transport
        and ledger.root_drive_id == validated_id
        and ledger.root_url == validated_url
        and ledger.root_access == access
        and ledger.root_state == state
    ):
        return ledger

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["transport"] = transport
    raw["root"] = {
        "drive_id": validated_id,
        "url": validated_url,
        "access": access,
        "state": state,
    }
    _write_mirror_mapping_atomic(path, raw)
    return load_mirror_ledger(path)


def record_remote_folders(
    *,
    mirror_path: str | Path,
    inventory: object,
) -> MirrorLedger:
    """Atomically record one complete, private remote folder inventory."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    if ledger.transport == "undecided":
        raise ValueError("remote folders require a recorded upload transport")
    if ledger.root_state not in {"created", "uploaded"}:
        raise ValueError("remote folders require a created or uploaded root")
    raw_inventory = _mapping(
        inventory,
        {"account", "root", "phases"},
        "remote folder inventory",
    )
    if raw_inventory["account"] != _ACCOUNT:
        raise ValueError(f"remote folder account must be exactly {_ACCOUNT}")
    remote_root = _mapping(
        raw_inventory["root"],
        {"drive_id", "url"},
        "remote folder root",
    )
    root_drive_id = _opaque_id(remote_root["drive_id"], "remote folder root drive_id")
    root_url = _drive_folder_url(remote_root["url"], "remote folder root URL")
    if (
        root_drive_id is None
        or root_url is None
        or root_drive_id != ledger.root_drive_id
        or root_url != ledger.root_url
    ):
        raise ValueError("remote folder root differs from the recorded root")
    remote_phases = raw_inventory["phases"]
    if not isinstance(remote_phases, dict) or set(remote_phases) != set(ledger.phases):
        raise ValueError("remote phase inventory differs from the mirror ledger")

    normalized_phases: dict[str, dict[str, object]] = {}
    all_drive_ids = [root_drive_id]
    all_urls = [root_url]
    for slug, phase in ledger.phases.items():
        remote_phase = _mapping(
            remote_phases[slug],
            {"drive_id", "url", "products"},
            f"remote phase {slug}",
        )
        phase_drive_id = _opaque_id(remote_phase["drive_id"], f"remote phase {slug} drive_id")
        phase_url = _drive_folder_url(remote_phase["url"], f"remote phase {slug} URL")
        remote_products = remote_phase["products"]
        if (
            phase_drive_id is None
            or phase_url is None
            or not isinstance(remote_products, dict)
            or set(remote_products) != set(phase.products)
        ):
            raise ValueError(f"remote product inventory differs for phase {slug}")
        normalized_products: dict[str, dict[str, str]] = {}
        all_drive_ids.append(phase_drive_id)
        all_urls.append(phase_url)
        for product_id in phase.products:
            remote_product = _mapping(
                remote_products[product_id],
                {"drive_id", "url"},
                f"remote product {product_id}",
            )
            product_drive_id = _opaque_id(
                remote_product["drive_id"],
                f"remote product {product_id} drive_id",
            )
            product_url = _drive_folder_url(
                remote_product["url"],
                f"remote product {product_id} URL",
            )
            if product_drive_id is None or product_url is None:
                raise ValueError(f"remote product {product_id} requires an ID and URL")
            all_drive_ids.append(product_drive_id)
            all_urls.append(product_url)
            normalized_products[product_id] = {
                "drive_id": product_drive_id,
                "url": product_url,
            }
        normalized_phases[slug] = {
            "drive_id": phase_drive_id,
            "url": phase_url,
            "products": normalized_products,
        }
    if len(set(all_drive_ids)) != len(all_drive_ids):
        raise ValueError("remote folder drive IDs must be unique")
    if len(set(all_urls)) != len(all_urls):
        raise ValueError("remote folder URLs must be unique")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    changed = raw["root"]["state"] != "uploaded"
    raw["root"]["state"] = "uploaded"
    for slug, remote_phase in normalized_phases.items():
        phase_record = raw["phases"][slug]
        for field in ("drive_id", "url"):
            existing = phase_record[field]
            observed = remote_phase[field]
            if existing not in {None, observed}:
                raise ValueError(f"remote phase {slug} refuses to replace {field}")
            changed = changed or existing != observed
            phase_record[field] = observed
        changed = changed or phase_record["state"] != "uploaded"
        phase_record["access"] = "private"
        phase_record["state"] = "uploaded"
        for product_id, remote_product in remote_phase["products"].items():
            product_record = phase_record["products"][product_id]
            for field in ("drive_id", "url"):
                existing = product_record[field]
                observed = remote_product[field]
                if existing not in {None, observed}:
                    raise ValueError(f"remote product {product_id} refuses to replace {field}")
                changed = changed or existing != observed
                product_record[field] = observed
            changed = changed or product_record["state"] != "uploaded"
            product_record["access"] = "private"
            product_record["state"] = "uploaded"
    if not changed:
        return ledger
    _write_mirror_mapping_atomic(path, raw)
    return load_mirror_ledger(path)


def record_uploaded_private_acceptance(
    *,
    mirror_path: str | Path,
    acceptance: object,
) -> MirrorLedger:
    """Record upload-only private acceptance without claiming byte verification."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    normalized = _validate_upload_acceptance(acceptance)
    if ledger.root_state not in {"uploaded", "uploaded-private"}:
        raise ValueError("uploaded-private acceptance requires an uploaded mirror root")
    if (
        ledger.transport == "undecided"
        or ledger.root_drive_id is None
        or ledger.root_url is None
        or ledger.root_access != "private"
    ):
        raise ValueError(
            "uploaded-private acceptance requires a private root identity and recorded transport"
        )
    if any(
        ledger.quota[field] is None
        for field in ("observed_at", "total_bytes", "used_bytes", "free_bytes")
    ):
        raise ValueError("uploaded-private acceptance requires a quota observation")
    if any(
        phase.state != "uploaded"
        or phase.access != "private"
        or phase.drive_id is None
        or phase.url is None
        for phase in ledger.phases.values()
    ):
        raise ValueError("uploaded-private acceptance requires uploaded private phase identities")
    if any(
        product.state != "uploaded"
        or product.access != "private"
        or product.drive_id is None
        or product.url is None
        or product.package_manifest_sha256 is not None
        or product.verified_at is not None
        for phase in ledger.phases.values()
        for product in phase.products.values()
    ):
        raise ValueError(
            "uploaded-private acceptance requires uploaded, not "
            "verified-private, product identities"
        )
    if ledger.root_state == "uploaded-private":
        if ledger.upload_acceptance == normalized:
            return ledger
        raise ValueError("record-uploaded-private refuses to replace terminal acceptance")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["schema_version"] = 2
    raw["upload_acceptance"] = {field: dict(value) for field, value in normalized.items()}
    raw["root"]["state"] = "uploaded-private"
    _validate_mirror_mapping_candidate(path, raw)
    _write_mirror_mapping_atomic(path, raw)
    return load_mirror_ledger(path)


def record_site_draft(
    *,
    mirror_path: str | Path,
    editor_url: str,
    proposed_public_url: str,
    audience: str,
    state: str,
) -> MirrorLedger:
    """Atomically record one complete, still-unpublished university Site draft."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    if ledger.root_state != "uploaded-private":
        raise ValueError("site draft requires an uploaded-private mirror root")
    if audience != "university-only" or state != "draft-complete":
        raise ValueError("site draft must remain university-only and draft-complete")
    validated_editor_url = _sites_editor_url(editor_url, "site draft editor URL")
    validated_public_url = _sites_url(
        proposed_public_url,
        "site draft proposed public URL",
        allow_none=False,
    )
    if validated_public_url is None:  # pragma: no cover - guarded by allow_none=False
        raise ValueError("site draft proposed public URL must be non-empty text")
    requested = {
        "draft_url": validated_editor_url,
        "public_url": validated_public_url,
        "audience": audience,
        "state": state,
    }
    current = {
        "draft_url": ledger.site_draft_url,
        "public_url": ledger.site_public_url,
        "audience": ledger.site_audience,
        "state": ledger.site_state,
    }
    if current == requested:
        return ledger
    if ledger.site_state == "draft-complete":
        raise ValueError("record-site-draft refuses to replace a complete draft")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["site"] = requested
    _validate_mirror_mapping_candidate(path, raw)
    _write_mirror_mapping_atomic(path, raw)
    return load_mirror_ledger(path)


def record_public_verification(
    *,
    mirror_path: str | Path,
    verification: object,
) -> MirrorLedger:
    """Atomically record exact public access without claiming a full byte round trip."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    normalized = _validate_public_verification(
        verification,
        root_url=ledger.root_url,
        site_public_url=ledger.site_public_url,
        phases=ledger.phases,
    )
    normalized_frozen = _deep_freeze(normalized)
    if ledger.root_state == _PUBLIC_STATE:
        if ledger.public_verification == normalized_frozen:
            return ledger
        raise ValueError("record-public-verified refuses to replace terminal public verification")
    if ledger.root_state != "uploaded-private":
        raise ValueError("public verification requires an uploaded-private mirror root")
    if (
        ledger.site_state != "draft-complete"
        or ledger.site_audience != "university-only"
        or ledger.site_public_url is None
    ):
        raise ValueError("public verification requires the complete university-only Site draft")
    if ledger.upload_acceptance is None:
        raise ValueError("public verification requires the Task 8 upload acceptance")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["schema_version"] = 3
    raw["public_verification"] = _deep_thaw(normalized_frozen)
    raw["root"]["access"] = "public-link"
    raw["root"]["state"] = _PUBLIC_STATE
    raw["site"]["audience"] = "public"
    raw["site"]["state"] = _PUBLIC_STATE
    for phase in raw["phases"].values():
        phase["access"] = "public-link"
        phase["state"] = _PUBLIC_STATE
        for product in phase["products"].values():
            product["access"] = "public-link"
            product["state"] = _PUBLIC_STATE
    _validate_mirror_mapping_candidate(path, raw)
    _write_mirror_mapping_atomic(path, raw)
    return load_mirror_ledger(path)


def record_mirror_quota(
    *,
    mirror_path: str | Path,
    observed_at: str,
    total_bytes: int,
    used_bytes: int,
    free_bytes: int,
    canonical_bytes: int,
) -> MirrorLedger:
    """Atomically record a live quota observation only when the gate passes."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    _iso_timestamp(
        observed_at,
        "quota observed_at",
        allow_none=False,
        require_utc=True,
    )
    for label, value in (
        ("total_bytes", total_bytes),
        ("used_bytes", used_bytes),
        ("free_bytes", free_bytes),
        ("canonical_bytes", canonical_bytes),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"quota {label} must be a non-negative integer")
    if total_bytes == 0 or free_bytes == 0 or canonical_bytes == 0:
        raise ValueError("quota total_bytes, free_bytes, and canonical_bytes must be positive")
    if used_bytes + free_bytes != total_bytes:
        raise ValueError("quota total_bytes must equal used_bytes plus free_bytes")
    required_headroom = int(ledger.quota["required_headroom_bytes"])
    if canonical_bytes + required_headroom > free_bytes:
        raise ValueError("quota headroom gate failed")
    quota = {
        "observed_at": observed_at,
        "total_bytes": total_bytes,
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "required_headroom_bytes": required_headroom,
        "canonical_upload_bytes": canonical_bytes,
        "canonical_upload_bytes_basis": _CANONICAL_UPLOAD_BYTES_BASIS,
    }
    if dict(ledger.quota) == quota:
        return ledger
    if ledger.root_state in _INVENTORY_COMPLETE_STATES:
        raise ValueError("record-quota refuses to replace terminal quota")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw["schema_version"] == 1:
        raw["schema_version"] = 2
        raw["upload_acceptance"] = None
    raw["quota"] = quota
    _validate_mirror_mapping_candidate(path, raw)
    _write_mirror_mapping_atomic(path, raw)
    return load_mirror_ledger(path)


def _expected_phase_files(canonical_phase_root: Path) -> dict[str, str]:
    phase_manifest = canonical_phase_root / "phase-package.yml"
    phase_package = validate_phase_package(phase_manifest)
    expected = {"phase-package.yml": sha256_file(phase_manifest)}
    for product_id in phase_package.product_ids:
        manifest = canonical_phase_root / "products" / product_id / "product-package.yml"
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
    for root, directories, filenames in os.walk(downloaded_phase_root, followlinks=False):
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
                raise ValueError(f"downloaded phase must not contain a symlink: {relative}")
            if not path.is_file():
                raise ValueError(f"downloaded phase entry must be a regular file: {relative}")
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
            raise ValueError(f"downloaded phase must not contain a symlink: {relative}")
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


def _exact_phase_directories(root: Path, expected: set[str], label: str) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} must be a real directory")
    observed: set[str] = set()
    for entry in root.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            raise ValueError(f"{label} must contain only real phase directories")
        observed.add(entry.name)
    if observed != expected:
        raise ValueError(f"{label} phase inventory differs from the mirror ledger")


def reconcile_downloaded_mirror(
    *,
    canonical_root: str | Path,
    download_root: str | Path,
    mirror_path: str | Path,
) -> MirrorReconciliation:
    """Reconcile all 12 downloaded phases before one atomic state promotion."""
    path = Path(mirror_path).absolute()
    if path.is_symlink():
        raise ValueError("mirror ledger must not be a symlink")
    ledger = load_mirror_ledger(path)
    if ledger.root_state != "uploaded":
        raise ValueError("reconciliation requires an uploaded mirror root")
    if ledger.root_access != "private" or ledger.root_drive_id is None or ledger.root_url is None:
        raise ValueError("reconciliation requires a private remote root identity")
    for phase in ledger.phases.values():
        if (
            phase.state != "uploaded"
            or phase.access != "private"
            or phase.drive_id is None
            or phase.url is None
        ):
            raise ValueError("reconciliation requires uploaded private phase identities")
        for product in phase.products.values():
            if (
                product.state != "uploaded"
                or product.access != "private"
                or product.drive_id is None
                or product.url is None
            ):
                raise ValueError("reconciliation requires uploaded private product identities")

    canonical = Path(canonical_root).absolute()
    downloaded = Path(download_root).absolute()
    expected_phases = set(ledger.phases)
    _exact_phase_directories(canonical, expected_phases, "canonical root")
    _exact_phase_directories(downloaded, expected_phases, "download root")

    results: dict[str, DownloadReconciliation] = {}
    phase_packages = {}
    for slug, phase in ledger.phases.items():
        phase_package = validate_phase_package(canonical / slug / "phase-package.yml")
        if set(phase_package.product_ids) != set(phase.products):
            raise ValueError(f"canonical product inventory differs for phase {slug}")
        phase_packages[slug] = phase_package
        results[slug] = reconcile_downloaded_phase(
            canonical / slug,
            downloaded / slug,
        )
    missing = sum(len(result.missing) for result in results.values())
    mismatched = sum(len(result.mismatched) for result in results.values())
    unexpected = sum(len(result.unexpected) for result in results.values())
    if missing or mismatched or unexpected:
        raise ValueError(
            "reconciliation failed "
            f"missing={missing} mismatched={mismatched} "
            f"unexpected={unexpected}"
        )

    verified_at = (
        datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["root"]["access"] = "private"
    raw["root"]["state"] = "complete-private"
    for slug, phase_package in phase_packages.items():
        phase_record = raw["phases"][slug]
        phase_record["access"] = "private"
        phase_record["state"] = "verified-private"
        for product_id, digest in phase_package.manifest_sha256_by_product.items():
            product_record = phase_record["products"][product_id]
            product_record["access"] = "private"
            product_record["state"] = "verified-private"
            product_record["package_manifest_sha256"] = digest
            product_record["verified_at"] = verified_at
    _write_mirror_mapping_atomic(path, raw)
    updated = load_mirror_ledger(path)
    return MirrorReconciliation(
        ledger=updated,
        phase_count=updated.phase_count,
        product_count=updated.product_count,
        expected_files=sum(result.expected_files for result in results.values()),
        verified_files=sum(result.verified_files for result in results.values()),
        missing=0,
        mismatched=0,
        unexpected=0,
    )


def validate_mirror_ledger(
    *,
    mirror_path: str | Path,
    require_state: str,
) -> MirrorValidation:
    """Validate the exact requested mirror state without changing the ledger."""
    ledger = load_mirror_ledger(mirror_path)
    if ledger.root_state != require_state:
        raise ValueError(f"mirror root state is {ledger.root_state}, not {require_state}")
    verified_private = sum(
        product.state == "verified-private"
        and product.access == "private"
        and product.drive_id is not None
        and product.url is not None
        and product.package_manifest_sha256 is not None
        and product.verified_at is not None
        for phase in ledger.phases.values()
        for product in phase.products.values()
    )
    if require_state in {"complete-private", "uploaded-private", _PUBLIC_STATE}:
        if ledger.transport == "undecided":
            raise ValueError(f"{require_state} mirror requires a recorded transport")
        if any(
            ledger.quota[field] is None
            for field in (
                "observed_at",
                "total_bytes",
                "used_bytes",
                "free_bytes",
            )
        ):
            raise ValueError(f"{require_state} mirror requires a quota observation")
    if require_state == "complete-private":
        if verified_private != _EXPECTED_COMPLETE_PRODUCTS:
            raise ValueError("complete-private mirror requires 125 verified-private products")
    if require_state == "uploaded-private" and verified_private != 0:
        raise ValueError("uploaded-private mirror must not claim verified-private products")
    if require_state == _PUBLIC_STATE:
        if (
            ledger.public_product_count != _EXPECTED_COMPLETE_PRODUCTS
            or len(public_product_urls(ledger)) != _EXPECTED_COMPLETE_PRODUCTS
            or ledger.site_audience != "public"
            or ledger.site_state != _PUBLIC_STATE
            or ledger.public_verification is None
        ):
            raise ValueError(
                "public-verified mirror requires 125 public products and a public Site"
            )
        if verified_private != 0:
            raise ValueError("public-verified mirror must not claim verified-private products")
    return MirrorValidation(
        ledger=ledger,
        verified_private_products=verified_private,
    )


def export_local_mirror(
    *,
    mirror_path: str | Path,
    output_path: str | Path,
    require_state: str,
) -> Path:
    """Write an exact validated ledger copy for last-file remote upload."""
    validation = validate_mirror_ledger(
        mirror_path=mirror_path,
        require_state=require_state,
    )
    source = validation.ledger.path
    output = Path(output_path).absolute()
    if output.is_symlink():
        raise ValueError("local mirror output must not be a symlink")
    if output == source:
        raise ValueError("local mirror output must differ from the ledger")
    payload = source.read_bytes()
    if output.is_file() and output.read_bytes() == payload:
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    partial: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".partial",
            delete=False,
        ) as handle:
            partial = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(partial, output)
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if partial is not None and partial.exists():
            partial.unlink()
    return output


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
    if (
        mirror_phase is not None
        and mirror_phase.url is not None
        and (mirror_phase.state == _PUBLIC_STATE or allow_private_links)
    ):
        link_label = (
            "Open the public full-resolution Drive phase folder"
            if mirror_phase.state == _PUBLIC_STATE
            else "Open the restricted Drive phase folder for signed-in review"
        )
        page_lines.extend(("", f"[{link_label}]({mirror_phase.url})"))
    page_lines.extend(("", "## Products", ""))
    for product in products:
        page_lines.append(f"- **{product.title}** — {product.caption}")
        full_resolution = public_urls.get(product.identifier)
        if full_resolution is not None:
            page_lines.append(f"  - [Open full-resolution package]({full_resolution})")
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
        product_id for phase in ledger.phases.values() for product_id in phase.products
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
                *(f"- [{phase.display_name}](phases/{phase.slug}.md)" for phase in phases),
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
        phase_products = tuple(product for product in products if phase.slug in product.phase_slugs)
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
                    if ledger.phases[phase.slug].state == _PUBLIC_STATE or allow_private_links
                    else None
                ),
                "product_ids": [
                    product.identifier for product in products if phase.slug in product.phase_slugs
                ],
            }
            for phase in phases
        ],
        "products": [
            {
                "id": product.identifier,
                "phase_slugs": list(product.phase_slugs),
                "delivery": {"full_resolution_url": public_urls.get(product.identifier)},
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
    "MirrorReconciliation",
    "MirrorValidation",
    "MirrorPhase",
    "MirrorProduct",
    "build_google_site_source",
    "export_local_mirror",
    "initialize_mirror_ledger",
    "load_mirror_ledger",
    "public_product_urls",
    "reconcile_downloaded_phase",
    "reconcile_downloaded_mirror",
    "record_mirror_quota",
    "record_remote_folders",
    "record_uploaded_private_acceptance",
    "set_mirror_root",
    "validate_mirror_ledger",
]

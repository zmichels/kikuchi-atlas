from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.atlas import (
    build_google_site_source,
    initialize_mirror_ledger,
    load_mirror_ledger,
    load_product_package,
    public_product_urls,
    reconcile_downloaded_phase,
)


ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "docs/atlas/PHASE_REGISTRY.yml"
PRODUCTS = ROOT / "docs/atlas/PRODUCT_REGISTRY.yml"


def _write_yaml(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _mirror_mapping(
    *,
    account: str = "zmichels@umn.edu",
    local_mount: str | None = None,
    root_state: str = "planned",
    phases: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": "google-drive",
        "account": account,
        "local_mount": local_mount,
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
            "state": root_state,
        },
        "phases": phases or {},
        "site": {
            "draft_url": "https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test",
            "public_url": None,
            "audience": "university-only",
            "state": "draft",
        },
    }


def _mirror_product(
    product_id: str,
    *,
    state: str,
    drive_id: str,
    url: str,
) -> dict[str, object]:
    return {
        "drive_id": drive_id,
        "url": url,
        "access": "private" if state != "public-verified" else "public-link",
        "state": state,
        "package_manifest_sha256": None,
        "verified_at": None,
    }


def test_mirror_ledger_rejects_wrong_account_and_local_mount(tmp_path: Path) -> None:
    wrong_account = _write_yaml(
        tmp_path / "wrong-account.yml",
        _mirror_mapping(
            account="mich0201@umn.edu",
            local_mount="/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu",
        ),
    )
    with pytest.raises(ValueError, match="zmichels@umn.edu"):
        load_mirror_ledger(wrong_account)

    wrong_mount = _write_yaml(
        tmp_path / "wrong-mount.yml",
        _mirror_mapping(
            local_mount="/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu"
        ),
    )
    with pytest.raises(ValueError, match="mich0201"):
        load_mirror_ledger(wrong_mount)


def test_drive_ids_and_urls_are_validated_independently(tmp_path: Path) -> None:
    phases = {
        "quartz": {
            "drive_id": "opaque-phase-id",
            "url": "https://drive.google.com/drive/folders/different-opaque-url-id",
            "access": "private",
            "state": "planned",
            "products": {},
        }
    }
    ledger = load_mirror_ledger(
        _write_yaml(tmp_path / "valid.yml", _mirror_mapping(phases=phases))
    )
    assert ledger.phases["quartz"].drive_id == "opaque-phase-id"
    assert (
        ledger.phases["quartz"].url
        == "https://drive.google.com/drive/folders/different-opaque-url-id"
    )

    invalid_id = _mirror_mapping(phases=phases)
    invalid_id["root"]["drive_id"] = "derived/from/a/url"  # type: ignore[index]
    with pytest.raises(ValueError, match="opaque"):
        load_mirror_ledger(_write_yaml(tmp_path / "invalid-id.yml", invalid_id))

    invalid_url = _mirror_mapping(phases=phases)
    invalid_url["root"]["url"] = "https://example.com/drive/folders/not-google"  # type: ignore[index]
    with pytest.raises(ValueError, match="Google Drive folder URL"):
        load_mirror_ledger(_write_yaml(tmp_path / "invalid-url.yml", invalid_url))


def test_complete_state_requires_twelve_phases_and_125_products(tmp_path: Path) -> None:
    incomplete = _mirror_mapping(
        root_state="complete-private",
        phases={
            "quartz": {
                "drive_id": None,
                "url": None,
                "access": "private",
                "state": "verified-private",
                "products": {},
            }
        },
    )
    with pytest.raises(ValueError, match="12 phases and 125 products"):
        load_mirror_ledger(_write_yaml(tmp_path / "incomplete.yml", incomplete))


def test_public_urls_include_only_public_verified_products(tmp_path: Path) -> None:
    phases = {
        "quartz": {
            "drive_id": "phase-id",
            "url": "https://drive.google.com/drive/folders/phase-id",
            "access": "private",
            "state": "planned",
            "products": {
                "quartz-demo": _mirror_product(
                    "quartz-demo",
                    state="public-verified",
                    drive_id="verified-id",
                    url="https://drive.google.com/drive/folders/verified-id",
                ),
                "quartz-private": _mirror_product(
                    "quartz-private",
                    state="verified-private",
                    drive_id="private-id",
                    url="https://drive.google.com/drive/folders/private-id",
                ),
                "quartz-uploaded": _mirror_product(
                    "quartz-uploaded",
                    state="uploaded",
                    drive_id="uploaded-id",
                    url="https://drive.google.com/drive/folders/uploaded-id",
                ),
            },
        }
    }
    ledger = load_mirror_ledger(
        _write_yaml(tmp_path / "mixed.yml", _mirror_mapping(phases=phases))
    )
    assert public_product_urls(ledger) == {
        "quartz-demo": "https://drive.google.com/drive/folders/verified-id"
    }


def test_ledger_rejects_duplicate_product_ids(tmp_path: Path) -> None:
    duplicate = _mirror_product(
        "shared-id",
        state="uploaded",
        drive_id="shared-folder",
        url="https://drive.google.com/drive/folders/shared-folder",
    )
    phases = {
        slug: {
            "drive_id": f"{slug}-id",
            "url": f"https://drive.google.com/drive/folders/{slug}-id",
            "access": "private",
            "state": "planned",
            "products": {"shared-id": duplicate},
        }
        for slug in ("quartz", "forsterite")
    }
    with pytest.raises(ValueError, match="unique"):
        load_mirror_ledger(
            _write_yaml(tmp_path / "duplicate.yml", _mirror_mapping(phases=phases))
        )


def test_ledger_rejects_public_verified_product_without_opaque_id(
    tmp_path: Path,
) -> None:
    unbound = _mirror_product(
        "quartz-public",
        state="public-verified",
        drive_id="public-folder",
        url="https://drive.google.com/drive/folders/public-folder",
    )
    unbound["drive_id"] = None
    phases = {
        "quartz": {
            "drive_id": "quartz-id",
            "url": "https://drive.google.com/drive/folders/quartz-id",
            "access": "private",
            "state": "planned",
            "products": {"quartz-public": unbound},
        }
    }
    with pytest.raises(ValueError, match="opaque ID"):
        load_mirror_ledger(
            _write_yaml(tmp_path / "unbound.yml", _mirror_mapping(phases=phases))
        )


def test_ledger_rejects_public_verified_phase_without_public_access(
    tmp_path: Path,
) -> None:
    phases = {
        "quartz": {
            "drive_id": "quartz-id",
            "url": "https://drive.google.com/drive/folders/quartz-id",
            "access": "private",
            "state": "public-verified",
            "products": {},
        }
    }
    with pytest.raises(ValueError, match="public-link"):
        load_mirror_ledger(
            _write_yaml(
                tmp_path / "private-public-phase.yml",
                _mirror_mapping(phases=phases),
            )
        )


def _write_product_package(product_root: Path) -> dict[str, bytes]:
    payloads = {
        "media/demo.mov": b"authoritative-mov",
        "previews/preview.png": b"preview",
        "web/demo.mp4": b"browser-mp4",
        "provenance/manifest.json": b'{"source":"fixture"}\n',
        "provenance/scientific-fields/field.npz": b"scientific-field",
    }
    for relative, content in payloads.items():
        path = product_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = {
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
            for relative, content in payloads.items()
        ],
    }
    _write_yaml(product_root / "product-package.yml", manifest)
    return payloads


@pytest.fixture
def canonical_phase(tmp_path: Path) -> Path:
    phase = tmp_path / "canonical/demo"
    product_root = phase / "products/demo-movie"
    _write_product_package(product_root)
    package_identity = load_product_package(
        product_root / "product-package.yml"
    ).package_sha256
    _write_yaml(
        phase / "phase-package.yml",
        {
            "schema_version": 1,
            "phase_slug": "demo",
            "source_record": "phases/demo/source.yml",
            "products": [
                {
                    "product_id": "demo-movie",
                    "manifest": "products/demo-movie/product-package.yml",
                    "manifest_sha256": package_identity,
                }
            ],
        },
    )
    return phase


@pytest.fixture
def downloaded_phase(canonical_phase: Path, tmp_path: Path) -> Path:
    downloaded = tmp_path / "downloaded/demo"
    for source in canonical_phase.rglob("*"):
        if source.is_file():
            destination = downloaded / source.relative_to(canonical_phase)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
    return downloaded


def test_downloaded_phase_reconciles_every_package_file(
    canonical_phase: Path, downloaded_phase: Path
) -> None:
    result = reconcile_downloaded_phase(
        canonical_phase_root=canonical_phase,
        downloaded_phase_root=downloaded_phase,
    )
    assert result.expected_files == result.verified_files
    assert result.expected_files == 7
    assert result.missing == ()
    assert result.mismatched == ()
    assert result.unexpected == ()


def test_downloaded_phase_reports_missing_mismatch_and_extra(
    canonical_phase: Path, downloaded_phase: Path
) -> None:
    (downloaded_phase / "products/demo-movie/web/demo.mp4").unlink()
    (downloaded_phase / "products/demo-movie/media/demo.mov").write_bytes(b"changed")
    (downloaded_phase / "unmanifested.txt").write_text("extra", encoding="utf-8")

    result = reconcile_downloaded_phase(canonical_phase, downloaded_phase)

    assert result.missing == ("products/demo-movie/web/demo.mp4",)
    assert result.mismatched == ("products/demo-movie/media/demo.mov",)
    assert result.unexpected == ("unmanifested.txt",)
    assert result.verified_files < result.expected_files


def test_downloaded_phase_rejects_symlinks(
    canonical_phase: Path, downloaded_phase: Path
) -> None:
    target = downloaded_phase / "products/demo-movie/media/demo.mov"
    target.unlink()
    target.symlink_to(canonical_phase / "products/demo-movie/media/demo.mov")

    with pytest.raises(ValueError, match="symlink"):
        reconcile_downloaded_phase(canonical_phase, downloaded_phase)


def test_google_site_source_has_landing_about_and_twelve_phase_pages(
    tmp_path: Path,
) -> None:
    mirror = tmp_path / "GOOGLE_MIRROR.yml"
    initialize_mirror_ledger(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        output_path=mirror,
    )
    result = build_google_site_source(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        mirror_registry_path=mirror,
        output_root=tmp_path / "site",
    )

    assert len(result.phase_pages) == 12
    assert "125 products" in result.index_path.read_text(encoding="utf-8")
    assert "not acquired EBSD patterns" in result.about_path.read_text(encoding="utf-8")
    inventory = json.loads(result.inventory_path.read_text(encoding="utf-8"))
    assert inventory["phase_count"] == 12
    assert inventory["product_count"] == 125
    assert inventory["mirror"]["root_state"] == "planned"
    assert "public-verified" not in inventory["mirror"]["product_urls"]
    generated_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (result.index_path, result.about_path, *result.phase_pages)
    )
    assert "https://drive.google.com/drive/folders/" not in generated_text
    assert "public access has not been verified" in generated_text

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from kikuchi_lab.atlas import (
    build_google_site_source,
    initialize_mirror_ledger,
    load_mirror_ledger,
    load_phase_package,
    load_product_package,
    public_product_urls,
    reconcile_downloaded_phase,
)


ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "docs/atlas/PHASE_REGISTRY.yml"
PRODUCTS = ROOT / "docs/atlas/PRODUCT_REGISTRY.yml"
MIRROR_SCRIPT = ROOT / "scripts/atlas_google_mirror.py"
CANONICAL_UPLOAD_BYTES = 7_206_478_751
CANONICAL_UPLOAD_BYTES_BASIS = "exact-regular-file-sum"


def _write_yaml(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _run_mirror_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MIRROR_SCRIPT), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


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


def _complete_remote_inventory(ledger: object) -> dict[str, object]:
    phases = ledger.phases  # type: ignore[attr-defined]
    return {
        "account": "zmichels@umn.edu",
        "root": {
            "drive_id": "exact-root-id",
            "url": "https://drive.google.com/drive/folders/exact-root-id",
        },
        "phases": {
            slug: {
                "drive_id": f"phase-{phase_index}",
                "url": (f"https://drive.google.com/drive/folders/phase-{phase_index}"),
                "products": {
                    product_id: {
                        "drive_id": f"product-{phase_index}-{product_index}",
                        "url": (
                            "https://drive.google.com/drive/folders/"
                            f"product-{phase_index}-{product_index}"
                        ),
                    }
                    for product_index, product_id in enumerate(phase.products)
                },
            }
            for phase_index, (slug, phase) in enumerate(phases.items())
        },
    }


def _recorded_remote_inventory(ledger: object) -> dict[str, object]:
    phases = ledger.phases  # type: ignore[attr-defined]
    return {
        "account": "zmichels@umn.edu",
        "root": {
            "drive_id": ledger.root_drive_id,  # type: ignore[attr-defined]
            "url": ledger.root_url,  # type: ignore[attr-defined]
        },
        "phases": {
            slug: {
                "drive_id": phase.drive_id,
                "url": phase.url,
                "products": {
                    product_id: {
                        "drive_id": product.drive_id,
                        "url": product.url,
                    }
                    for product_id, product in phase.products.items()
                },
            }
            for slug, phase in phases.items()
        },
    }


def _uploaded_private_acceptance() -> dict[str, object]:
    return {
        "upload_observation": {
            "observed_at": None,
            "completed_files": 1212,
            "total_files": 1212,
            "completion_signal": "1 upload complete",
            "failure_signal": "none-observed",
            "canonical_upload_bytes": CANONICAL_UPLOAD_BYTES,
            "canonical_upload_bytes_basis": CANONICAL_UPLOAD_BYTES_BASIS,
        },
        "hierarchy_reconciliation": {
            "root_phases_folder_count": 1,
            "phase_count": 12,
            "product_count": 125,
            "missing_identities": 0,
            "duplicate_drive_ids": 0,
            "duplicate_urls": 0,
        },
        "privacy_verification": {
            "observed_at": None,
            "root_private": True,
            "phases_private": 12,
            "product_folder_samples_private": 12,
            "leaf_file_samples_private": 3,
            "inherited_public_link_removed": True,
            "sample_leaf_files": [
                "calcite/product-package.yml",
                "forsterite/product-package.yml",
                "titanite/product-package.yml",
            ],
        },
        "round_trip_verification": {
            "status": "not-performed",
            "disposition": "waived-by-user",
            "waived_at": "2026-07-26T16:45:00Z",
            "reason": (
                "User accepted observed Drive upload completeness and explicitly "
                "waived round-trip downloads."
            ),
            "downloaded_phase_archives": 0,
            "sha256_compared_files": 0,
        },
    }


def _make_uploaded_private_mirror(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    mirror = tmp_path / "mirror.yml"
    initialize_mirror_ledger(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        output_path=mirror,
    )
    quota = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:30:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )
    assert quota.returncode == 0, quota.stderr
    created = _run_mirror_cli(
        "set-root",
        "--mirror",
        str(mirror),
        "--transport",
        "chrome-folder-upload",
        "--drive-id",
        "exact-root-id",
        "--url",
        "https://drive.google.com/drive/folders/exact-root-id",
        "--access",
        "private",
        "--state",
        "created",
    )
    assert created.returncode == 0, created.stderr
    inventory = _complete_remote_inventory(load_mirror_ledger(mirror))
    recorded = _run_mirror_cli(
        "record-remote-folders",
        "--mirror",
        str(mirror),
        "--inventory-json",
        json.dumps(inventory, separators=(",", ":")),
    )
    assert recorded.returncode == 0, recorded.stderr
    acceptance = _uploaded_private_acceptance()
    accepted = _run_mirror_cli(
        "record-uploaded-private",
        "--mirror",
        str(mirror),
        "--acceptance-json",
        json.dumps(acceptance, separators=(",", ":")),
    )
    assert accepted.returncode == 0, accepted.stderr
    return mirror, acceptance


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
        _mirror_mapping(local_mount="/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu"),
    )
    with pytest.raises(ValueError, match="mich0201"):
        load_mirror_ledger(wrong_mount)


def test_initialize_refuses_to_overwrite_an_existing_ledger(tmp_path: Path) -> None:
    mirror = tmp_path / "mirror.yml"
    initialize_mirror_ledger(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        output_path=mirror,
    )
    before = mirror.read_bytes()

    with pytest.raises(ValueError, match="refuses an existing output"):
        initialize_mirror_ledger(
            registry_path=REGISTRY,
            product_registry_path=PRODUCTS,
            output_path=mirror,
        )

    assert mirror.read_bytes() == before
    assert not tuple(tmp_path.glob(".mirror.yml.*.partial"))


def test_initialize_refuses_symlink_output_and_parent_escape(tmp_path: Path) -> None:
    target = _write_yaml(tmp_path / "target.yml", {"sentinel": "preserve"})
    before = target.read_bytes()
    output_link = tmp_path / "linked-output.yml"
    output_link.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        initialize_mirror_ledger(
            registry_path=REGISTRY,
            product_registry_path=PRODUCTS,
            output_path=output_link,
        )

    assert target.read_bytes() == before
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(ValueError, match="parent.*symlink"):
        initialize_mirror_ledger(
            registry_path=REGISTRY,
            product_registry_path=PRODUCTS,
            output_path=linked_parent / "mirror.yml",
        )

    assert not (real_parent / "mirror.yml").exists()


def test_initialize_refuses_hardlink_and_nonregular_output(tmp_path: Path) -> None:
    hardlink_source = tmp_path / "hardlink-source.yml"
    hardlink_source.write_bytes(b"preserve-hardlink")
    hardlink_output = tmp_path / "hardlink-output.yml"
    os.link(hardlink_source, hardlink_output)

    with pytest.raises(ValueError, match="refuses an existing output"):
        initialize_mirror_ledger(
            registry_path=REGISTRY,
            product_registry_path=PRODUCTS,
            output_path=hardlink_output,
        )

    assert hardlink_source.read_bytes() == b"preserve-hardlink"
    nonregular_output = tmp_path / "directory-output"
    nonregular_output.mkdir()

    with pytest.raises(ValueError, match="refuses an existing output"):
        initialize_mirror_ledger(
            registry_path=REGISTRY,
            product_registry_path=PRODUCTS,
            output_path=nonregular_output,
        )


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
    ledger = load_mirror_ledger(_write_yaml(tmp_path / "valid.yml", _mirror_mapping(phases=phases)))
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


def test_cli_set_root_records_only_the_exact_private_identity(tmp_path: Path) -> None:
    mirror = _write_yaml(tmp_path / "mirror.yml", _mirror_mapping())
    command = (
        "set-root",
        "--mirror",
        str(mirror),
        "--transport",
        "chrome-folder-upload",
        "--drive-id",
        "exact-root-id",
        "--url",
        "https://drive.google.com/drive/folders/exact-root-id",
        "--access",
        "private",
        "--state",
        "created",
    )

    first = _run_mirror_cli(*command)

    assert first.returncode == 0, first.stderr
    first_bytes = mirror.read_bytes()
    ledger = load_mirror_ledger(mirror)
    assert ledger.transport == "chrome-folder-upload"
    assert ledger.root_drive_id == "exact-root-id"
    assert ledger.root_url == "https://drive.google.com/drive/folders/exact-root-id"
    assert ledger.root_access == "private"
    assert ledger.root_state == "created"

    second = _run_mirror_cli(*command)
    assert second.returncode == 0, second.stderr
    assert mirror.read_bytes() == first_bytes

    collision = _run_mirror_cli(
        "set-root",
        "--mirror",
        str(mirror),
        "--transport",
        "chrome-folder-upload",
        "--drive-id",
        "different-root-id",
        "--url",
        "https://drive.google.com/drive/folders/different-root-id",
        "--access",
        "private",
        "--state",
        "created",
    )
    assert collision.returncode != 0
    assert "refuses to replace" in collision.stderr
    assert mirror.read_bytes() == first_bytes


def test_cli_record_remote_folders_requires_the_complete_private_inventory(
    tmp_path: Path,
) -> None:
    mirror = tmp_path / "mirror.yml"
    initialize_mirror_ledger(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        output_path=mirror,
    )
    set_root = _run_mirror_cli(
        "set-root",
        "--mirror",
        str(mirror),
        "--transport",
        "chrome-folder-upload",
        "--drive-id",
        "exact-root-id",
        "--url",
        "https://drive.google.com/drive/folders/exact-root-id",
        "--access",
        "private",
        "--state",
        "created",
    )
    assert set_root.returncode == 0, set_root.stderr
    ledger = load_mirror_ledger(mirror)
    inventory = _complete_remote_inventory(ledger)

    recorded = _run_mirror_cli(
        "record-remote-folders",
        "--mirror",
        str(mirror),
        "--inventory-json",
        json.dumps(inventory, separators=(",", ":")),
    )

    assert recorded.returncode == 0, recorded.stderr
    updated = load_mirror_ledger(mirror)
    assert updated.root_state == "uploaded"
    assert all(phase.state == "uploaded" for phase in updated.phases.values())
    assert all(
        product.state == "uploaded"
        and product.drive_id is not None
        and product.url is not None
        and product.access == "private"
        for phase in updated.phases.values()
        for product in phase.products.values()
    )

    incomplete = json.loads(json.dumps(inventory))
    incomplete["phases"].pop(next(iter(incomplete["phases"])))
    before = mirror.read_bytes()
    rejected = _run_mirror_cli(
        "record-remote-folders",
        "--mirror",
        str(mirror),
        "--inventory-json",
        json.dumps(incomplete, separators=(",", ":")),
    )
    assert rejected.returncode != 0
    assert "phase inventory differs" in rejected.stderr
    assert mirror.read_bytes() == before


def test_cli_records_uploaded_private_waiver_without_hash_overclaim(
    tmp_path: Path,
) -> None:
    mirror = tmp_path / "mirror.yml"
    initialize_mirror_ledger(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        output_path=mirror,
    )
    quota = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:30:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )
    assert quota.returncode == 0, quota.stderr
    created = _run_mirror_cli(
        "set-root",
        "--mirror",
        str(mirror),
        "--transport",
        "chrome-folder-upload",
        "--drive-id",
        "exact-root-id",
        "--url",
        "https://drive.google.com/drive/folders/exact-root-id",
        "--access",
        "private",
        "--state",
        "created",
    )
    assert created.returncode == 0, created.stderr
    inventory = _complete_remote_inventory(load_mirror_ledger(mirror))
    recorded = _run_mirror_cli(
        "record-remote-folders",
        "--mirror",
        str(mirror),
        "--inventory-json",
        json.dumps(inventory, separators=(",", ":")),
    )
    assert recorded.returncode == 0, recorded.stderr
    acceptance = _uploaded_private_acceptance()

    accepted = _run_mirror_cli(
        "record-uploaded-private",
        "--mirror",
        str(mirror),
        "--acceptance-json",
        json.dumps(acceptance, separators=(",", ":")),
    )

    assert accepted.returncode == 0, accepted.stderr
    assert (
        "upload accepted state=uploaded-private phases=12 products=125 "
        "round-trip=not-performed disposition=waived-by-user"
    ) in accepted.stdout
    ledger = load_mirror_ledger(mirror)
    assert ledger.root_state == "uploaded-private"
    assert ledger.root_access == "private"
    assert ledger.upload_acceptance == acceptance
    assert all(
        phase.state == "uploaded" and phase.access == "private" for phase in ledger.phases.values()
    )
    assert all(
        product.state == "uploaded"
        and product.access == "private"
        and product.package_manifest_sha256 is None
        and product.verified_at is None
        for phase in ledger.phases.values()
        for product in phase.products.values()
    )
    assert public_product_urls(ledger) == {}

    validated = _run_mirror_cli(
        "validate",
        "--mirror",
        str(mirror),
        "--require-state",
        "uploaded-private",
    )
    assert validated.returncode == 0, validated.stderr
    assert (
        "mirror valid state=uploaded-private phases=12 products=125 "
        "verified-private=0 round-trip=not-performed "
        "disposition=waived-by-user"
    ) in validated.stdout

    local_copy = tmp_path / "local/atlas/atlas-mirror.yml"
    exported = _run_mirror_cli(
        "export-local",
        "--mirror",
        str(mirror),
        "--output",
        str(local_copy),
        "--require-state",
        "uploaded-private",
    )
    assert exported.returncode == 0, exported.stderr
    assert local_copy.read_bytes() == mirror.read_bytes()

    invalid_acceptance = json.loads(json.dumps(acceptance))
    invalid_acceptance["privacy_verification"]["phases_private"] = 11
    before = mirror.read_bytes()
    rejected = _run_mirror_cli(
        "record-uploaded-private",
        "--mirror",
        str(mirror),
        "--acceptance-json",
        json.dumps(invalid_acceptance, separators=(",", ":")),
    )
    assert rejected.returncode != 0
    assert "12 private phase folders" in rejected.stderr
    assert mirror.read_bytes() == before


@pytest.mark.parametrize(
    ("tamper", "message"),
    (
        ("duplicate-drive-id", "Drive IDs must be globally unique"),
        ("duplicate-drive-url", "Drive URLs must be globally unique"),
        ("mismatched-url-token", "URL token must match"),
        ("bad-quota-timestamp", "quota observed_at must be ISO-8601 UTC"),
        ("incoherent-quota", "total_bytes must equal used_bytes plus free_bytes"),
        ("failed-headroom", "quota headroom gate failed"),
        ("wrong-registry-product", "registry set"),
        ("canonical-byte-mismatch", "canonical upload bytes differ"),
    ),
)
def test_uploaded_private_loader_recomputes_terminal_invariants(
    tmp_path: Path,
    tamper: str,
    message: str,
) -> None:
    mirror, _ = _make_uploaded_private_mirror(tmp_path)
    raw = yaml.safe_load(mirror.read_text(encoding="utf-8"))
    phase_records = list(raw["phases"].values())
    product_records = [product for phase in phase_records for product in phase["products"].values()]

    if tamper == "duplicate-drive-id":
        product_records[1]["drive_id"] = product_records[0]["drive_id"]
    elif tamper == "duplicate-drive-url":
        product_records[1]["url"] = product_records[0]["url"]
    elif tamper == "mismatched-url-token":
        product_records[0]["url"] = "https://drive.google.com/drive/folders/different-unique-token"
    elif tamper == "bad-quota-timestamp":
        raw["quota"]["observed_at"] = "2026-07-26T08:30:00-07:00"
    elif tamper == "incoherent-quota":
        raw["quota"]["total_bytes"] += 1
    elif tamper == "failed-headroom":
        raw["quota"]["free_bytes"] = (
            raw["quota"]["canonical_upload_bytes"] + raw["quota"]["required_headroom_bytes"] - 1
        )
        raw["quota"]["total_bytes"] = raw["quota"]["used_bytes"] + raw["quota"]["free_bytes"]
    elif tamper == "wrong-registry-product":
        first_phase = phase_records[0]
        product_id, product = first_phase["products"].popitem()
        first_phase["products"][f"{product_id}-tampered"] = product
    elif tamper == "canonical-byte-mismatch":
        raw["upload_acceptance"]["upload_observation"]["canonical_upload_bytes"] += 1
    else:  # pragma: no cover - parameter list is exhaustive
        raise AssertionError(tamper)

    _write_yaml(mirror, raw)

    with pytest.raises(ValueError, match=message):
        load_mirror_ledger(mirror)

    validated = _run_mirror_cli(
        "validate",
        "--mirror",
        str(mirror),
        "--require-state",
        "uploaded-private",
    )
    assert validated.returncode != 0
    assert message.replace("\\", "")[:20] in validated.stderr


def test_uploaded_private_acceptance_is_terminal_and_collision_safe(
    tmp_path: Path,
) -> None:
    mirror, acceptance = _make_uploaded_private_mirror(tmp_path)
    before = mirror.read_bytes()
    identical = _run_mirror_cli(
        "record-uploaded-private",
        "--mirror",
        str(mirror),
        "--acceptance-json",
        json.dumps(acceptance, separators=(",", ":")),
    )
    assert identical.returncode == 0, identical.stderr
    assert mirror.read_bytes() == before

    changed_acceptance = json.loads(json.dumps(acceptance))
    changed_acceptance["round_trip_verification"]["reason"] = (
        "A different but otherwise valid waiver reason."
    )
    collision = _run_mirror_cli(
        "record-uploaded-private",
        "--mirror",
        str(mirror),
        "--acceptance-json",
        json.dumps(changed_acceptance, separators=(",", ":")),
    )
    assert collision.returncode != 0
    assert "refuses to replace terminal acceptance" in collision.stderr
    assert mirror.read_bytes() == before


def test_uploaded_private_promotion_validates_before_atomic_write(
    tmp_path: Path,
) -> None:
    mirror, acceptance = _make_uploaded_private_mirror(tmp_path)
    raw = yaml.safe_load(mirror.read_text(encoding="utf-8"))
    raw["root"]["state"] = "uploaded"
    raw["upload_acceptance"] = None
    first_phase = next(iter(raw["phases"].values()))
    first_product = next(iter(first_phase["products"].values()))
    first_product["url"] = "https://drive.google.com/drive/folders/different-unique-token"
    _write_yaml(mirror, raw)
    before = mirror.read_bytes()

    rejected = _run_mirror_cli(
        "record-uploaded-private",
        "--mirror",
        str(mirror),
        "--acceptance-json",
        json.dumps(acceptance, separators=(",", ":")),
    )

    assert rejected.returncode != 0
    assert "URL token must match" in rejected.stderr
    assert mirror.read_bytes() == before
    assert not tuple(tmp_path.glob(".mirror.yml.*.partial"))
    assert not tuple(tmp_path.glob(".mirror.yml.*.validate"))


def test_terminal_uploaded_private_quota_is_immutable(tmp_path: Path) -> None:
    mirror, _ = _make_uploaded_private_mirror(tmp_path)
    before = mirror.read_bytes()
    exact = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:30:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )
    assert exact.returncode == 0, exact.stderr
    assert mirror.read_bytes() == before

    changed = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:31:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )
    assert changed.returncode != 0
    assert "refuses to replace terminal quota" in changed.stderr
    assert mirror.read_bytes() == before


@pytest.mark.parametrize("terminal_state", ("complete", "public-verified"))
def test_other_terminal_quota_states_are_immutable(
    tmp_path: Path,
    terminal_state: str,
) -> None:
    mirror, _ = _make_uploaded_private_mirror(tmp_path)
    raw = yaml.safe_load(mirror.read_text(encoding="utf-8"))
    raw["root"]["state"] = terminal_state
    if terminal_state == "public-verified":
        raw["root"]["access"] = "public-link"
    _write_yaml(mirror, raw)
    before = mirror.read_bytes()

    changed = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:31:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )

    assert changed.returncode != 0
    assert "refuses to replace terminal quota" in changed.stderr
    assert mirror.read_bytes() == before


def test_other_identity_transitions_refuse_uploaded_private_regression(
    tmp_path: Path,
) -> None:
    mirror, _ = _make_uploaded_private_mirror(tmp_path)
    ledger = load_mirror_ledger(mirror)
    before = mirror.read_bytes()

    set_root = _run_mirror_cli(
        "set-root",
        "--mirror",
        str(mirror),
        "--transport",
        "chrome-folder-upload",
        "--drive-id",
        str(ledger.root_drive_id),
        "--url",
        str(ledger.root_url),
        "--access",
        "private",
        "--state",
        "created",
    )
    assert set_root.returncode != 0
    assert "progressed root state" in set_root.stderr

    remote_folders = _run_mirror_cli(
        "record-remote-folders",
        "--mirror",
        str(mirror),
        "--inventory-json",
        json.dumps(_recorded_remote_inventory(ledger), separators=(",", ":")),
    )
    assert remote_folders.returncode != 0
    assert "created or uploaded root" in remote_folders.stderr

    reconcile = _run_mirror_cli(
        "reconcile-downloaded",
        "--canonical-root",
        str(tmp_path / "canonical-not-read"),
        "--download-root",
        str(tmp_path / "download-not-read"),
        "--mirror",
        str(mirror),
    )
    assert reconcile.returncode != 0
    assert "requires an uploaded mirror root" in reconcile.stderr
    assert mirror.read_bytes() == before


def test_cli_record_quota_enforces_the_headroom_gate(tmp_path: Path) -> None:
    mirror = _write_yaml(tmp_path / "mirror.yml", _mirror_mapping())
    command = (
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:30:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )

    recorded = _run_mirror_cli(*command)

    assert recorded.returncode == 0, recorded.stderr
    ledger = load_mirror_ledger(mirror)
    assert dict(ledger.quota) == {
        "observed_at": "2026-07-26T08:30:00Z",
        "total_bytes": 100000000000,
        "used_bytes": 7820000000,
        "free_bytes": 92180000000,
        "required_headroom_bytes": 10737418240,
        "canonical_upload_bytes": CANONICAL_UPLOAD_BYTES,
        "canonical_upload_bytes_basis": CANONICAL_UPLOAD_BYTES_BASIS,
    }

    before = mirror.read_bytes()
    blocked = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:31:00Z",
        "--total-bytes",
        "20000000000",
        "--used-bytes",
        "10000000000",
        "--free-bytes",
        "10000000000",
        "--canonical-bytes",
        str(CANONICAL_UPLOAD_BYTES),
    )
    assert blocked.returncode != 0
    assert "headroom gate" in blocked.stderr
    assert mirror.read_bytes() == before


def test_cli_reconcile_downloaded_requires_all_exact_package_bytes(
    tmp_path: Path,
) -> None:
    mirror = tmp_path / "mirror.yml"
    initialize_mirror_ledger(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        output_path=mirror,
    )
    quota = _run_mirror_cli(
        "record-quota",
        "--mirror",
        str(mirror),
        "--observed-at",
        "2026-07-26T08:30:00Z",
        "--total-bytes",
        "100000000000",
        "--used-bytes",
        "7820000000",
        "--free-bytes",
        "92180000000",
        "--canonical-bytes",
        "100",
    )
    assert quota.returncode == 0, quota.stderr
    assert (
        _run_mirror_cli(
            "set-root",
            "--mirror",
            str(mirror),
            "--transport",
            "chrome-folder-upload",
            "--drive-id",
            "exact-root-id",
            "--url",
            "https://drive.google.com/drive/folders/exact-root-id",
            "--access",
            "private",
            "--state",
            "created",
        ).returncode
        == 0
    )
    inventory = _complete_remote_inventory(load_mirror_ledger(mirror))
    recorded = _run_mirror_cli(
        "record-remote-folders",
        "--mirror",
        str(mirror),
        "--inventory-json",
        json.dumps(inventory, separators=(",", ":")),
    )
    assert recorded.returncode == 0, recorded.stderr
    canonical = tmp_path / "canonical"
    downloaded = tmp_path / "downloaded"
    _write_full_mirror_fixture_packages(canonical, mirror)
    shutil.copytree(canonical, downloaded)
    ledger = load_mirror_ledger(mirror)
    first_slug = next(iter(ledger.phases))
    first_product = next(iter(ledger.phases[first_slug].products))
    changed = downloaded / first_slug / "products" / first_product / "media/payload.bin"
    changed.write_bytes(b"not-the-canonical-bytes")
    before = mirror.read_bytes()

    rejected = _run_mirror_cli(
        "reconcile-downloaded",
        "--canonical-root",
        str(canonical),
        "--download-root",
        str(downloaded),
        "--mirror",
        str(mirror),
    )

    assert rejected.returncode != 0
    assert "mismatched=1" in rejected.stderr
    assert mirror.read_bytes() == before
    shutil.copy2(
        canonical / first_slug / "products" / first_product / "media/payload.bin",
        changed,
    )

    reconciled = _run_mirror_cli(
        "reconcile-downloaded",
        "--canonical-root",
        str(canonical),
        "--download-root",
        str(downloaded),
        "--mirror",
        str(mirror),
    )

    assert reconciled.returncode == 0, reconciled.stderr
    assert "reconciled phases=12 products=125 missing=0 mismatched=0" in reconciled.stdout
    verified = load_mirror_ledger(mirror)
    assert verified.root_state == "complete-private"
    assert all(
        phase.state == "verified-private"
        and phase.access == "private"
        and phase.drive_id is not None
        and phase.url is not None
        for phase in verified.phases.values()
    )
    for slug, phase in verified.phases.items():
        phase_package = load_phase_package(canonical / slug / "phase-package.yml")
        for product_id, product in phase.products.items():
            assert product.state == "verified-private"
            assert product.access == "private"
            assert (
                product.package_manifest_sha256
                == phase_package.manifest_sha256_by_product[product_id]
            )
            assert product.verified_at is not None

    validated = _run_mirror_cli(
        "validate",
        "--mirror",
        str(mirror),
        "--require-state",
        "complete-private",
    )
    assert validated.returncode == 0, validated.stderr
    assert (
        "mirror valid state=complete-private phases=12 products=125 verified-private=125"
    ) in validated.stdout

    local_copy = tmp_path / "local/atlas/atlas-mirror.yml"
    exported = _run_mirror_cli(
        "export-local",
        "--mirror",
        str(mirror),
        "--output",
        str(local_copy),
        "--require-state",
        "complete-private",
    )
    assert exported.returncode == 0, exported.stderr
    assert local_copy.read_bytes() == mirror.read_bytes()


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
    ledger = load_mirror_ledger(_write_yaml(tmp_path / "mixed.yml", _mirror_mapping(phases=phases)))
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
        load_mirror_ledger(_write_yaml(tmp_path / "duplicate.yml", _mirror_mapping(phases=phases)))


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
        load_mirror_ledger(_write_yaml(tmp_path / "unbound.yml", _mirror_mapping(phases=phases)))


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
                    "preview" if relative.startswith("previews/") else relative.split("/", 1)[0]
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


def _write_full_mirror_fixture_packages(
    canonical_root: Path,
    mirror_path: Path,
) -> None:
    ledger = load_mirror_ledger(mirror_path)
    for slug, phase in ledger.phases.items():
        phase_root = canonical_root / slug
        phase_products = []
        for product_id in phase.products:
            product_root = phase_root / "products" / product_id
            for directory in ("media", "previews", "web", "provenance"):
                (product_root / directory).mkdir(parents=True, exist_ok=True)
            payload = f"{slug}/{product_id}\n".encode()
            payload_path = product_root / "media/payload.bin"
            payload_path.write_bytes(payload)
            manifest_path = _write_yaml(
                product_root / "product-package.yml",
                {
                    "schema_version": 1,
                    "phase_slug": slug,
                    "product_id": product_id,
                    "registry_id": product_id,
                    "source_commit": "1" * 40,
                    "tracked_references": {"recipe": f"recipes/{product_id}.yml"},
                    "files": [
                        {
                            "path": "media/payload.bin",
                            "role": "media",
                            "bytes": len(payload),
                            "sha256": hashlib.sha256(payload).hexdigest(),
                            "mime_type": "application/octet-stream",
                            "destinations": ["google-drive"],
                        }
                    ],
                },
            )
            phase_products.append(
                {
                    "product_id": product_id,
                    "manifest": f"products/{product_id}/product-package.yml",
                    "manifest_sha256": load_product_package(manifest_path).package_sha256,
                }
            )
        _write_yaml(
            phase_root / "phase-package.yml",
            {
                "schema_version": 1,
                "phase_slug": slug,
                "source_record": f"phases/{slug}/source.yml",
                "products": phase_products,
            },
        )


@pytest.fixture
def canonical_phase(tmp_path: Path) -> Path:
    phase = tmp_path / "canonical/demo"
    product_root = phase / "products/demo-movie"
    _write_product_package(product_root)
    package_identity = load_product_package(product_root / "product-package.yml").package_sha256
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


def test_downloaded_phase_rejects_symlinks(canonical_phase: Path, downloaded_phase: Path) -> None:
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

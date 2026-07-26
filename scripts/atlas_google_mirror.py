#!/usr/bin/env python3
"""Initialize and inspect local source contracts for the Atlas Google mirror."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kikuchi_lab.atlas import (
    build_google_site_source,
    export_local_mirror,
    initialize_mirror_ledger,
    record_mirror_quota,
    record_remote_folders,
    record_site_draft,
    record_uploaded_private_acceptance,
    reconcile_downloaded_mirror,
    set_mirror_root,
    validate_mirror_ledger,
)


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser(
        "initialize",
        help="Write the planned private 12-phase/125-product mirror skeleton.",
    )
    initialize.add_argument(
        "--phases",
        type=Path,
        default=ROOT / "docs/atlas/PHASE_REGISTRY.yml",
    )
    initialize.add_argument(
        "--products",
        type=Path,
        default=ROOT / "docs/atlas/PRODUCT_REGISTRY.yml",
    )
    initialize.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/atlas/GOOGLE_MIRROR.yml",
    )

    site = commands.add_parser(
        "build-site-source",
        help="Generate reviewable local Markdown for a later Google Site.",
    )
    site.add_argument(
        "--phases",
        type=Path,
        default=ROOT / "docs/atlas/PHASE_REGISTRY.yml",
    )
    site.add_argument(
        "--products",
        type=Path,
        default=ROOT / "docs/atlas/PRODUCT_REGISTRY.yml",
    )
    site.add_argument(
        "--mirror",
        type=Path,
        default=ROOT / "docs/atlas/GOOGLE_MIRROR.yml",
    )
    site.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist/google-site",
    )
    site.add_argument(
        "--allow-private-links",
        action="store_true",
        help="Include exact restricted phase-folder links for signed-in draft review.",
    )

    set_root = commands.add_parser(
        "set-root",
        help="Bind the ledger to one exact, still-private Drive root.",
    )
    set_root.add_argument("--mirror", type=Path, required=True)
    set_root.add_argument(
        "--transport",
        choices=("drive-for-desktop", "chrome-folder-upload"),
        required=True,
    )
    set_root.add_argument("--drive-id", required=True)
    set_root.add_argument("--url", required=True)
    set_root.add_argument("--access", choices=("private",), required=True)
    set_root.add_argument("--state", choices=("created",), required=True)

    remote_folders = commands.add_parser(
        "record-remote-folders",
        help="Record one complete private phase/product folder inventory.",
    )
    remote_folders.add_argument("--mirror", type=Path, required=True)
    remote_folders.add_argument("--inventory-json", required=True)

    uploaded_private = commands.add_parser(
        "record-uploaded-private",
        help=(
            "Record private upload acceptance with explicit user-waived round-trip verification."
        ),
    )
    uploaded_private.add_argument("--mirror", type=Path, required=True)
    uploaded_private.add_argument("--acceptance-json", required=True)

    site_draft = commands.add_parser(
        "record-site-draft",
        help="Record one complete, university-only, still-unpublished Site draft.",
    )
    site_draft.add_argument("--mirror", type=Path, required=True)
    site_draft.add_argument("--editor-url", required=True)
    site_draft.add_argument("--proposed-public-url", required=True)
    site_draft.add_argument("--audience", choices=("university-only",), required=True)
    site_draft.add_argument("--state", choices=("draft-complete",), required=True)

    quota = commands.add_parser(
        "record-quota",
        help="Record a live quota observation after enforcing the headroom gate.",
    )
    quota.add_argument("--mirror", type=Path, required=True)
    quota.add_argument("--observed-at", required=True)
    quota.add_argument("--total-bytes", type=int, required=True)
    quota.add_argument("--used-bytes", type=int, required=True)
    quota.add_argument("--free-bytes", type=int, required=True)
    quota.add_argument("--canonical-bytes", type=int, required=True)

    reconcile = commands.add_parser(
        "reconcile-downloaded",
        help="Reconcile all downloaded phases and promote verified-private state.",
    )
    reconcile.add_argument("--canonical-root", type=Path, required=True)
    reconcile.add_argument("--download-root", type=Path, required=True)
    reconcile.add_argument("--mirror", type=Path, required=True)

    validate = commands.add_parser(
        "validate",
        help="Validate an exact required mirror state without changing it.",
    )
    validate.add_argument("--mirror", type=Path, required=True)
    validate.add_argument("--require-state", required=True)

    export = commands.add_parser(
        "export-local",
        help="Write an exact validated ledger copy for last-file upload.",
    )
    export.add_argument("--mirror", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--require-state", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "initialize":
        ledger = initialize_mirror_ledger(
            registry_path=args.phases,
            product_registry_path=args.products,
            output_path=args.output,
        )
        print(
            f"mirror initialized state={ledger.root_state} "
            f"phases={ledger.phase_count} products={ledger.product_count} "
            f"output={ledger.path}"
        )
        return

    if args.command == "set-root":
        ledger = set_mirror_root(
            mirror_path=args.mirror,
            transport=args.transport,
            drive_id=args.drive_id,
            url=args.url,
            access=args.access,
            state=args.state,
        )
        print(
            f"mirror root state={ledger.root_state} access={ledger.root_access} "
            f"transport={ledger.transport} drive_id={ledger.root_drive_id} "
            f"url={ledger.root_url}"
        )
        return

    if args.command == "record-remote-folders":
        ledger = record_remote_folders(
            mirror_path=args.mirror,
            inventory=json.loads(args.inventory_json),
        )
        print(
            f"remote folders recorded state={ledger.root_state} "
            f"phases={ledger.phase_count} products={ledger.product_count}"
        )
        return

    if args.command == "record-quota":
        ledger = record_mirror_quota(
            mirror_path=args.mirror,
            observed_at=args.observed_at,
            total_bytes=args.total_bytes,
            used_bytes=args.used_bytes,
            free_bytes=args.free_bytes,
            canonical_bytes=args.canonical_bytes,
        )
        print(
            f"quota recorded observed_at={ledger.quota['observed_at']} "
            f"total={ledger.quota['total_bytes']} "
            f"used={ledger.quota['used_bytes']} "
            f"free={ledger.quota['free_bytes']}"
        )
        return

    if args.command == "record-uploaded-private":
        ledger = record_uploaded_private_acceptance(
            mirror_path=args.mirror,
            acceptance=json.loads(args.acceptance_json),
        )
        acceptance = ledger.upload_acceptance
        if acceptance is None:
            raise ValueError("uploaded-private acceptance was not recorded")
        round_trip = acceptance["round_trip_verification"]
        print(
            f"upload accepted state={ledger.root_state} "
            f"phases={ledger.phase_count} products={ledger.product_count} "
            f"round-trip={round_trip['status']} "
            f"disposition={round_trip['disposition']}"
        )
        return

    if args.command == "record-site-draft":
        ledger = record_site_draft(
            mirror_path=args.mirror,
            editor_url=args.editor_url,
            proposed_public_url=args.proposed_public_url,
            audience=args.audience,
            state=args.state,
        )
        print(
            f"site draft recorded state={ledger.site_state} "
            f"audience={ledger.site_audience} "
            f"editor={ledger.site_draft_url} "
            f"proposed={ledger.site_public_url}"
        )
        return

    if args.command == "reconcile-downloaded":
        result = reconcile_downloaded_mirror(
            canonical_root=args.canonical_root,
            download_root=args.download_root,
            mirror_path=args.mirror,
        )
        print(
            f"reconciled phases={result.phase_count} "
            f"products={result.product_count} "
            f"missing={result.missing} mismatched={result.mismatched}"
        )
        return

    if args.command == "validate":
        result = validate_mirror_ledger(
            mirror_path=args.mirror,
            require_state=args.require_state,
        )
        acceptance_suffix = ""
        if result.ledger.upload_acceptance is not None:
            round_trip = result.ledger.upload_acceptance["round_trip_verification"]
            acceptance_suffix = (
                f" round-trip={round_trip['status']} disposition={round_trip['disposition']}"
            )
        print(
            f"mirror valid state={result.ledger.root_state} "
            f"phases={result.ledger.phase_count} "
            f"products={result.ledger.product_count} "
            f"verified-private={result.verified_private_products}"
            f"{acceptance_suffix}"
        )
        return

    if args.command == "export-local":
        output = export_local_mirror(
            mirror_path=args.mirror,
            output_path=args.output,
            require_state=args.require_state,
        )
        print(f"local mirror exported output={output}")
        return

    result = build_google_site_source(
        registry_path=args.phases,
        product_registry_path=args.products,
        mirror_registry_path=args.mirror,
        output_root=args.output,
        allow_private_links=args.allow_private_links,
    )
    print(
        f"Google Site source built phases={len(result.phase_pages)} "
        f"index={result.index_path} about={result.about_path} "
        f"inventory={result.inventory_path}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Initialize and inspect local source contracts for the Atlas Google mirror."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas import build_google_site_source, initialize_mirror_ledger


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

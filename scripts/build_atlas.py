#!/usr/bin/env python3
"""Build the local static Kikuchi Atlas from tracked registry data."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas import build_atlas, load_mirror_ledger, public_product_urls


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "docs/atlas/PHASE_REGISTRY.yml")
    parser.add_argument(
        "--product-registry", type=Path, default=ROOT / "docs/atlas/PRODUCT_REGISTRY.yml"
    )
    parser.add_argument(
        "--anchor-catalog", type=Path, default=ROOT / "docs/products/ARTIFACT_CATALOG.yml"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "docs/atlas/site")
    parser.add_argument(
        "--mirror-registry",
        type=Path,
        help="Optional mirror ledger; only public-verified product URLs are added.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    product_urls = (
        public_product_urls(load_mirror_ledger(args.mirror_registry))
        if args.mirror_registry is not None
        else None
    )
    result = build_atlas(
        registry_path=args.registry,
        product_registry_path=args.product_registry,
        anchor_catalog_path=args.anchor_catalog,
        output_root=args.output,
        product_urls=product_urls,
    )
    print(
        f"atlas built phases={result.phase_count} individual_products={result.product_count} "
        f"index={result.index_path} products={result.products_path}"
    )


if __name__ == "__main__":
    main()

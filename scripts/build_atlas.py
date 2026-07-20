#!/usr/bin/env python3
"""Build the local static Kikuchi Atlas from tracked registry data."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas import build_atlas


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "docs/atlas/PHASE_REGISTRY.yml")
    parser.add_argument("--products", type=Path, default=ROOT / "docs/products/ARTIFACT_CATALOG.yml")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/atlas/site")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_atlas(
        registry_path=args.registry,
        product_catalog_path=args.products,
        output_root=args.output,
    )
    print(
        f"atlas built phases={result.phase_count} product_associations={result.product_count} "
        f"index={result.index_path}"
    )


if __name__ == "__main__":
    main()

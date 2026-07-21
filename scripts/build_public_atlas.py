#!/usr/bin/env python3
"""Build a deployable static Kikuchi Atlas gallery and archival-release staging area."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas import build_public_atlas


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
    parser.add_argument("--output", type=Path, default=ROOT / "dist/atlas-public")
    parser.add_argument(
        "--stage-archive",
        action="store_true",
        help="Copy selected media/provenance files into an archival-release staging directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_public_atlas(
        registry_path=args.registry,
        product_registry_path=args.product_registry,
        anchor_catalog_path=args.anchor_catalog,
        output_root=args.output,
        stage_archive=args.stage_archive,
    )
    print(
        f"public Atlas built site={result.site_root} web_assets={result.web_asset_count} "
        f"web_bytes={result.web_asset_bytes} archive_assets={result.archival_asset_count} "
        f"archive_bytes={result.archival_asset_bytes} inventory={result.inventory_path}"
    )


if __name__ == "__main__":
    main()

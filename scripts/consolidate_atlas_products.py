#!/usr/bin/env python3
"""Plan deterministic Atlas package consolidation without copying artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas.consolidation import (
    build_migration_ledger,
    validate_migration_output_path,
    write_migration_ledger,
)


ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="Write a frozen no-copy migration plan.")
    plan.add_argument("--registry", type=Path, default=ROOT / "docs/atlas/PHASE_REGISTRY.yml")
    plan.add_argument(
        "--products",
        type=Path,
        default=ROOT / "docs/atlas/PRODUCT_REGISTRY.yml",
    )
    plan.add_argument(
        "--catalog",
        type=Path,
        default=ROOT / "docs/products/ARTIFACT_CATALOG.yml",
    )
    plan.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "docs/atlas/CONSOLIDATION.yml",
    )
    plan.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/atlas/ATLAS_MIGRATION.yml",
    )
    plan.add_argument("--source-commit", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        validate_migration_output_path(args.output, args.policy)
        ledger = build_migration_ledger(
            registry_path=args.registry,
            product_registry_path=args.products,
            artifact_catalog_path=args.catalog,
            consolidation_path=args.policy,
            source_commit=args.source_commit,
        )
        write_migration_ledger(ledger, args.output)
        print(f"{ledger.state} phases={ledger.phase_count} products={ledger.product_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

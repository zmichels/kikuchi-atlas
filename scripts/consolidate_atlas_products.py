#!/usr/bin/env python3
"""Plan deterministic Atlas package consolidation without copying artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas.consolidation import (
    audit_legacy_paths,
    build_migration_ledger,
    materialize_ledger,
    rewrite_product_registry,
    validate_migration_output_path,
    verify_canonical_tree,
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
    materialize = subparsers.add_parser(
        "materialize",
        help="Materialize and byte-verify every planned canonical package.",
    )
    materialize.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "docs/atlas/ATLAS_MIGRATION.yml",
    )
    materialize.add_argument("--root", type=Path, default=ROOT)
    verify = subparsers.add_parser(
        "verify",
        help="Verify the complete canonical package tree.",
    )
    verify.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "docs/atlas/ATLAS_MIGRATION.yml",
    )
    verify.add_argument("--root", type=Path, default=ROOT)
    rewrite = subparsers.add_parser(
        "rewrite-registry",
        help="Atomically cut the product registry over to verified canonical packages.",
    )
    rewrite.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "docs/atlas/ATLAS_MIGRATION.yml",
    )
    rewrite.add_argument(
        "--products",
        type=Path,
        default=ROOT / "docs/atlas/PRODUCT_REGISTRY.yml",
    )
    rewrite.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "docs/atlas/CONSOLIDATION.yml",
    )
    rewrite.add_argument("--root", type=Path, default=ROOT)
    audit = subparsers.add_parser(
        "audit-paths",
        help="Classify every tracked current legacy-root reference.",
    )
    audit.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "docs/atlas/ATLAS_MIGRATION.yml",
    )
    audit.add_argument("--root", type=Path, default=ROOT)
    audit.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/atlas/LEGACY_PATH_AUDIT.yml",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        validate_migration_output_path(args.output, args.policy, args.registry)
        ledger = build_migration_ledger(
            registry_path=args.registry,
            product_registry_path=args.products,
            artifact_catalog_path=args.catalog,
            consolidation_path=args.policy,
            source_commit=args.source_commit,
        )
        write_migration_ledger(ledger, args.output)
        print(f"{ledger.state} phases={ledger.phase_count} products={ledger.product_count}")
    elif args.command == "materialize":
        ledger = materialize_ledger(args.ledger, repository_root=args.root)
        print(
            f"{ledger.state} phases={ledger.phase_count} "
            f"products={ledger.product_count}"
        )
    elif args.command == "verify":
        result = verify_canonical_tree(args.ledger, repository_root=args.root)
        print(
            f"verified phases={result.phase_count} products={result.product_count} "
            f"missing={result.missing_count} mismatched={result.mismatched_count} "
            f"symlinks={result.symlink_count}"
        )
        if not result.valid:
            return 1
    elif args.command == "rewrite-registry":
        result = rewrite_product_registry(
            ledger_path=args.ledger,
            product_registry_path=args.products,
            consolidation_path=args.policy,
            repository_root=args.root,
        )
        print(
            f"registry cutover products={result.product_count} "
            f"available={result.available_count} "
            f"legacy_paths={result.legacy_path_count}"
        )
    elif args.command == "audit-paths":
        result = audit_legacy_paths(
            ledger_path=args.ledger,
            repository_root=args.root,
            output_path=args.output,
        )
        print(
            "publishable legacy references="
            f"{result.publishable_legacy_reference_count} "
            f"allowed={result.allowed_reference_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

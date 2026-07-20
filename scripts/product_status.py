#!/usr/bin/env python3
"""Validate the static local-product catalog and report media availability."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REQUIRED_ENTRY_FIELDS = {
    "id",
    "tier",
    "phase",
    "artifact_path",
    "files",
    "recipe",
    "entrypoint",
    "state",
}


def load_catalog(path: Path) -> list[dict[str, Any]]:
    """Load and validate the intentionally small catalog contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("catalog must be a schema_version 1 mapping")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("catalog must contain non-empty entries")

    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or REQUIRED_ENTRY_FIELDS - set(entry):
            raise ValueError("each catalog entry must contain the required fields")
        product_id = entry["id"]
        if not isinstance(product_id, str) or not product_id or product_id in seen:
            raise ValueError("catalog entry ids must be unique non-empty strings")
        seen.add(product_id)
        for field in ("tier", "artifact_path", "recipe", "entrypoint", "state"):
            if not isinstance(entry[field], str) or not entry[field]:
                raise ValueError(f"catalog entry {product_id!r} has invalid {field!r}")
        if Path(entry["artifact_path"]).is_absolute() or Path(entry["recipe"]).is_absolute():
            raise ValueError(f"catalog entry {product_id!r} must use repository-relative paths")
        if not isinstance(entry["files"], list) or not entry["files"] or not all(
            isinstance(name, str) and name and not Path(name).is_absolute()
            for name in entry["files"]
        ):
            raise ValueError(f"catalog entry {product_id!r} has invalid files")
    return entries


def catalog_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=catalog_root() / "docs/products/ARTIFACT_CATALOG.yml",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=catalog_root(),
        help="Checkout containing the machine-local local/ product store.",
    )
    parser.add_argument(
        "--require-present",
        action="store_true",
        help="Return nonzero when a cataloged local product is absent or incomplete.",
    )
    args = parser.parse_args(argv)

    try:
        entries = load_catalog(args.catalog)
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.error(f"invalid product catalog: {error}")

    missing = 0
    root = args.root.resolve()
    for entry in entries:
        artifact = root / entry["artifact_path"]
        absent = [name for name in entry["files"] if not (artifact / name).is_file()]
        if absent:
            missing += 1
            print(f"MISSING  {entry['id']}: {artifact} ({', '.join(absent)})")
        else:
            print(f"PRESENT  {entry['id']}: {artifact}")
    print(f"Catalog: {len(entries) - missing} present, {missing} missing, {len(entries)} total")
    return 1 if args.require_present and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

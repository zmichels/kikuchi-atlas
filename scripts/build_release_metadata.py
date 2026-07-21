#!/usr/bin/env python3
"""Build the tracked Kikuchi Atlas structural-source attribution audit."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas import build_structural_source_audit


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "docs/atlas/PHASE_REGISTRY.yml")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/atlas")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_structural_source_audit(registry_path=args.registry, output_directory=args.output)
    print(
        f"structural source audit built sources={result.source_count} json={result.json_path} "
        f"markdown={result.markdown_path}"
    )


if __name__ == "__main__":
    main()

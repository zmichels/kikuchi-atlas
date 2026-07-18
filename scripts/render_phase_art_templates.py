#!/usr/bin/env python3
"""Publish reusable standard-width direct-reflector print templates for one phase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kikuchi_lab.art_products.hemisphere_recipe import load_hemisphere_series_recipe
from kikuchi_lab.workflows.phase_art_templates import render_phase_art_templates


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument(
        "--series-recipe",
        type=Path,
        default=ROOT / "recipes/art/five-phase-hemisphere-series.yml",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = render_phase_art_templates(
        phase_slug=args.phase,
        catalog_path=args.catalog,
        series=load_hemisphere_series_recipe(args.series_recipe),
        output_root=args.output,
    )
    print(
        json.dumps(
            {
                "phase": result.phase_slug,
                "standard_source": str(result.standard_bundle.path),
                "templates": [
                    {
                        "variant": variant.slug,
                        "bunge_zxz_deg": list(variant.orientation.euler_bunge_deg),
                        "path": str(bundle.path),
                        "svg": str(bundle.path / f"{args.phase}-hemisphere-standard.svg"),
                        "stencil": str(
                            bundle.path / f"{args.phase}-hemisphere-standard-stencil.png"
                        ),
                    }
                    for variant, bundle in result.bundles
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

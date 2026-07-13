"""Kikuchi Lab command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from kikuchi_lab import __version__
from kikuchi_lab.doctor import collect_doctor_report


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI with an optional explicit argument sequence."""
    parser = argparse.ArgumentParser(prog="kikuchi-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("version", help="Print the package version.")
    doctor = subparsers.add_parser("doctor", help="Check the simulation runtime.")
    doctor.add_argument("--json", action="store_true", dest="as_json")
    doctor.add_argument("--output-root", default="local")
    simulate = subparsers.add_parser(
        "simulate-master", help="Generate and validate a canonical master pattern."
    )
    simulate.add_argument("--structure", required=True)
    simulate.add_argument("--source", required=True)
    simulate.add_argument("--recipe", required=True)
    simulate.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    if args.command == "version":
        print(f"kikuchi-lab {__version__}")
        return 0

    if args.command == "doctor":
        report = collect_doctor_report(args.output_root)
        if args.as_json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print("Kikuchi Lab runtime: " + ("ready" if report["ok"] else "not ready"))
            for name, check in report["checks"].items():
                state = "PASS" if check["ok"] else "FAIL"
                print(f"{state:4} {name}: {check['observed']}")
        return 0 if report["ok"] else 1

    if args.command == "simulate-master":
        from kikuchi_lab.sources.ebsdsim_adapter import (
            generate_master_pattern,
            load_simulation_recipe,
        )
        from kikuchi_lab.sources.structure import load_structure_record

        try:
            source = load_structure_record(args.source)
            requested_structure = Path(args.structure).resolve()
            if requested_structure != source.cif_path:
                raise ValueError(
                    "--structure must resolve to the tracked CIF named by --source"
                )
            recipe = load_simulation_recipe(args.recipe)
            output_root = Path(args.output).resolve()
            output_root.mkdir(parents=True, exist_ok=True)
            result = generate_master_pattern(
                source=source,
                recipe=recipe,
                output_npz=output_root / f"{source.identifier}-ebsdsim.npz",
            )
        except (OSError, ValueError, RuntimeError) as error:
            print(f"kikuchi-lab: simulation failed: {error}", file=sys.stderr)
            return 1
        print(result.manifest)
        return 0

    return 2


def entrypoint() -> None:
    """Console-script wrapper."""
    raise SystemExit(main())

"""Kikuchi Lab command-line entry point."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from kikuchi_lab import __version__
from kikuchi_lab.doctor import collect_doctor_report


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI with an optional explicit argument sequence."""
    arguments = list(sys.argv[1:] if argv is None else argv)
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
    proof = subparsers.add_parser(
        "proof", help="Render a deterministic orientation proof for human review."
    )
    proof.add_argument("--recipe", required=True)
    proof.add_argument("--master-product", required=True)
    proof.add_argument("--source", required=True)
    proof.add_argument("--output", required=True)
    select_orientation = subparsers.add_parser(
        "select-orientation",
        help="Record an immutable human orientation decision for a sealed proof.",
    )
    select_orientation.add_argument("--run", required=True)
    select_orientation.add_argument("--candidate", required=True)
    select_orientation.add_argument("--author", required=True)
    select_orientation.add_argument("--rationale", required=True)
    select_orientation.add_argument("--selected-on", required=True)
    select_orientation.add_argument("--output", required=True)
    select_orientation.add_argument("--supersedes")
    select_orientation.add_argument("--supersede-reason")
    render_final_parser = subparsers.add_parser(
        "render-final",
        help="Render a verified current orientation selection into final products.",
    )
    render_final_parser.add_argument("--recipe", required=True)
    render_final_parser.add_argument("--selection", required=True)
    render_final_parser.add_argument("--proof-root", required=True)
    render_final_parser.add_argument("--master-product", required=True)
    render_final_parser.add_argument("--output", required=True)
    render_final_parser.add_argument(
        "--profile", choices=("final", "development"), default="final"
    )
    reproduce_final_parser = subparsers.add_parser(
        "reproduce-final",
        help="Rebuild a final run from its manifest recipe snapshot.",
    )
    reproduce_final_parser.add_argument("--run", required=True)
    reproduce_final_parser.add_argument("--selection", required=True)
    reproduce_final_parser.add_argument("--proof-root", required=True)
    reproduce_final_parser.add_argument("--master-product", required=True)
    reproduce_final_parser.add_argument("--output", required=True)
    reproduce_final_parser.add_argument(
        "--source-mode", choices=("exact", "gpu-tolerant"), default="exact"
    )
    reproduce_final_parser.add_argument("--source-atol", type=float, default=0.0)
    reproduce_final_parser.add_argument("--source-rtol", type=float, default=0.0)
    args = parser.parse_args(arguments)

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

    if args.command == "proof":
        from kikuchi_lab.model import load_master_product
        from kikuchi_lab.workflows import load_proof_recipe, render_proof

        try:
            load_proof_recipe(args.recipe)
            master = load_master_product(args.master_product)
            result = render_proof(
                master=master,
                recipe_path=args.recipe,
                output_root=args.output,
                master_locator=args.master_product,
                source_locator=args.source,
                invocation=["kikuchi-lab", *arguments],
            )
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"kikuchi-lab: proof failed: {error}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "proof_id": result.proof_id,
                    "state": result.state,
                    "path": str(result.path),
                    "contact_sheet": str(result.contact_sheet),
                    "candidate_count": len(result.candidate_ids),
                    "elapsed_seconds": result.elapsed_seconds,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "select-orientation":
        from kikuchi_lab.orientations.selection import (
            OrientationSelectionError,
            create_orientation_selection,
        )

        try:
            result = create_orientation_selection(
                run=args.run,
                candidate_id=args.candidate,
                author=args.author,
                rationale=args.rationale,
                selected_on=args.selected_on,
                output_root=args.output,
                supersedes=args.supersedes,
                supersede_reason=args.supersede_reason,
            )
        except (OSError, OrientationSelectionError) as error:
            print(f"kikuchi-lab: selection failed: {error}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "selection_id": result.selection_id,
                    "path": str(result.path),
                    "selection": str(result.selection_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "render-final":
        from kikuchi_lab.model import load_master_product
        from kikuchi_lab.workflows import render_final

        try:
            result = render_final(
                master=load_master_product(args.master_product),
                recipe_path=args.recipe,
                selection_path=args.selection,
                proof_root=args.proof_root,
                output_root=args.output,
                profile=args.profile,
            )
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"kikuchi-lab: final render failed: {error}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "path": str(result.path),
                    "profile": result.profile,
                    "selection_id": result.selection_id,
                    "not_final_quality": result.not_final_quality,
                    "elapsed_seconds": result.elapsed_seconds,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "reproduce-final":
        from kikuchi_lab.model import load_master_product
        from kikuchi_lab.workflows import reproduce_final

        try:
            result = reproduce_final(
                original_run=args.run,
                master=load_master_product(args.master_product),
                selection_path=args.selection,
                proof_root=args.proof_root,
                output_root=args.output,
                source_mode=args.source_mode,
                source_atol=args.source_atol,
                source_rtol=args.source_rtol,
            )
        except (OSError, ValueError, RuntimeError, AssertionError) as error:
            print(f"kikuchi-lab: final reproduction failed: {error}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "reproduced": result.comparison.equal,
                    "run_id": result.run.run_id,
                    "path": str(result.run.path),
                    "source_comparison": result.comparison.source_comparison,
                    "cpu_processing_comparison": result.comparison.cpu_processing_comparison,
                    "first_manifest_identity": result.comparison.first_manifest_identity,
                    "second_manifest_identity": result.comparison.second_manifest_identity,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    return 2


def entrypoint() -> None:
    """Console-script wrapper."""
    raise SystemExit(main())

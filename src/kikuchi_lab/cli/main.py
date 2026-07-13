"""Kikuchi Lab command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from kikuchi_lab import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI with an optional explicit argument sequence."""
    parser = argparse.ArgumentParser(prog="kikuchi-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("version", help="Print the package version.")
    args = parser.parse_args(argv)

    if args.command == "version":
        print(f"kikuchi-lab {__version__}")
        return 0

    return 2


def entrypoint() -> None:
    """Console-script wrapper."""
    raise SystemExit(main())

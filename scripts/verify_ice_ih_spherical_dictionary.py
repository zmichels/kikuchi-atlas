#!/usr/bin/env python3
"""Verify an Ice Ih spherical candidate dictionary package."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from kikuchi_lab.dictionary.ice_ih import verify_ice_ih_candidate_dictionary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="candidate dictionary package directory")
    args = parser.parse_args(argv)
    try:
        result = verify_ice_ih_candidate_dictionary(args.package)
    except ValueError as error:
        print(f"verification failed: {error}", file=sys.stderr)
        return 2
    print(f"Verified {result.dictionary_id}")
    print(f"Entries: {result.entry_count}")
    print(f"Expected top entry index: {result.expected_top_entry_index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

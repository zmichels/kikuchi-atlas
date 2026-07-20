#!/usr/bin/env python3
"""Verify a portable spherical dictionary package and its ranking fixture."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from kikuchi_lab.dictionary import verify_spherical_dictionary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="dictionary package directory")
    args = parser.parse_args(argv)
    try:
        result = verify_spherical_dictionary(args.package)
    except ValueError as error:
        print(f"verification failed: {error}", file=sys.stderr)
        return 2
    print(f"Verified {result.dictionary_id}")
    print(f"Files: {result.file_count}")
    print(f"Expected top entry: {result.expected_top_entry_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

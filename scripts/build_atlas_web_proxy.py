#!/usr/bin/env python3
"""Build and verify one heavyweight Atlas browser proxy."""

from __future__ import annotations

import argparse
from pathlib import Path

from kikuchi_lab.atlas.web_proxy import WEB_PROXY_PROFILE, build_web_proxy


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--profile", default=WEB_PROXY_PROFILE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_web_proxy(args.source, args.destination, args.profile)
    print(
        f"frames={result.frame_count} fps={result.frame_rate:g} "
        f"duration={result.duration_seconds:.3f} bytes={result.byte_count} "
        f"sha256={result.sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Summarize Kikuchi Lab's validated repo-native work items.

Adapted from the repo-native-work-tracking skill's work_tracker.py.
Original source: /Users/Z/.codex/skills/repo-native-work-tracking/
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from validate_work_items import validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    work_root = args.root / "docs" / "work"
    items = validate(work_root)
    counts = Counter((item.metadata["type"], item.metadata["status"]) for item in items.values())
    type_counts = Counter(item.metadata["type"] for item in items.values())

    print("Work tracker status")
    print(f"  epic: {type_counts['epic']}")
    print(f"  feature: {type_counts['feature']}")
    print(f"  task: {type_counts['task']}")
    print(f"  done: {sum(count for (kind, status), count in counts.items() if status == 'done')}")
    print(f"  ready: {sum(count for (kind, status), count in counts.items() if status == 'ready')}")
    print(f"  active: {sum(count for (kind, status), count in counts.items() if status == 'active')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

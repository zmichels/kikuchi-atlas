#!/usr/bin/env python3
"""Create the next flat KIKU task work item.

Adapted from the repo-native-work-tracking skill's scaffold_tracker.py.
Original source: /Users/Z/.codex/skills/repo-native-work-tracking/
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from validate_work_items import load_items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title")
    parser.add_argument("--parent", default="KIKU-F001")
    parser.add_argument("--root", type=Path, default=Path("docs/work"))
    args = parser.parse_args(argv)

    items = load_items(args.root)
    next_number = 1 + max(
        int(item_id.removeprefix("KIKU-T"))
        for item_id in items
        if item_id.startswith("KIKU-T")
    )
    item_id = f"KIKU-T{next_number:03d}"
    path = args.root / f"{item_id}.md"
    body = f"""---
id: {item_id}
type: task
title: {args.title}
status: proposed
parent: {args.parent}
created: {date.today().isoformat()}
priority: P2
tags: [planning]
---

# {item_id}: {args.title}

## Description

Describe the intended increment and its evidence.

## Acceptance Criteria

- [ ] Observable evidence is recorded here.
"""
    path.write_text(body, encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

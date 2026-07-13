#!/usr/bin/env python3
"""Create the next flat KIKU task work item.

Adapted from the repo-native-work-tracking skill's scaffold_tracker.py.
Original source: /Users/Z/.codex/skills/repo-native-work-tracking/
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import yaml

from validate_work_items import load_items


def _append_child_to_parent(parent_path: Path, child_id: str) -> None:
    text = parent_path.read_text(encoding="utf-8")
    _, raw_frontmatter, body = text.split("---\n", 2)
    metadata = yaml.safe_load(raw_frontmatter)
    children = metadata.setdefault("children", [])
    children.append(child_id)
    updated_frontmatter = yaml.safe_dump(metadata, sort_keys=False)
    parent_path.write_text(f"---\n{updated_frontmatter}---\n{body}", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title")
    parser.add_argument("--parent", default="KIKU-F001")
    parser.add_argument("--root", type=Path, default=Path("docs/work"))
    args = parser.parse_args(argv)

    items = load_items(args.root)
    if args.parent not in items or items[args.parent].metadata["type"] != "feature":
        parser.error(f"parent must name an existing feature: {args.parent}")
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
    _append_child_to_parent(items[args.parent].path, item_id)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

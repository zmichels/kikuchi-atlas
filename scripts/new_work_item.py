#!/usr/bin/env python3
"""Create the next flat KIKU task work item.

Adapted from the repo-native-work-tracking skill's scaffold_tracker.py.
Original source: /Users/Z/.codex/skills/repo-native-work-tracking/
"""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

import yaml

from validate_work_items import load_items, validate


def _read_document(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    _, raw_frontmatter, body = text.split("---\n", 2)
    metadata = yaml.safe_load(raw_frontmatter)
    return metadata, body


def _render_document(metadata: dict[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
    return f"---\n{frontmatter}---\n{body}"


def _render_updated_parent(parent_path: Path, child_id: str) -> str:
    metadata, body = _read_document(parent_path)
    children = metadata.setdefault("children", [])
    children.append(child_id)
    return _render_document(metadata, body)


def _validate_candidate(
    work_root: Path,
    parent_name: str,
    parent_document: str,
    child_name: str,
    child_document: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="kikuchi-tracker-validation-") as temporary:
        staged_root = Path(temporary) / "work"
        shutil.copytree(work_root, staged_root)
        (staged_root / parent_name).write_text(parent_document, encoding="utf-8")
        (staged_root / child_name).write_text(child_document, encoding="utf-8")
        validate(staged_root)


def _replace_pair(
    work_root: Path,
    parent_path: Path,
    parent_document: str,
    child_path: Path,
    child_document: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix=".new-work-item-", dir=work_root) as temporary:
        temporary_root = Path(temporary)
        temporary_parent = temporary_root / parent_path.name
        temporary_child = temporary_root / child_path.name
        temporary_child.write_text(child_document, encoding="utf-8")
        temporary_parent.write_text(parent_document, encoding="utf-8")
        os.replace(temporary_child, child_path)
        try:
            os.replace(temporary_parent, parent_path)
        except Exception:
            child_path.unlink(missing_ok=True)
            raise


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
    metadata = {
        "id": item_id,
        "type": "task",
        "title": args.title,
        "status": "proposed",
        "parent": args.parent,
        "created": date.today().isoformat(),
        "priority": "P2",
        "tags": ["planning"],
    }
    display_title = args.title.replace("\n", " ")
    body = f"""
# {item_id}: {display_title}

## Description

Describe the intended increment and its evidence.

## Acceptance Criteria

- [ ] Observable evidence is recorded here.
"""
    child_document = _render_document(metadata, body)
    parent_path = items[args.parent].path
    parent_document = _render_updated_parent(parent_path, item_id)
    _validate_candidate(
        args.root,
        parent_path.name,
        parent_document,
        path.name,
        child_document,
    )
    _replace_pair(args.root, parent_path, parent_document, path, child_document)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

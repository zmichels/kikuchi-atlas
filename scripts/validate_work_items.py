#!/usr/bin/env python3
"""Validate Kikuchi Lab's repo-native work items.

Adapted from the repo-native-work-tracking skill's work_tracker.py.
Original source: /Users/Z/.codex/skills/repo-native-work-tracking/
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


ALLOWED_STATUSES = {"proposed", "ready", "active", "blocked", "done", "deferred", "superseded"}
ALLOWED_PRIORITIES = {"P0", "P1", "P2", "P3"}
EXPECTED_PARENT_TYPE = {"epic": None, "feature": "epic", "task": "feature"}
ID_PATTERN = re.compile(r"^KIKU-([EFT])(\d{3})$")
CHECKBOX_PATTERN = re.compile(r"^- \[[ xX]\] .+", re.MULTILINE)


class ValidationError(ValueError):
    """Raised when a work item violates the project tracker contract."""


@dataclass(frozen=True)
class WorkItem:
    path: Path
    metadata: dict[str, Any]
    body: str


def _parse_item(path: Path) -> WorkItem:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValidationError(f"{path}: missing YAML frontmatter")
    try:
        _, raw_frontmatter, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValidationError(f"{path}: malformed YAML frontmatter") from exc
    metadata = yaml.safe_load(raw_frontmatter)
    if not isinstance(metadata, dict):
        raise ValidationError(f"{path}: frontmatter must be a mapping")
    return WorkItem(path, metadata, body)


def load_items(root: Path) -> dict[str, WorkItem]:
    items: dict[str, WorkItem] = {}
    for path in sorted(root.glob("KIKU-*.md")):
        item = _parse_item(path)
        item_id = item.metadata.get("id")
        if not isinstance(item_id, str):
            raise ValidationError(f"{path}: missing string id")
        if item_id in items:
            raise ValidationError(f"duplicate work item id: {item_id}")
        items[item_id] = item
    if not items:
        raise ValidationError(f"{root}: no KIKU work items found")
    return items


def validate(root: Path) -> dict[str, WorkItem]:
    items = load_items(root)
    letter_by_type = {"epic": "E", "feature": "F", "task": "T"}

    for item_id, item in items.items():
        metadata = item.metadata
        for field in ("id", "type", "title", "status", "parent", "created", "priority"):
            if field not in metadata:
                raise ValidationError(f"{item.path}: missing required field {field!r}")
        item_type = metadata["type"]
        if item_type not in EXPECTED_PARENT_TYPE:
            raise ValidationError(f"{item.path}: invalid type {item_type!r}")
        match = ID_PATTERN.fullmatch(item_id)
        if match is None or match.group(1) != letter_by_type[item_type]:
            raise ValidationError(f"{item.path}: id does not match type {item_type}")
        if item.path.stem != item_id:
            raise ValidationError(f"{item.path}: filename must match id")
        if metadata["status"] not in ALLOWED_STATUSES:
            raise ValidationError(f"{item.path}: invalid status {metadata['status']!r}")
        if metadata["priority"] not in ALLOWED_PRIORITIES:
            raise ValidationError(f"{item.path}: invalid priority {metadata['priority']!r}")
        if "## Description" not in item.body or "## Acceptance Criteria" not in item.body:
            raise ValidationError(f"{item.path}: required body section missing")
        if not CHECKBOX_PATTERN.search(item.body.split("## Acceptance Criteria", 1)[1]):
            raise ValidationError(f"{item.path}: acceptance criteria must contain checkboxes")
        if metadata["status"] == "done" and "- [ ]" in item.body.split("## Acceptance Criteria", 1)[1]:
            raise ValidationError(f"{item.path}: done item has unchecked acceptance criteria")

        expected_parent_type = EXPECTED_PARENT_TYPE[item_type]
        parent_id = metadata["parent"]
        if expected_parent_type is None:
            if parent_id not in (None, ""):
                raise ValidationError(f"{item.path}: epic parent must be empty")
        else:
            if parent_id not in items:
                raise ValidationError(f"{item.path}: parent {parent_id!r} does not exist")
            if items[parent_id].metadata["type"] != expected_parent_type:
                raise ValidationError(f"{item.path}: parent must be a {expected_parent_type}")
            if item_id not in (items[parent_id].metadata.get("children") or []):
                raise ValidationError(f"{item.path}: parent {parent_id} does not list child {item_id}")

        children = metadata.get("children", [])
        if item_type != "task" and not isinstance(children, list):
            raise ValidationError(f"{item.path}: children must be a list")
        for child_id in children or []:
            if child_id not in items:
                raise ValidationError(f"{item.path}: child {child_id!r} does not exist")
            if items[child_id].metadata.get("parent") != item_id:
                raise ValidationError(f"{item.path}: child {child_id} does not point back")
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("docs/work"))
    args = parser.parse_args(argv)
    items = validate(args.root)
    print(f"Validated {len(items)} work items in {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

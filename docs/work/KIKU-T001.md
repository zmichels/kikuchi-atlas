---
id: KIKU-T001
type: task
title: Bootstrap Package, Tracker, and Environment Gate
status: done
parent: KIKU-F001
created: 2026-07-12
started: 2026-07-12
completed: 2026-07-12
priority: P0
tags: [bootstrap, python, tracker]
links:
  - ../../pyproject.toml
  - ../../tests/unit/test_cli.py
  - index.md
---

# KIKU-T001: Bootstrap Package, Tracker, and Environment Gate

## Description

Create the installable Python 3.12 package, minimal version CLI, local-only
development guidance, and validated repo-native milestone hierarchy.

## Acceptance Criteria

- [x] `uv run pytest tests/unit/test_cli.py -q` passes for the version command.
- [x] `uv run ruff check src tests` passes on the package foundation.
- [x] The managed runtime reports Python 3.12 on arm64.
- [x] `scripts/validate_work_items.py` accepts the symmetric KIKU hierarchy.
- [x] `scripts/work_status.py --root .` reports exactly one done task.

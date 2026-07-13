# Kikuchi Lab Work Tracker

This flat, source-controlled ledger maps the approved exceptional-forsterite
implementation plan to stable `KIKU` identifiers. Frontmatter and acceptance
criteria in each item are canonical; chat history is not required to recover
project state.

## Commands

```bash
uv run python scripts/validate_work_items.py
uv run python scripts/work_status.py --root .
```

The first milestone is `KIKU-E001`. `KIKU-F001` contains the twelve
review-sized implementation tasks. Only accepted work is marked `done`.

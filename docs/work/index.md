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

`KIKU-E001` is the broader dynamical Kikuchi companion. Its first milestone,
`KIKU-F001`, contains the twelve review-sized implementation tasks for an
exceptional forsterite pattern. The milestone's specific implementation plan
intentionally maps those tasks directly to its single feature: adding an
artificial story layer would not add a meaningful planning or acceptance
boundary. Parent/child links remain symmetric, and only accepted work is
marked `done`.

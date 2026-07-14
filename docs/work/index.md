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

`KIKU-E001` is the broader dynamical Kikuchi companion. `KIKU-F001` contains
the twelve review-sized implementation tasks for the dynamical exceptional-
forsterite pattern. `KIKU-F002` adds six tasks for a deliberately separate,
kikuchipy-native kinematical reference bundle and its visual decision gate.
`KIKU-F003` adds six dependent tasks for an exact spherical scalar field,
validated axial derivative, and bounded MTEX density/3D bridge. Parent/child
links remain symmetric, and only accepted work is marked `done`.

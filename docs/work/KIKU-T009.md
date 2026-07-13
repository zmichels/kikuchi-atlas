---
id: KIKU-T009
type: task
title: Record the Human Orientation Choice
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [decision, orientation, human-gate]
evidence:
  - ../../tests/unit/test_orientation_selection.py
  - ../../src/kikuchi_lab/orientations/selection.py
  - ../../local/decisions/forsterite-selection/selection.json
---

# KIKU-T009: Record the Human Orientation Choice

## Description

Validate and persist the user's selected proof candidate, rationale, source
comparison identity, and any bounded final-render adjustments.

## Acceptance Criteria

- [ ] Selection-schema and CLI validation tests reject ambiguous or stale proof choices.
- [ ] `local/decisions/forsterite-selection/selection.json` references one candidate and one proof bundle.
- [ ] User approval evidence is linked here before the task is marked done.

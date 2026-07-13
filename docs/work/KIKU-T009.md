---
id: KIKU-T009
type: task
title: Record the Human Orientation Choice
status: done
parent: KIKU-F001
created: 2026-07-12
completed: 2026-07-13
priority: P0
tags: [decision, orientation, human-gate]
evidence:
  - ../../tests/unit/test_orientation_selection.py
  - ../../src/kikuchi_lab/orientations/selection.py
  - ../../local/decisions/orientation-selection-c6e4810de875c630/selection.json
---

# KIKU-T009: Record the Human Orientation Choice

## Description

Validate and persist the user's selected proof candidate, rationale, source
comparison identity, and any bounded final-render adjustments.

## Acceptance Criteria

- [x] Selection-schema and CLI validation tests reject ambiguous or stale proof choices.
- [x] The content-addressed selection references one candidate, the sealed proof,
  its external manifest checksum, and exact candidate-set, candidate, evidence,
  geometry, and metrics checksums.
- [x] User approval is recorded with author `Z`, date `2026-07-13`, and the
  concrete visual rationale in the immutable selection artifact.

## Accepted Evidence

- Implementation commit: `2841d87` (`feat: add immutable orientation selections`).
- Selection: `orientation-selection-c6e4810de875c630` for
  `fo-011-phi1-045`; artifact SHA-256
  `4dea097ce6e0af51812895e1c360e42e7d7db55bd08cccf2886e4acb708ed3fc`.
- Authoritative proof: `proof-bb3c2766ff577427`; manifest SHA-256
  `76fa1a3d62aa9aac06cfc1a90dd5319500da42b25d682bed3c731053b9ae8e57`.
- The complete proof-tree digest was
  `55a9a3d81c2b0cab147676e22a8ce0edff7b67f5d9865364513bd3c9b6eba277`
  both immediately before and immediately after selection publication.
- Focused gate: `14 passed` in `tests/unit/test_orientation_selection.py`.
- Fast full gate: `320 passed`; Ruff and the 14-item work tracker validated.

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
  - ../../local/decisions/orientation-selection-be329b1c99f2066e/selection.json
  - ../../local/decisions/orientation-selection-c6e4810de875c630/selection.json
---

# KIKU-T009: Record the Human Orientation Choice

## Description

Validate and persist the user's selected proof candidate, rationale, source
comparison identity, and any bounded final-render adjustments.

## Acceptance Criteria

- [x] Selection-schema and CLI validation tests reject ambiguous or stale proof choices.
- [x] Candidate metadata IDs are globally unique, `candidate_order` contains
  every candidate exactly once, and the selected ID resolves to one candidate
  and one evidence directory before human choice is accepted.
- [x] The content-addressed selection references one candidate, the sealed proof,
  its external manifest checksum, and exact candidate-set, candidate, evidence,
  geometry, metrics, and proof-tree checksums.
- [x] User approval is recorded with author `Z`, date `2026-07-13`, and the
  concrete visual rationale in the immutable selection artifact.

## Accepted Evidence

- Implementation commits: `2841d87` (`feat: add immutable orientation
  selections`) and `9aac920` (`fix: reject ambiguous orientation selections`).
- Authoritative schema-v2 selection: `orientation-selection-be329b1c99f2066e`
  for `fo-011-phi1-045`; artifact SHA-256
  `4696ef01be1635c3ab521d10c897c475020c2ddb38a794cd74751cc97abf2c79`.
- The schema-v2 selection supersedes, but does not overwrite,
  `orientation-selection-c6e4810de875c630`. The original schema-v1 artifact
  remains byte-identical at SHA-256
  `4dea097ce6e0af51812895e1c360e42e7d7db55bd08cccf2886e4acb708ed3fc`;
  the scientific orientation, author, date, and rationale are unchanged.
- Authoritative proof: `proof-bb3c2766ff577427`; manifest SHA-256
  `76fa1a3d62aa9aac06cfc1a90dd5319500da42b25d682bed3c731053b9ae8e57`.
- Canonical proof-tree digest: 93 files, SHA-256
  `84f398693ce40fb65971becdabb4c0080e9928d696790ec8b7a899fa8b84e7cd`.
  It is recomputable as follows: enumerate every non-symlink regular file
  recursively under the proof root, including `manifest.json`, with no file
  exclusions; form entries containing `relative_posix_path`, file `sha256`,
  and byte count; order entries by ascending Unicode code-point order of the
  relative POSIX path; then SHA-256 hash the UTF-8, no-trailing-newline
  canonical JSON object containing the versioned contract and ordered entries.
  The exact contract is embedded in the schema-v2 selection.
- Focused gate: `21 passed` in `tests/unit/test_orientation_selection.py`.
- Fast full gate: `327 passed`; Ruff and the 14-item work tracker validated.

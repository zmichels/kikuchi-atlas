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
  - ../../local/decisions/orientation-selection-0903bbee65fa3896/selection.json
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
- [x] Proof-scoped cross-process locking permits one concurrent winner and
  enforces a single linear supersession leaf without forks or double successors.
- [x] Proof traversal and every proof-relative locator reject symbolic links,
  escaping paths, and non-regular entries before a decision can be published.
- [x] Publication fsyncs the selection file and staging directory before atomic
  rename, then fsyncs the output directory; failed pre-rename publication cleans
  its staging directory.
- [x] The content-addressed selection references one candidate, the sealed proof,
  its external manifest checksum, and exact candidate-set, candidate, evidence,
  geometry, metrics, and proof-tree checksums.
- [x] User approval is recorded with author `Z`, date `2026-07-13`, and the
  concrete visual rationale in the immutable selection artifact.

## Accepted Evidence

- Implementation commits: `2841d87` (`feat: add immutable orientation
  selections`), `9aac920` (`fix: reject ambiguous orientation selections`),
  and `92e7cc8` (`fix: serialize and harden orientation decisions`).
- Authoritative schema-v3 leaf: `orientation-selection-0903bbee65fa3896`
  for `fo-011-phi1-045`; artifact SHA-256
  `ca9ac51b14b7a862c8d33734071a57397e58556d2aa4d869e76a67b817ff818b`.
- The lineage is exactly v1 -> v2 -> v3 with one leaf. Schema-v2
  `orientation-selection-be329b1c99f2066e` remains byte-identical at SHA-256
  `4696ef01be1635c3ab521d10c897c475020c2ddb38a794cd74751cc97abf2c79`;
  schema-v1 `orientation-selection-c6e4810de875c630` remains byte-identical at
  SHA-256
  `4dea097ce6e0af51812895e1c360e42e7d7db55bd08cccf2886e4acb708ed3fc`;
  the scientific orientation, author, date, and rationale are unchanged.
  In every supersession link, `selection_id` is defined as
  `orientation-selection-` plus the first 16 lowercase hexadecimal characters
  of that predecessor's full `decision_sha256`; the full predecessor decision
  and selection-file hashes are also required and validated.
- Authoritative proof: `proof-bb3c2766ff577427`; manifest SHA-256
  `76fa1a3d62aa9aac06cfc1a90dd5319500da42b25d682bed3c731053b9ae8e57`.
- Canonical proof-tree digest: 93 files, SHA-256
  `e2c0aafe851bba0e823e8b2f922eb7dd1eab7b20b911ce0648af1b0183ffc350`.
  It is recomputable as follows: recursively enumerate every regular file under
  the proof root, including `manifest.json`, with an empty exclusions list;
  encountering any symbolic link or non-regular entry is an error. Form entries
  containing `relative_posix_path`, file `sha256`, and byte count; order entries
  by ascending Unicode code-point order of the relative POSIX path; then
  SHA-256 hash the UTF-8, no-trailing-newline canonical JSON object containing
  the versioned contract and ordered entries. The exact contract is embedded
  in the schema-v3 selection.
- Concurrency gates: a deterministic six-subprocess supersession race and a
  separate concurrent-initial-selection race each produced exactly one winner.
- Focused gate: `38 passed` in `tests/unit/test_orientation_selection.py`.
- Fast full gate: `344 passed`; Ruff and the 14-item work tracker validated.

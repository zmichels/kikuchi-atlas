---
id: KIKU-T077
type: task
title: Track and verify the Ni source inventory without redistributing raw data
status: done
parent: KIKU-F029
children: []
created: 2026-07-24
priority: P1
tags: [reference-pack, integrity, checksum, kikuchipy]
links:
  - ../../reference-packs/ni-gain24db-calibration-hough-v0.1.source-inventory.json
evidence:
  - ../../src/kikuchi_lab/reference_pack/integrity.py
  - ../../scripts/verify_ni_gain24db_reference_pack.py
---

# KIKU-T077: Track and verify the Ni source inventory without redistributing raw data

## Description

Make the external Ni source inspectable through a strict tracked inventory and
a small dependency-free integrity layer, then connect it to the documented
Kikuchipy loaders.

## Acceptance Criteria

- [x] The verifier requires exact source filenames, byte sizes, and SHA-256
  values rather than accepting a plausible-looking cache.
- [x] It does not write a raw-data copy into the repository and downloads only
  after explicit `--allow-download`.

## Completion Evidence

Unit tests cover success, missing/extra/modified files, and malformed
inventories. The real local verification accepted all 26 pinned source files.

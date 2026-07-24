---
id: KIKU-T080
type: task
title: Render and document the Ni preprocessing-sensitivity evidence bundle
status: done
parent: KIKU-F030
children: []
created: 2026-07-24
priority: P1
tags: [nickel, visualization, provenance, reference-pack]
links:
  - ../acceptance/ni-gain24db-preprocessing-sensitivity.md
  - ../reference-packs/ni-gain24db-preprocessing-sensitivity-v0.1.md
evidence:
  - ../../scripts/run_ni_gain24db_preprocessing_sensitivity.py
---

# KIKU-T080: Render and document the Ni preprocessing-sensitivity evidence bundle

## Description

Create a compact visual and documentation slice that shows the same source
pattern under each declared variant, the aggregate diagnostics, and the
symmetry-reduced orientation agreement without over-interpreting any of them.

## Acceptance Criteria

- [x] The runner writes a visual, JSON result, and SHA-256 manifest into an
  ignored immutable local output directory.
- [x] Public documentation gives the exact command, result values, source
  linkage, and nonclaims.

## Completion Evidence

The 1.64 MB diagnostic visual and 5.2 KB local report are checksum-listed. The
small, attributed CC BY derived figure is retained under the Reference Pack
docs for browser sharing; raw EBSD inputs remain upstream.

---
id: KIKU-T008
type: task
title: Render the Deterministic Proof Comparison
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P1
tags: [proof, contact-sheet, comparison]
evidence:
  - ../../tests/integration/test_proof_workflow.py
  - ../../recipes/proof/forsterite-proof.yml
  - ../../src/kikuchi_lab/artifacts/contact_sheet.py
  - ../../local/runs/
---

# KIKU-T008: Render the Deterministic Proof Comparison

## Description

Render the fixed candidate set into matched acquisition/gallery comparisons
and a legible contact sheet for human orientation selection.

## Acceptance Criteria

- [ ] Proof integration tests reproduce bundle identities and contact-sheet layout.
- [ ] Each tile exposes orientation and processing identity without obscuring bands.
- [ ] The proof bundle and contact sheet are linked here.

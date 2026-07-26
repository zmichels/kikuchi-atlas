---
id: KIKU-T085
type: task
title: Canonicalize Atlas product packages
status: ready
parent: KIKU-F012
children: []
created: 2026-07-25
priority: P1
tags: [atlas, publication, consolidation]
links:
  - ../atlas/CONSOLIDATION.yml
  - ../atlas/ATLAS_MIGRATION.yml
evidence:
  - ../../src/kikuchi_lab/atlas/consolidation.py
  - ../atlas/ATLAS_MIGRATION.yml
---

# KIKU-T085: Canonicalize Atlas product packages

## Description

Copy every publishable 12-phase Atlas artifact into the phase-slugged canonical package hierarchy and prove byte identity before registry cutover.

## Acceptance Criteria

- [ ] Exactly 125 product manifests and 12 phase manifests validate.
- [ ] Every copied destination matches its frozen source SHA-256 and byte count.
- [ ] The 125-product Atlas builds without a legacy-root fallback.
- [ ] No legacy file has been deleted before all external publication gates pass.

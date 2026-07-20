---
id: KIKU-T028
type: task
title: Publish shared Ice Ih art band catalog
status: done
parent: KIKU-F005
created: 2026-07-16
priority: P1
tags: [ice-ih, science-art, catalog, provenance]
links:
  - ../superpowers/specs/2026-07-16-ice-art-globe-and-tattoo-design.md
  - ../superpowers/plans/2026-07-16-ice-art-catalog-and-tattoo.md
evidence:
  - ../superpowers/plans/2026-07-16-ice-art-catalog-and-tattoo.md
  - ../acceptance/ice-ih-tattoo-primary.md
---

# KIKU-T028: Publish shared Ice Ih art band catalog

## Description

Build and publish the source-location-independent catalog that ranks validated
Ice Ih axial bands, records globe and tattoo eligibility, and partitions globe
members into four nonempty tie-aware strength cohorts.

## Acceptance Criteria

- [x] Immutable member and catalog contracts validate numeric evidence, policy fields, provenance, and content-derived identities.
- [x] Equal weights remain together while deterministic ranking produces four nonempty globe cohorts and inclusive tattoo eligibility.
- [x] A strict catalog snapshot and bounded bundle reject forged or incomplete content before atomic publication.
- [x] The real Ice catalog records all source, recipe, threshold, member, cohort, and claim-boundary evidence.

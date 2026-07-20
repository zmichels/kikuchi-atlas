---
id: KIKU-T041
type: task
title: Intake plagioclase, muscovite, and clinopyroxene references
status: done
parent: KIKU-F009
created: 2026-07-20
priority: P1
tags: [phase-intake, plagioclase, muscovite, clinopyroxene]
links:
  - ../atlas/PHASE_REGISTRY.yml
evidence:
  - ../../tests/unit/test_atlas.py
---

# KIKU-T041: Intake plagioclase, muscovite, and clinopyroxene references

## Description

Add three science-honest reference candidates to the initial browsing set:
intermediate plagioclase An52, 2M1 muscovite, and ambient diopside as the
first clinopyroxene. Preserve their source URLs, why each was selected, and
the promotion test required before any render or dictionary claim.

## Acceptance Criteria

- [x] Plagioclase is represented by an explicit An52 candidate rather than a generic family label.
- [x] Muscovite is represented by a named 2M1 reference with its mixed-occupancy source scope visible.
- [x] Clinopyroxene is represented by ambient stoichiometric diopside rather than an unspecified pyroxene.
- [x] Each candidate names a source, CIF, license, rationale, and promotion trigger.

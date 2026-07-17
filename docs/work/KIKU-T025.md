---
id: KIKU-T025
type: task
title: Define habit recipe and quartz reference source
status: ready
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- recipe
- cif
- provenance
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T025: Define habit recipe and quartz reference source

## Description

Define the immutable habit recipe, tracked public-domain quartz CIF, explicit
support distances, source hash, and content-derived recipe identity.

## Acceptance Criteria

- [ ] Quartz CIF bytes and public-domain provenance are tracked with the reviewed SHA-256.
- [ ] The recipe validates Miller convention, support distances, target millimetres, and optional FDM context.
- [ ] Recipe identity includes semantic content and CIF bytes without machine-local paths.

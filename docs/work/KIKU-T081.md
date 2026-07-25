---
id: KIKU-T081
type: task
title: Inventory requested mineral phases and source candidates
status: active
parent: KIKU-F031
children: []
created: 2026-07-24
priority: P1
tags: [atlas, source-intake, cod, mineralogy]
links:
  - ../atlas/REQUESTED_PHASE_EXPANSION.md
evidence:
  - ../../phases/calcite/source.yml
  - ../../phases/enstatite/source.yml
  - ../../phases/pyrope/source.yml
  - ../acceptance/pyrope-atlas-parity.md
  - ../atlas/REQUESTED_PHASE_EXPANSION.md
---

# KIKU-T081: Inventory requested mineral phases and source candidates

## Description

Resolve group names to exact endmembers or representative compositions and
select structure records with adequate coordinates, occupancies, thermal
factors, setting information, licensing, and citations.

## Acceptance Criteria

- [x] Existing requested coverage is identified without deleting or renaming
  retained phase records.
- [x] Missing minerals have located source candidates and scope notes.
- [ ] Candidate records are promoted or explicitly deferred after source-level
  validation.

## Pyrope promotion evidence

`COD-9000435` is now promoted as the 298.15 K pure-Mg pyrope endmember after
checksum, setting, site, occupancy, thermal-factor, direct-reflector parity,
and product-family checks. Its tracked derivative, source attribution, and
complete acceptance evidence are recorded in
`phases/pyrope/source.yml` and `docs/acceptance/pyrope-atlas-parity.md`.

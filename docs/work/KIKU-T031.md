---
id: KIKU-T031
type: task
title: Define relief globe recipes and source identity
status: ready
parent: KIKU-F005
created: '2026-07-17'
priority: P1
tags:
- relief
- recipe
- provenance
evidence:
- ../superpowers/plans/2026-07-17-spherical-intensity-relief-globe.md
---

# KIKU-T031: Define relief globe recipes and source identity

## Description

Define a strict, immutable relief-globe recipe whose semantic identity captures
the expected master product and every approved geometry, mapping, filter,
export, and advisory FDM setting without embedding local paths.

## Acceptance Criteria

- [ ] The canonical forsterite recipe loads with the approved source hashes, `80.0 mm` base diameter, `1.2 mm` outward relief, subdivision `7`, global `1/99` percentiles, gamma `1.0`, and `0.8 mm` spherical Gaussian FWHM.
- [ ] Unknown keys, malformed identities, booleans-as-numbers, non-finite values, and unsupported semantic choices fail closed with focused errors.
- [ ] Recipe IDs are deterministic, path-independent, and covered by focused unit tests and Ruff.

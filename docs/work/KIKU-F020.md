---
id: KIKU-F020
type: feature
title: Prove multi-orientation Ice Ih detector-to-dictionary recovery
status: done
parent: KIKU-E001
children:
  - KIKU-T065
created: 2026-07-21
priority: P0
tags: [ice-ih, dictionary, detector-geometry, orientation, recovery]
links:
  - ../dictionaries/ice-ih-flagship-design.md
  - ../acceptance/ice-ih-synthetic-detector-orientation-recovery.md
evidence:
  - ../../scripts/run_ice_ih_synthetic_detector_orientation_recovery.py
---

# KIKU-F020: Prove multi-orientation Ice Ih detector-to-dictionary recovery

## Description

Use the new master-to-detector and detector-to-partial-S2 primitives together
for several well-separated dictionary orientations. Preserve all inputs and
score records so the synthetic nature and the exact convention path remain
inspectable.

## Acceptance Criteria

- [x] A deterministic orientation-selection rule chooses a diverse subset of
  the published cache rather than manually favorable examples.
- [x] Every synthetic detector field uses the same declared geometry and
  covered-direction mask, then recovers its target cached entry first.
- [x] A compact visual proof shows both orientation-varied detector patterns
  and their candidate rankings with an explicit non-acquisition boundary.

## Completion Evidence

The `ice-ih-synthetic-detector-orientation-recovery-v0.1.0` bundle contains
four selected target entries; all four rank first with zero direct quaternion
error and coverage fixed at 308 of 1,946 directions.

---
id: KIKU-T025
type: task
title: Render bounded Ice Ih oxygen-sublattice proof
status: active
parent: KIKU-F004
created: 2026-07-14
priority: P1
tags: [ice-ih, hexagonal, kikuchipy, visual-review]
evidence:
  - ../acceptance/ice-ih-oxygen-sublattice.md
  - ../../phases/ice-ih/source.yml
  - ../../recipes/kinematical/ice-ih-oxygen-quiet-proof.yml
  - ../../tests/adapters/test_ice_ih_kinematical.py
  - ../../local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21/manifest.json
---

# KIKU-T025: Render bounded Ice Ih oxygen-sublattice proof

## Description

Use a cited low-temperature electron-diffraction structure to exercise the
kinematical pipeline with primitive hexagonal Ice Ih, explicitly limiting the
first proof to its fully occupied average oxygen sublattice.

## Acceptance Criteria

- [x] The tracked structure record verifies its derived CIF checksum, P 63/m m c setting, oxygen site, and omitted disordered hydrogen sites.
- [x] The phase adapter accepts identity and cyclic unsigned axis permutations without changing the accepted forsterite result.
- [x] The primitive-hexagonal fallback retains no centering restriction and lets the expanded-cell structure factor remove the forbidden 001 reflection.
- [x] One full-resolution `[001]` run emits the same quiet circular treatment and complete projection ledger.
- [ ] The user reviews the Ice quiet image and records whether it joins the curated aesthetic set.

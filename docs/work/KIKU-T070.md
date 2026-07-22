---
id: KIKU-T070
type: task
title: Render transparent Ice Ih photometric stress inputs
status: done
parent: KIKU-F024
created: 2026-07-22
priority: P1
tags: [ice-ih, stress-test, saturation, illumination, noise, visualization]
links:
  - ../acceptance/ice-ih-photometric-stress.md
evidence:
  - ../../scripts/run_ice_ih_photometric_stress.py
  - ../../tests/unit/test_ice_ih_photometric_stress.py
---

# KIKU-T070: Render transparent Ice Ih photometric stress inputs

## Description

Generate named, deterministic image transforms of the source detector and
measure their partial-S2 coarse-cache responses. Keep the transforms outside
the observation package's preprocessing contract.

## Acceptance Criteria

- [x] Every condition has a stored parameter record and a deterministic image
  realization.
- [x] A single sheet shows condition appearance, top candidate, score, and
  angular error with no blur.
- [x] Tests confirm stable seeded transforms and reject flat/non-finite inputs.

## Completion Evidence

The six-condition output preserves the Ice Ih coarse winner while quantifying
its score response; saturation is the strongest configured score reduction.

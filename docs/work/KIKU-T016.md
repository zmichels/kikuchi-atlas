---
id: KIKU-T016
type: task
title: Render Crisp Kinematical Figures and Selection Diagnostics
status: done
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [figures, diagnostics, spherical, svg]
evidence:
  - ../superpowers/specs/2026-07-13-band-aware-focused-and-diagrammatic-rendering-design.md
  - ../../tests/unit/test_kinematical_render.py
  - ../../local/visual-reviews/kinematical-development/
---

# KIKU-T016: Render Crisp Kinematical Figures and Selection Diagnostics

## Description

Render deterministic stereographic, spherical, and detector figures plus a
contact sheet comparing explicit reflection-selection thresholds. Promote the
user-selected quiet etched-master style while retaining the denser balanced
variant as a diagnostic.

## Acceptance Criteria

- [x] Geometry is never blurred, smoothed, generated, or repainted.
- [x] Scientific marks stay in projection space while labels and minimum strokes remain presentation-stable.
- [x] The comparison figure makes line density, master intensity, and detector consequences inspectable together.
- [x] `quiet` is the promoted etched-master style and `balanced` remains a retained density diagnostic.

## Development Figure Inventory

The bounded visual-review run used `half_size=256`, detector shape
`(384, 512)`, and `figure_size_px=1200`. Its uncommitted local inventory is:

- `kinematical-stereographic-bands.svg`
- `kinematical-spherical-bands.png`
- `kinematical-detector-overlay.png`
- `etched-master-balanced.png`
- `etched-master-quiet.png`
- `reflector-selection.png`

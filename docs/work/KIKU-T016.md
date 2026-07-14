---
id: KIKU-T016
type: task
title: Render Crisp Kinematical Figures and Selection Diagnostics
status: ready
parent: KIKU-F002
created: 2026-07-13
priority: P0
tags: [figures, diagnostics, spherical, svg]
evidence:
  - ../superpowers/specs/2026-07-13-band-aware-focused-and-diagrammatic-rendering-design.md
---

# KIKU-T016: Render Crisp Kinematical Figures and Selection Diagnostics

## Description

Render deterministic stereographic, spherical, and detector figures plus a
contact sheet comparing explicit reflection-selection thresholds. Promote the
user-selected quiet etched-master style while retaining the denser balanced
variant as a diagnostic.

## Acceptance Criteria

- [ ] Geometry is never blurred, smoothed, generated, or repainted.
- [ ] Scientific marks stay in projection space while labels and minimum strokes remain presentation-stable.
- [ ] The comparison figure makes line density, master intensity, and detector consequences inspectable together.
- [ ] `quiet` is the promoted etched-master style and `balanced` remains a retained density diagnostic.

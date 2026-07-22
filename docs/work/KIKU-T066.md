---
id: KIKU-T066
type: task
title: Compute and render raw Ice Ih detector line-Hough evidence
status: done
parent: KIKU-F021
created: 2026-07-21
priority: P1
tags: [ice-ih, hough, finite-difference, line-evidence, visualization]
links:
  - ../acceptance/ice-ih-detector-hough-diagnostic.md
evidence:
  - ../../src/kikuchi_lab/diagnostics/hough.py
  - ../../tests/unit/test_hough_diagnostic.py
---

# KIKU-T066: Compute and render raw Ice Ih detector line-Hough evidence

## Description

Implement a bounded, native-resolution image-space Hough diagnostic that
selects finite-difference detector edges, accumulates line hypotheses across a
named theta grid, and records both raw data and a visual bridge to the
detector pattern.

## Acceptance Criteria

- [x] Edge selection uses no blur and records its percentile threshold,
  retained-pixel count, and source image identity.
- [x] The Hough accumulator retains its theta/distance coordinate arrays and
  peak records rather than a display-only image.
- [x] The evidence clearly separates line hypotheses from reflector indexing,
  detector geometry, orientation solving, and acquired-pattern claims.

## Completion Evidence

The `ice-ih-detector-hough-diagnostic-v0.1.0` bundle contains all native
diagnostic arrays and the four-panel Hough-space image. Focused unit tests
exercise simple line inputs and invalid parameter bounds.

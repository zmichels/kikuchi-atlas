---
id: KIKU-F021
type: feature
title: Add a native-resolution Ice Ih detector Hough-space diagnostic
status: done
parent: KIKU-E001
children:
  - KIKU-T066
created: 2026-07-21
priority: P1
tags: [ice-ih, detector, hough, diagnostics, pattern-processing]
links:
  - ../acceptance/ice-ih-detector-hough-diagnostic.md
evidence:
  - ../../scripts/run_ice_ih_detector_hough_diagnostic.py
---

# KIKU-F021: Add a native-resolution Ice Ih detector Hough-space diagnostic

## Description

Create a source-bound image-space Hough accumulator for the checked Ice Ih
detector image. Make its edge selection, raw accumulator, and line hypotheses
visible without implying a phase/orientation solution or substituting it for
the spherical dictionary signal.

## Acceptance Criteria

- [x] A reusable diagnostic takes a finite detector image, applies only a
  native finite-difference gradient threshold, and retains named Hough peaks.
- [x] Unit tests cover horizontal/vertical line evidence and invalid
  configuration rejection.
- [x] A checksum-bearing local output keeps source, gradient, edge mask,
  accumulator, coordinates, peak records, figure, and nonclaims together.

## Completion Evidence

The Ice Ih source image retains 25,166 top-gradient pixels and produces a
5121 x 360 image-space accumulator. The visual proof connects its strongest
line hypotheses back to the original high-resolution detector pattern.

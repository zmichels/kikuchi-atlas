---
id: KIKU-T062
type: task
title: Render source-bound detector footprint on the Ice Ih S2 cache panel
status: done
parent: KIKU-F017
created: 2026-07-21
priority: P1
tags: [ice-ih, detector-geometry, gnomonic, spherical, verification]
links:
  - ../acceptance/ice-ih-dictionary-signal-space-bridge.md
evidence:
  - ../../src/kikuchi_lab/dictionary/signal_space_bridge.py
  - ../../tests/unit/test_signal_space_bridge.py
---

# KIKU-T062: Render source-bound detector footprint on the Ice Ih S2 cache panel

## Description

Convert gnomonic detector rays into unit sample-frame directions using the
declared upstream detector transform, then render and record the detector
boundary as a visual coverage overlay without introducing detector-intensity
resampling.

## Acceptance Criteria

- [x] A pure helper maps `(gy, gx)` detector rays through an orthonormal,
  right-handed sample-to-detector transform and rejects invalid geometry.
- [x] A unit test verifies the identity-frame ray mapping, source inventory,
  and geometry-only manifest record.
- [x] The Ice run recipe identity is checked against the source run manifest
  before the visual bridge is published.

## Completion Evidence

The bridge's 384 boundary directions and center ray are stored in the local
`v0.1.1` output record. Its exact recipe is provenance-bound and the footprint
is rendered behind—not substituted for—the cache signal samples.

---
id: KIKU-T061
type: task
title: Render and verify the Ice Ih detector-to-cache signal-space bridge
status: done
parent: KIKU-F016
created: 2026-07-21
priority: P1
tags: [ice-ih, dictionary, visualization, verification]
links:
  - ../acceptance/ice-ih-dictionary-signal-space-bridge.md
evidence:
  - ../../src/kikuchi_lab/dictionary/signal_space_bridge.py
  - ../../tests/unit/test_signal_space_bridge.py
---

# KIKU-T061: Render and verify the Ice Ih detector-to-cache signal-space bridge

## Description

Create a deterministic local proof artifact that makes the current engine's
signal-space contract legible: display the human-recognizable detector image
and master while clearly separating them from the sparse cache vector used for
canonical-S2 ranking.

## Acceptance Criteria

- [x] Source images are checked against the authoritative run manifest before
  a bridge is published.
- [x] The cache panel uses the package's exact directions and validation
  signal, verifies vector width and unit directions, and labels its matching
  normalization.
- [x] A failing test proves width mismatch is rejected, and a passing test
  proves the bridge record contains checked source and output inventories.

## Completion Evidence

The renderer uses the checked `kinematical-run-8e0fa453f0869a21` detector and
master PNGs and Ice Ih `v0.1.3` package fixture. Its output is intentionally a
human explanation of existing representations, not a new detector projection,
Hough transform, or indexing result.

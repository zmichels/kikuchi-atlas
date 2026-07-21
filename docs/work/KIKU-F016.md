---
id: KIKU-F016
type: feature
title: Make Ice Ih dictionary signal spaces visually interpretable
status: done
parent: KIKU-E001
children:
  - KIKU-T061
created: 2026-07-21
priority: P1
tags: [ice-ih, dictionary, visualization, provenance, claim-boundary]
links:
  - ../dictionaries/ice-ih-flagship-design.md
  - ../acceptance/ice-ih-dictionary-signal-space-bridge.md
evidence:
  - ../../scripts/render_ice_ih_dictionary_signal_space_bridge.py
---

# KIKU-F016: Make Ice Ih dictionary signal spaces visually interpretable

## Description

Provide a source-bound visual bridge between the Ice Ih kinematical
detector-plane image, its two-hemisphere stereographic master, and the sparse
sample-frame S2 vector that the present dictionary ranker actually compares.
The bridge must explain the representation boundary rather than suggesting
that the cache scatter is a detector pattern or Hough-space transform.

## Acceptance Criteria

- [x] A single rendered figure shows the detector projection, master field,
  and exact cache-signal representation with their roles labeled.
- [x] The output record binds every displayed source input and the exact
  dictionary manifest identity with checksums.
- [x] The artifact and documentation explicitly state that Hough/Radon space,
  a detector-to-S2 adapter, and acquired-EBSD validation are not implemented.

## Completion Evidence

`scripts/render_ice_ih_dictionary_signal_space_bridge.py` verifies the
immutable Ice Ih `v0.1.3` dictionary and checks the source run's detector and
master PNG hashes before atomically publishing the local bridge bundle. The
unit tests cover a valid source-bound publication and a mismatched cache-input
width rejection.

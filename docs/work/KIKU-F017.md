---
id: KIKU-F017
type: feature
title: Show declared Ice Ih detector coverage in spherical dictionary context
status: done
parent: KIKU-E001
children:
  - KIKU-T062
created: 2026-07-21
priority: P1
tags: [ice-ih, dictionary, detector-geometry, visualization, provenance]
links:
  - ../acceptance/ice-ih-dictionary-signal-space-bridge.md
evidence:
  - ../../scripts/render_ice_ih_dictionary_signal_space_bridge.py
---

# KIKU-F017: Show declared Ice Ih detector coverage in spherical dictionary context

## Description

Extend the Ice Ih signal-space bridge with an exact geometry-only detector
footprint on the sample-frame sphere. This lets a reader see the partial
gnomonic field of view relative to the full-sphere cache without mistaking the
overlay for an intensity projection or an acquired-data indexer.

## Acceptance Criteria

- [x] The overlay is derived from the source run's exact checked detector
  recipe, PC convention, shape, and tilt values.
- [x] The bridge records its boundary directions and projection-center ray in
  sample coordinates, together with a source hash for the detector recipe.
- [x] The artifact labels the footprint as geometry only and explicitly
  excludes detector-intensity resampling.

## Completion Evidence

The `v0.1.1` bridge maps the detector boundary through
`kikuchipy.EBSDDetector.to_gnomonic_coords` and its explicit
`sample_to_detector` transform. The result is a teal footprint and center ray
over the canonical S2 cache panel; it does not alter or sample the detector
image.

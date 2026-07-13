# Orientations from EBSD Maps

- Status: Incubating
- Boundary: imported orientation requests, not map processing or indexing

## Motivation

Rendering a pattern for an orientation selected from real indexed EBSD data
would connect the simulator to measured microstructures, enable map-guided
science-art, and provide a useful seam for future ebsdx collaboration. The
import must retain coordinate-system, phase, calibration, and provenance
semantics rather than accepting bare Euler triples.

## Current evidence

- The public orientation contract is an active crystal-to-sample Bunge ZXZ
  rotation in degrees with EDAX-TSL `[RD, TD, ND]` sample axes
  ([KIKU-T004](../work/KIKU-T004.md)).
- Candidate and selection records prove stable orientation identities and an
  externally verified human-decision lineage ([ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md)
  and [KIKU-T009](../work/KIKU-T009.md)).
- The repository currently has no EBSD map reader, map-coordinate model,
  quality-field contract, or phase-association importer.

## Dependencies

- A small, licensed indexed-map fixture with known vendor, Euler, sample-frame,
  phase, and spatial-axis semantics.
- An explicit import adapter that converts external orientations into the
  project contract and records the conversion.
- A selection model for point, grain, representative orientation, or bounded
  subset provenance.

## Unresolved questions

- Which input should establish the first contract: vendor files, a portable
  exchange representation, or an ebsdx-owned dataset product?
- How should unindexed, mixed-phase, low-confidence, and pseudosymmetric points
  be represented?
- Should detector geometry come from acquisition metadata or a separate
  simulation recipe when rendering a map orientation?

## Linked decisions and experiments

- [ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md) fixes the
  current frame and symmetry-reduction semantics.
- [KIKU-T009](../work/KIKU-T009.md) demonstrates immutable orientation-choice
  evidence without importing map state.
- [ebsdx integration](ebsdx-integration.md) records the related product-boundary
  questions.

## Promotion trigger

Promote when one redistributable indexed-map fixture and its complete orientation, phase, and sample-frame semantics can be round-tripped into the project orientation contract.

## Present non-goals

- Indexing raw EBSD patterns or reindexing a map.
- Grain reconstruction, segmentation, or map cleanup.
- Assuming vendor Euler angles already use the project frame.
- Production integration with ebsdx or ebsdx-rs.

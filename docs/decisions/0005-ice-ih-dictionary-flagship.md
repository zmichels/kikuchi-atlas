# ADR 0005: Ice Ih is the flagship scientific dictionary phase

- Status: Accepted
- Date: 2026-07-20
- Work item: [KIKU-F013](../work/KIKU-F013.md)
- Interchange contract: [`ebsdx-rs` spherical dictionary resource contract](../../../ebsdx-rs/docs/spherical-dictionary-resource-contract.md)

## Context

The initial forsterite S2 fixture proves a portable resource contract, but it
is deliberately too small and detector-agnostic to be a practical indexing
resource. The next scientific slice should prioritize a phase where rapid,
open, reproducible indexing could be unusually valuable. Ice Ih is the
ordinary crystalline ice phase for the intended near-ambient use case and
already has a cited, provenance-bearing, oxygen-sublattice kinematical master
in this repository.

The source model is deliberately bounded to the average oxygen sublattice in
`P 63/m m c` (No. 194). It does not assert a hydrogen-ordered structure, a
general ice polymorph classifier, an acquired-pattern calibration, or a
vendor-specific detector model.

## Decision

Ice Ih becomes the flagship scientific dictionary phase. The first useful
resource is a two-level spherical dictionary rather than a giant opaque stack
of detector images:

1. a compact, symmetry-reduced, 5-degree SO(3) candidate cache for fast
   ranking; and
2. the checked 1025-by-1025 two-hemisphere master for deterministic local
   candidate refinement.

The coarse cache uses the `6/mmm` fundamental region and a 5-degree spherical
sample grid. The expected initial shape is 13,155 orientations by 1,946 sample
directions. Every cached row is generated from the canonical raw master with
only declared interpolation, mean-centering, and L2 normalization. The source
master, cache recipe, sampling methods, symmetry, quaternions, byte hashes,
and matching transforms are retained in the package.

The first matcher accepts an already spherical observed signal. A
detector-to-sphere adapter is a distinct later boundary, because its geometry,
pattern-center convention, masks, background correction, and resampling must
be supplied rather than guessed. The first acceptance proof therefore uses
held-out synthetic signals and reports retrieval and angular diagnostics, not
experimental accuracy.

## Consequences

- The package can support fast candidate retrieval without tying the canonical
  physics to one microscope or camera.
- A later `ebsdx` or `ebsdx-rs` adapter can consume the same resource once its
  observed-pattern preprocessing and detector geometry are explicit.
- Ice Ic/stacking disorder, amorphous ice, high-pressure polymorphs, and
  hydrogen-order effects remain named exclusions rather than hidden failure
  modes.
- Forsterite stays as a compact contract fixture and comparison phase; it no
  longer defines the flagship scientific priority.

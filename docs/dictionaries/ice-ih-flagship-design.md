# Ice Ih flagship spherical dictionary design

Status: accepted initial design, 2026-07-20.

## Objective

Deliver a practical, inspectable Ice Ih candidate-search resource that is fast
enough to use interactively, preserves the source master at full resolution,
and can later be connected to an explicit detector adapter. It is not an
experimental EBSD-indexing benchmark yet.

## Scientific identity

- Phase: Ice Ih, average oxygen sublattice.
- Setting: `P 63/m m c` (No. 194), point group `6/mmm`.
- Structural source: `phases/ice-ih/source.yml` (`COD-1572233-O-sublattice`).
- Physics source: the checked 20 keV kinematical stereographic master from
  `recipes/kinematical/ice-ih-oxygen-quiet-proof.yml`.
- Exclusions: hydrogen disorder/order, Ice Ic and stacking disorder, amorphous
  ice, high-pressure ice polymorphs, and detector/acquisition calibration.

## Two-level resource

| Layer | Purpose | Initial contract |
| --- | --- | --- |
| Canonical master | High-fidelity signal and local refinement | Raw 1025x1025 upper/lower stereographic master; bilinear sampling; no display tone map. |
| Candidate cache | Fast first-pass ranking | `6/mmm` cubochoric SO(3) fundamental grid at 5 degrees, sampled on a 5-degree S2 grid, row mean-centered and L2-normalized. |

The initial expected cache is 13,155 orientation quaternions and 1,946 S2
sample directions. It occupies roughly 102 MiB as contiguous float32 scores,
which is small enough to memory-map while retaining a simple, auditable CPU
dot-product path. Compact distribution storage may be added later only if its
numeric effect is measured and recorded.

## Matching interface

The first matcher receives a spherical observed signal sampled on the exact
published S2 directions. It rejects mismatched direction grids, non-finite
values, and unnamed transforms. It mean-centers and L2-normalizes the input,
then computes cosine similarity against the contiguous candidate matrix.

The result records the top candidates, their canonical active
crystal-to-sample `w,x,y,z` quaternions, the score metric, source dictionary
identity, and the observed-signal preprocessing identity. A later detector
adapter must be the producer of that observed spherical signal; it is not
silently folded into candidate ranking.

## Refinement and validation

The coarse winner is only a candidate. Refinement samples the full canonical
master around the best candidate with a separately declared local SO(3) grid.
The first proof holds out synthetic orientations that are not cache entries,
checks that the retained candidate set brackets the known orientation, and
records score and angular-error diagnostics. It will not state an experimental
indexing accuracy until declared acquired reference patterns are available.

## Acceptance gates

1. Every matrix row is reproducible from the verified Ice master and an
   explicit orientation and S2 sampling method.
2. The package includes manifest, entries, source hashes, cache, LICENSE,
   CITATION, checksum inventory, and a deterministic synthetic validation.
3. A held-out synthetic signal identifies a nearby coarse candidate and local
   refinement improves its angular error.
4. The resource is verified independently of the Atlas and clearly labels its
   non-calibration boundary.

The accompanying `scripts/run_ice_ih_synthetic_recovery.py` seals the first
held-out recovery proof as a checksum-bearing local bundle with a visual
diagnostic. It is intentionally separate from the immutable v0.1.0 cache;
future resource versions will carry this validation evidence inside the package
itself.

# ADR 0002: Forsterite Proof Candidate Set

- Status: Accepted
- Date: 2026-07-13
- Work item: [KIKU-T007](../work/KIKU-T007.md)
- Recipe: [forsterite-candidates.yml](../../recipes/proof/forsterite-candidates.yml)

## Context

The first proof comparison needs enough orientation variety to make an
informed visual choice without turning the milestone into an orientation-space
survey. Forsterite is orthorhombic `Pnma` (No. 62) with point group `mmm`, so
different Bunge triples can describe crystal-symmetry-equivalent physical
orientations. Retaining such duplicates would spend rendering time on the same
view and could make a visual selection appear more strongly supported than it
is.

The public project convention is an active crystal-to-sample rotation expressed
as Bunge ZXZ Euler angles in degrees. Sample axes remain fixed in EDAX-TSL
`[RD, TD, ND]` order. Reduction must preserve that convention at the project
boundary even though orix represents orientations using its passive
sample-to-crystal convention.

## Decision

The accepted recipe contains twelve explicitly ordered candidates:

1. `[001]` at 0 and 35 degree in-plane rolls;
2. `[100]` at 0 and 40 degree rolls;
3. `[010]` at 15 and 55 degree rolls; and
4. one view each around `[110]`, `[101]`, `[011]`, `[111]`, `[210]`, and
   `[012]` with deliberately varied in-plane rolls.

Zone directions are metric-aware direct-lattice directions using the verified
standard-Pnma simulation cell lengths `a = 10.207`, `b = 5.980`, and
`c = 4.756` angstrom. These are intentionally in the repository's transformed
Pnma axis order, not the differently ordered source-Pbnm CIF axes. Each is
aligned to sample ND before its stated roll is applied. Executable tests
verify the rounded explicit Euler triples retain that alignment within
`1e-6` degrees. Every candidate records both its zone-axis intent and a visual
composition hypothesis; those hypotheses guide comparison but do not assert
which orientation will produce the final artwork.

Symmetry reduction is contained in the orientation helper. It converts each
project-owned active crystal-to-sample `Orientation` to the inverse passive
sample-to-crystal orix orientation, assigns orix `D2h` (`mmm`) crystal
symmetry, and uses orix disorientation. In that passive representation,
crystal symmetry acts on the left and the sample frame remains fixed. No sample
symmetry is introduced. A regression test demonstrates both sides of this
boundary: a crystal twofold-equivalent representation reduces to zero while a
one-degree sample-frame rotation remains one degree.

Two candidates are considered equivalent when their reduced disorientation is
at most `0.01` degrees. The loader rejects a set containing such a pair. For
the accepted recipe, all 66 unordered pairs pass; the closest pair is
`fo-110-r010` versus `fo-111-r000` at approximately `24.0515` degrees. Stable
recipe order, explicit candidate IDs, content-derived orientation IDs, and the
content-derived candidate-set ID make the exact comparison set serializable
and reproducible. The accepted set ID is
`candidate-set-bf329b87e5427ecd`.

This is deliberately a bounded, non-exhaustive proof set. It is not a uniform
SO(3) sample, an inverse-pole-figure fundamental-zone grid, an optimization
result, or evidence that untested orientations are inferior. Phase-general
sampling and denser local exploration belong after the first proof comparison.

## Consequences

- Task 8 can render one deterministic order without importing orix types into
  its workflow contract.
- Every displayed candidate has a documented scientific and compositional
  reason for inclusion.
- Changing an angle, intent, lattice metric, order, or tolerance changes the
  candidate-set identity.
- The final orientation choice remains a separate human decision with its own
  evidence; this ADR only accepts the comparison population.
- Future phase-general work must choose and document its own symmetry and
  sampling strategy rather than treating this bounded set as exhaustive.

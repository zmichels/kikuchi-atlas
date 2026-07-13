# Orientation-Variety Gallery

- Status: Incubating
- Boundary: a later curated product, not an extension of the first final gate

## Motivation

Forsterite and later phases can support visually and scientifically distinct
views beyond the selected `[011]` composition. A gallery could expose symmetry,
zone-axis variety, and compositional choices while also becoming a stable
regression set for projection and processing.

## Current evidence

- The bounded twelve-orientation recipe has explicit active crystal-to-sample
  Bunge angles, direct-lattice zone directions, and `mmm` symmetry reduction
  ([ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md)).
- The proof workflow renders a deterministic contact sheet without claiming an
  exhaustive SO(3) sample ([KIKU-T008](../work/KIKU-T008.md)).
- The user selected `fo-011-phi1-045` through an immutable, proof-scoped
  decision lineage ([KIKU-T009](../work/KIKU-T009.md)).

## Dependencies

- Completion of the single-orientation production and visual-acceptance gate.
- A documented sampling purpose: curated zone axes, a local neighborhood,
  inverse-pole-figure coverage, or another explicitly bounded strategy.
- Gallery-level compute budgets, layout identity, captions, and per-image
  provenance.

## Unresolved questions

- Should the first gallery stay with forsterite or couple phase and orientation
  variety?
- How should crystallographic coverage and visual diversity be balanced without
  disguising curation as uniform sampling?
- Which processing parameters should be shared across all views, and which may
  vary with recorded justification?

## Linked decisions and experiments

- [ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md) records the
  current bounded population and its non-exhaustive meaning.
- [KIKU-T008](../work/KIKU-T008.md) links the authoritative proof contact sheet.
- [KIKU-T009](../work/KIKU-T009.md) records why one candidate was promoted for
  the first final render.

## Promotion trigger

Promote after the first production pattern is accepted and a reviewed gallery-sampling contract names its scientific coverage and compute bound.

## Present non-goals

- Reopening or weakening the accepted first orientation choice.
- Calling the existing twelve candidates exhaustive or uniformly distributed.
- Producing a phase-general gallery before phase-general validation exists.
- Adding gallery completion to the exceptional-forsterite milestone.

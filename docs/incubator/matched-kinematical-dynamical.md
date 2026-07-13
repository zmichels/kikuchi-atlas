# Matched Kinematical and Dynamical Comparison

- Status: Incubating
- Boundary: diagnostic companion capability, not a replacement source model

## Motivation

A deliberately matched pair could expose which bands, nodes, asymmetries, and
intensity relationships arise from dynamical physics and which remain legible
in a simpler geometrical or kinematical construction. That comparison could be
useful for teaching, science-art, processing diagnostics, and eventually
engine validation, provided the two products are never presented as physically
equivalent.

## Current evidence

- The ebsdsim adapter already supplies an authoritative dynamical master behind
  a source-neutral canonical product ([KIKU-T003](../work/KIKU-T003.md)).
- Detector geometry, orientation frames, processing, diagnostics, and bundles
  are explicit project-owned contracts ([KIKU-T004](../work/KIKU-T004.md),
  [KIKU-T005](../work/KIKU-T005.md), and
  [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)).
- The proof comparison demonstrates matched rendering across a bounded
  orientation set, but the repository contains no kinematical source or band
  renderer ([KIKU-T008](../work/KIKU-T008.md)).

## Dependencies

- A named canonical contract for a kinematical or diagrammatic product whose
  semantics cannot be confused with dynamical intensity.
- One shared phase, orientation, detector geometry, resolution, and display
  mapping for fair comparisons.
- Diagnostic measures that separate geometry agreement from intensity-model
  agreement.

## Unresolved questions

- Should the simpler branch generate band envelopes from reflectors, project a
  kinematical sphere, or expose both representations?
- Which normalization preserves meaningful comparison without implying that
  arbitrary kinematical amplitudes match dynamical intensities?
- Which discrepancies are expected model behavior, and which indicate frame,
  detector, or implementation errors?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)
  defines immutable identity and branch-lineage evidence.
- [ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md)
  defines the current orientation and symmetry convention.
- The real proof run documented by [KIKU-T008](../work/KIKU-T008.md) is the
  available dynamical comparison baseline.

## Promotion trigger

Promote when one scientifically labeled kinematical method can be rendered against the same canonical phase, orientation, and detector contract as a retained dynamical baseline.

## Present non-goals

- Claiming kinematical intensities are quantitatively interchangeable with
  dynamical intensities.
- Replacing ebsdsim in the accepted forsterite workflow.
- Automated orientation selection, indexing, or aesthetic ranking.
- Adding a second final product to milestone-one acceptance.

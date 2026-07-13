# EMsoft Cross-Validation

- Status: Incubating
- Boundary: independent comparison evidence, not a silent backend swap

## Motivation

An EMsoft-family dynamical result could test whether phase, frame, detector,
and large-scale intensity structures agree across independent implementations.
That evidence would strengthen scientific confidence and help distinguish
project-adapter mistakes from engine-specific numerical behavior.

## Current evidence

- ebsdsim is the accepted milestone source, preserved as untouched native NPZ
  plus canonical product and manifest ([KIKU-T003](../work/KIKU-T003.md)).
- Canonical products and project-owned projection recipes provide a possible
  comparison boundary without leaking either engine's native objects
  ([KIKU-T002](../work/KIKU-T002.md) and
  [KIKU-T004](../work/KIKU-T004.md)).
- A higher-control ebsdsim run remained GPU-active for about 1,175 seconds and
  was deliberately stopped without publication; this is resource-planning
  evidence, not an EMsoft result ([KIKU-T008](../work/KIKU-T008.md)).
- The repository has not installed, built, or executed EMsoftOO and contains no
  EMsoft output fixture.

## Dependencies

- A reproducible EMsoftOO or compatible EMsoft execution path and a
  license-cleared output fixture.
- Matched phase structure, voltage, energy integration, Bethe/scattering
  controls where meaningful, hemisphere convention, and detector geometry.
- A comparison protocol that separates coordinate, sampling, normalization,
  and model differences.

## Unresolved questions

- Which EMsoft repository and output format provide the smallest credible
  cross-validation slice on Apple Silicon?
- Which settings can truly be matched with ebsdsim, and which must remain
  explicitly non-equivalent?
- Should acceptance compare reconstructed master patterns, detector patterns,
  band locations, statistics, or several labeled levels?

## Linked decisions and experiments

- [KIKU-T003](../work/KIKU-T003.md) records the source transform and local Metal
  simulator evidence.
- [KIKU-T008](../work/KIKU-T008.md) records the proof master and aborted
  high-control performance observation.
- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) supplies
  comparison-friendly immutable identities and declared exclusions.

## Promotion trigger

Promote when one bounded EMsoft output can be generated or admitted with enough matched metadata to define an honest cross-engine comparison protocol.

## Present non-goals

- Requiring EMsoftOO for the accepted milestone workflow.
- Declaring pixel equality across different dynamical engines.
- Hiding unmatched simulation settings behind display normalization.
- Replacing ebsdsim without reviewed comparative evidence.

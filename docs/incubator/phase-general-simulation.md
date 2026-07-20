# Phase-General Simulation

- Status: Promoted into bounded proofs via [KIKU-F004](../work/KIKU-F004.md)
- Boundary: repeatable phase onboarding, not a claim of universal support

## Motivation

The companion becomes more scientifically useful when a new phase can be
added through validated structure evidence and the same stable downstream
contracts. Extending honestly requires preserving phase-specific setting,
symmetry, site, energy, and simulator limitations rather than treating
forsterite metadata as a generic template.

## Current evidence

- The canonical master product and projection boundary are source- and
  phase-metadata driven ([KIKU-T002](../work/KIKU-T002.md) and
  [KIKU-T004](../work/KIKU-T004.md)).
- Forsterite exposed a material setting issue: COD `P b n m` had to be
  transformed explicitly into ebsdsim's standard `P n m a`, with sites and
  multiplicities revalidated ([KIKU-T003](../work/KIKU-T003.md)).
- Candidate reduction is explicitly tied to forsterite `mmm` symmetry and is
  not phase-general ([ADR 0002](../decisions/0002-forsterite-proof-candidate-set.md)).
- Ice Ih now exercises an identity `P 63/m m c` setting, a non-orthogonal
  hexagonal metric, primitive-hexagonal reflection handling, and an explicit
  oxygen-only model boundary ([KIKU-T025](../work/KIKU-T025.md)).

## Dependencies

- A phase-onboarding contract for source license, checksum, citation, setting,
  cell transform, sites, occupancies, displacement factors, and symmetry.
- Phase-specific admissibility tests at the ebsdsim and projection boundaries.
- A second additional openly redistributable structure chosen to exercise a
  different pathway from both forsterite and Ice Ih.

## Unresolved questions

- Which phase should follow Ice Ih to exercise a meaningfully different
  symmetry, chemistry, or source-setting pathway?
- Which simulator limitations can be validated generically and which require a
  per-phase policy?
- How should phase-specific orientation sampling and detector recipes be
  registered without hard-coded branches?

## Linked decisions and experiments

- [KIKU-T003](../work/KIKU-T003.md) records the authoritative source transform,
  Metal smoke test, and failure-on-ambiguity policy.
- [KIKU-T004](../work/KIKU-T004.md) demonstrates a source-neutral downstream
  projection seam.
- The [approved design](../superpowers/specs/2026-07-12-kikuchi-companion-design.md)
  makes additional phases an explicit post-milestone direction.

## Promotion evidence

The Ice Ih oxygen-sublattice proof satisfies the original promotion trigger:
it is openly sourced, structurally different from forsterite, bounded by an
explicit approximation, and has reflection and visual validation evidence.
Promotion creates an active proof series; it does not imply universal phase
support.

## Present non-goals

- Advertising arbitrary-CIF or all-phase compatibility.
- Bulk-downloading structures or master-pattern datasets.
- Generalizing away phase-specific warnings and transforms.
- Adding any second phase to milestone-one acceptance.

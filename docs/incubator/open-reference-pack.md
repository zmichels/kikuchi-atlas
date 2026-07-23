# Open Kikuchi Reference Pack

- Status: Incubating
- Boundary: a reproducible acquired-pattern reference contract, not a new
  simulator, file format, or general indexing benchmark

## Motivation

Kikuchi Atlas can be more useful than a catalogue of attractive master-pattern
images if a small number of phase resources are joined to real detector
observations, declared processing and projection semantics, and a rerunnable
baseline. The purpose is to let an experimentalist, method developer, or
downstream project answer exactly what was compared and how—not merely to
download another image.

## Current evidence

- The [needs and gap review](../strategy/2026-07-23-open-kikuchi-reference-pack-needs-gap-review.md)
  identifies a contract layer between established simulation/indexing tools and
  acquired EBSD observations.
- The local Ice Ih virtual-camera packages prove that one canonical spherical
  dictionary can be observed through multiple named geometry adapters while
  preserving each adapter's coverage mask. They remain synthetic evidence, not
  acquired-pattern validation.
- The project-local ebsdx-rs spherical-dictionary resource contract supplies a
  compatible downstream framing for canonical resources, observation-specific
  adapters, and declared provenance.

## Dependencies

- A candidate public dataset with clear access and redistribution terms.
- Retained raw values or a durable legal pointer to them.
- Detector geometry/calibration metadata, or explicit representation of what
  is unknown.
- A cited phase record and reproducible master-resource recipe.
- One baseline method capable of producing a versioned golden result.

## Unresolved questions

- Which public Ni or Si dataset exposes enough calibration semantics for the
  first pack without importing vendor-specific ambiguity?
- Should a v0.1 pack distribute raw patterns, a stable external pointer, or
  both?
- What result should be treated as the first golden baseline: a known
  single-crystal orientation, a constrained phase/orientation candidate list,
  or a deliberately narrow detector-fit exercise?
- Which sidecar form best complements existing HDF5-based archives without
  inventing a competing container format?

## Linked decisions and experiments

- [Detector and acquisition model](detector-acquisition-model.md) preserves
  instrument-response semantics as a separate concern.
- [Pattern-processing contracts](pattern-processing-contracts.md) preserves
  reusable processing boundaries.
- [Independent engine](independent-engine.md) remains deferred until reference
  packs expose a bounded, validated missing component.
- [KIKU-F026](../work/KIKU-F026.md) records the synthetic Ice Ih
  multi-geometry transfer proof.

## Promotion trigger

Promote when one candidate dataset passes the written rights, raw-data,
geometry/calibration, phase/master-provenance, baseline-result, and user-scope
gates in the needs and gap review.

## Present non-goals

- Rewriting or forking kikuchipy, EMsoft, or PyEBSDIndex.
- Publishing a broad master-pattern database without observation semantics.
- Calling the current synthetic Ice Ih package an acquired-data benchmark.
- Training or releasing a general ML indexing model.
- Claiming vendor compatibility before a specific format path is tested.

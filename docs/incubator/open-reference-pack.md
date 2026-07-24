# Open Kikuchi Reference Pack

- Status: First lightweight implementation released
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
- The [Ni 24 dB pack](../reference-packs/ni-gain24db-calibration-hough-v0.1.md)
  now releases a source-bound, checksum-bearing seven-pattern Hough baseline
  through an upstream pointer, strict source verifier, tracked recipe, and
  local evidence runner. It is not an independent orientation-truth benchmark.

## Dependencies

- A candidate public dataset with clear access and redistribution terms.
- Retained raw values or a durable legal pointer to them.
- Detector geometry/calibration metadata, or explicit representation of what
  is unknown.
- A cited phase record and reproducible master-resource recipe.
- One baseline method capable of producing a versioned golden result.

## Unresolved questions

- Does the initial public release need independent orientation truth, or is a
  clearly labeled source-bound calibration baseline useful enough on its own?
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
- [KIKU-F028](../work/KIKU-F028.md) records the acquired Ni calibration
  intake and source-bound baseline.
- [KIKU-F029](../work/KIKU-F029.md) records the approved v0.1 pointer,
  inventory, verifier, and reproduction release.

## Promotion trigger

Promote when a second acquired phase pack has an independently bounded truth
or cross-instrument test that can test whether the contract is useful beyond a
single source-bound Ni reproduction.

## Present non-goals

- Rewriting or forking kikuchipy, EMsoft, or PyEBSDIndex.
- Publishing a broad master-pattern database without observation semantics.
- Calling the current synthetic Ice Ih package an acquired-data benchmark.
- Rebranding the Ni v0.1 source-bound baseline as an independent truth set.
- Training or releasing a general ML indexing model.
- Claiming vendor compatibility before a specific format path is tested.

# ebsdx and ebsdx-rs Integration

- Status: Incubating
- Boundary: product-level interoperability first, plugin architecture later

## Motivation

Kikuchi Lab products could eventually support ebsdx and ebsdx-rs with
simulation, selected-orientation rendering, processing experiments, regression
fixtures, or science-art exports. The safest path is an explicit data and
capability boundary rather than direct dependence on this repository's CLI or
upstream kikuchipy objects.

## Current evidence

- Project-owned canonical master, detector, recipe, provenance, identity, and
  bundle contracts keep ebsdsim and kikuchipy types behind adapters
  ([approved design](../superpowers/specs/2026-07-12-kikuchi-companion-design.md)).
- Final rendering can be driven from immutable selection, source, detector, and
  processing records and then reproduced from its manifest
  ([KIKU-T010](../work/KIKU-T010.md)).
- No ebsdx or ebsdx-rs code, file format, API, ownership boundary, or plugin
  lifecycle has been evaluated in this repository.

## Dependencies

- A jointly reviewed interchange use case and the smallest product contract
  needed by each host.
- Exact phase, orientation, detector, array-layout, and provenance mappings.
- A compatibility/versioning policy that allows either repository to evolve
  without sharing internal Python or Rust types.

## Unresolved questions

- Is the first useful seam a file bundle, command protocol, library API,
  service, or host-owned plugin adapter?
- Which side owns orchestration, storage, caching, cancellation, and progress?
- Can one language-neutral schema serve both Python ebsdx and Rust ebsdx-rs
  without flattening scientific semantics?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) defines
  the current portable artifact inventory and lineage.
- [KIKU-T004](../work/KIKU-T004.md) demonstrates containment of an upstream
  projection implementation behind a project boundary.
- [Pattern-processing contracts](pattern-processing-contracts.md) records the
  prerequisite engine-neutral processing questions.

## Promotion trigger

Promote when one concrete ebsdx or ebsdx-rs workflow names a minimal language-neutral product exchange and has an owner-approved integration boundary.

## Present non-goals

- Modifying either ebsdx repository from this incubator record.
- Committing to a plugin ABI, network service, or UI surface.
- Making Kikuchi Lab the owner of ebsdx datasets or application state.
- Adding integration delivery to the forsterite milestone.

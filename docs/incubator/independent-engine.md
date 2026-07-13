# Independent Kikuchi Simulation or Processing Engine

- Status: Incubating
- Boundary: a possible later project informed by evidence, not the current architecture

## Motivation

Building the companion around stable scientific contracts creates a practical
way to learn which capabilities, semantics, diagnostics, and performance
boundaries matter. That evidence may eventually justify an independent engine
for simulation, processing, or both, with ebsdsim, kikuchipy, EMsoft, and open
datasets serving as references rather than undocumented templates.

## Current evidence

- The approved architecture deliberately keeps upstream implementations behind
  project-owned source, canonical-product, projection, processing, artifact,
  and decision boundaries
  ([approved design](../superpowers/specs/2026-07-12-kikuchi-companion-design.md)).
- Milestone work now provides executable evidence for structure validation,
  source ingestion, frame conversion, detector projection, processing lineage,
  artifact identity, selection decisions, and exact CPU reproduction
  ([KIKU-T003](../work/KIKU-T003.md) through
  [KIKU-T010](../work/KIKU-T010.md)).
- Only one phase, one dynamical source implementation, one projection
  implementation, and one selected workflow have been exercised; this is not
  enough evidence to specify a credible independent engine.

## Dependencies

- Multiple independently generated validation fixtures with license and
  provenance suitable for long-term regression use.
- Clear separation of physical simulation, projection, processing, indexing,
  and host integration responsibilities.
- Documented accuracy, performance, precision, platform, and maintenance goals.
- A license and clean-room review before reimplementing behavior learned from
  upstream projects.

## Unresolved questions

- Is the first independent boundary most valuable in processing, projection,
  master-pattern simulation, or shared contracts?
- What physical fidelity and validation corpus would make an independent
  simulator scientifically defensible?
- Which implementation language and acceleration model best serve ebsdx,
  ebsdx-rs, notebook, CLI, and future native surfaces without UI-owned state?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) records
  the current engine-neutral artifact and lineage spine.
- [Matched kinematical and dynamical](matched-kinematical-dynamical.md),
  [pattern-processing contracts](pattern-processing-contracts.md), and
  [EMsoft cross-validation](emsoft-cross-validation.md) identify evidence that
  would narrow the first independent boundary.
- [KIKU-T003](../work/KIKU-T003.md) and
  [KIKU-T004](../work/KIKU-T004.md) document concrete upstream seams rather
  than treating their behavior as project-owned.

## Promotion trigger

Promote when comparative evidence across at least two implementations identifies one bounded component whose independent contract, validation corpus, and maintenance purpose are clear.

## Present non-goals

- Forking, cloning, or rewriting ebsdsim, kikuchipy, or EMsoft now.
- Claiming single-phase milestone evidence defines a general simulator.
- Designing a monolithic simulation-processing-indexing application.
- Moving the current companion milestone onto an unvalidated engine.

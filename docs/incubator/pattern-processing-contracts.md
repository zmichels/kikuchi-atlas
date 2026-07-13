# Reusable EBSD-Pattern Processing Contracts

- Status: Incubating
- Boundary: a reusable processing core, not a universal correction recipe

## Motivation

The named processing graph already separates acquisition correction,
normalization, local contrast, detail, sharpening, tone mapping, and
downsampling. Generalizing those boundaries could support measured EBSD
patterns, simulation comparisons, ebsdx integration, and an eventual
independent processing engine without losing provenance or hiding scientific
choices inside UI presets.

## Current evidence

- Every current stage owns an immutable float32 output and records parameters,
  content lineage, diagnostics, and structured warnings
  ([KIKU-T005](../work/KIKU-T005.md)).
- Bundles materialize both scientific and gallery lineages from one projection,
  retain intermediates, and link high-bit-depth exports to their float sources
  ([ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)).
- Final-workflow reproduction proves exact CPU-stage arrays and bytes while
  allowing an explicitly sourced GPU tolerance only at the source boundary
  ([KIKU-T010](../work/KIKU-T010.md)).
- The present graph has only been accepted for simulated forsterite products;
  it is not validated as a measured-pattern engine.

## Dependencies

- An engine-neutral input contract for simulated and measured patterns,
  including masks, bit depth, calibration, frames, and missing metadata.
- Versioned stage interfaces and capability discovery that do not depend on a
  browser, notebook, or host application.
- Licensed real-pattern fixtures and task-specific evaluation criteria.

## Unresolved questions

- Which current stages are scientifically reusable and which are specific to
  the selected gallery treatment?
- How should lazy arrays, tiles, batches, GPU implementations, and streaming
  preserve identity and diagnostics?
- Which outputs are quantitative, acquisition-corrected, display-only, or
  diagrammatic, and how should hosts enforce those labels?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) is the
  current executable lineage and export contract.
- [ADR 0003](../decisions/0003-clarity-aesthetic-target.md) defines the current
  scientific/gallery distinction.
- [KIKU-T005](../work/KIKU-T005.md) and
  [KIKU-T010](../work/KIKU-T010.md) link the stage and reproduction tests.

## Promotion trigger

Promote when one measured-pattern fixture and one simulated fixture can run through the same versioned stage interface with distinct, validated scientific labels.

## Present non-goals

- Declaring the current gallery recipe suitable for quantitative EBSD work.
- Building a GUI or plugin framework before the core contract is stable.
- Indexing, pattern matching, or map reconstruction.
- Replacing kikuchipy processing without comparative evidence.

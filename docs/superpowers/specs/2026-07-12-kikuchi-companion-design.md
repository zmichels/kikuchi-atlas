---
title: Kikuchi Companion Project Design
date: 2026-07-12
status: approved
project_prefix: KIKU
milestone: Exceptional Forsterite Pattern
---

# Kikuchi Companion Project Design

## Purpose

Build a local, scientifically traceable companion project for producing an
exceptional ultra-high-resolution forsterite EBSD pattern. The first artifact
should resemble a clean, high-end EBSD acquisition while retaining physically
meaningful dynamical band structure and an inspectable path from crystal source
through final tone mapping.

The project uses existing scientific software deliberately while preserving
our own contracts, evidence, recipes, and diagnostics. This creates a useful
companion now and a credible learning path toward a future independent
simulation or EBSD-pattern processing engine.

## Decisions

1. This repository is a companion project, not a kikuchipy fork.
2. `ebsdsim` is the authoritative dynamical source for milestone one.
3. kikuchipy is the first detector-projection and processing implementation.
4. Project-owned contracts isolate upstream types behind adapters.
5. Milestone one produces one exceptional forsterite pattern, not a phase
   gallery or general-purpose engine.
6. Future ideas are preserved with balanced evidence gates rather than added
   to active scope.
7. Implementation uses strict test-driven development.
8. When the implementation plan decomposes cleanly, tasks use sequential
   subagent-driven implementation and independent review.
9. The repository remains local with no configured remote or push requirement.

## Scope

Milestone one includes:

- a cited and validated forsterite structure source;
- a reproducible Python 3.12 environment pinned to compatible versions of
  ebsdsim and kikuchipy;
- local WebGPU/Metal readiness diagnostics;
- generation of a dynamical forsterite master pattern;
- conversion into a project-owned canonical master-pattern product;
- detector projection for a small set of symmetry-distinct orientations;
- a recorded choice of one compelling orientation;
- an explicit acquisition-style and gallery-style processing graph;
- high-bit-depth final exports;
- a complete local artifact bundle with recipes, intermediates, diagnostics,
  provenance, and decision records;
- automated scientific, numerical, adapter, and integration tests;
- human visual acceptance of the final image.

Milestone one does not include:

- a kikuchipy or ebsdsim fork;
- EMsoftOO installation as a required execution path;
- SHT parsing or spherical-harmonic indexing;
- multiple mineral phases or an orientation gallery as final products;
- simulation from imported EBSD maps;
- quantitative pattern matching or indexing;
- production integration with ebsdx or ebsdx-rs;
- a general plugin framework or independent simulation engine;
- 3D-print geometry generation;
- a graphical application.

## Architecture and Ownership

The stable data flow is:

```text
Source adapters
    ebsdsim | stored NPZ | future EMsoft HDF5 | future SHT
        |
        v
Canonical master-pattern product
    intensity + phase + energy + hemisphere + provenance
        |
        v
Detector projection
    orientation + detector geometry + supersampling
        |
        v
Processing graph
    background -> normalization -> contrast -> detail -> tone
        |
        v
Artifact and diagnostic bundle
    raw/intermediate/final images + recipe + metrics + ledger
```

### Source adapters

Each source adapter converts one external representation into the canonical
master-pattern product. Upstream objects must not leak past this boundary.
Milestone one implements ebsdsim input. Stored ebsdsim NPZ, EMsoft HDF5, and
SHT are compatible future adapters rather than present requirements.

### Canonical master-pattern product

The canonical product records at least:

- a floating-point intensity array;
- projection and hemisphere semantics;
- accelerating voltage and units;
- phase identity, formula, symmetry, and lattice metadata;
- source structure identifier and checksum;
- upstream generator and version;
- simulation recipe identifier and checksum;
- array shape, dtype, and finite-value validation;
- artifact identity and provenance links.

The contract is source-neutral and immutable. Derived products reference it
without modifying it.

### Detector projection

Projection consumes a canonical master pattern, one explicitly framed crystal
orientation, detector geometry, projection center, output resolution, and
supersampling factor. It emits an immutable floating-point detector-pattern
product plus complete geometry metadata.

Kikuchipy is the initial implementation. Project contracts, not kikuchipy
classes, define the public boundary.

### Processing graph

Processing consists of small named stages with immutable inputs, explicit
parameters, and inspectable outputs. Scientific-clean and gallery-crisp
variants derive from the same unchanged detector projection.

The intended stage order is:

```text
projected float intensity
    -> detector/background model
    -> background correction
    -> robust normalization
    -> local contrast
    -> multiscale detail enhancement
    -> restrained sharpening
    -> display tone mapping
    -> high-quality downsampling
```

No generic or hidden `make_pretty` operation is permitted. Gallery processing
may exaggerate presentation, but its recipe must reveal every transform and it
must not be mislabeled as a quantitative simulation product.

### Artifact and diagnostic bundle

A run bundle contains:

- a run manifest;
- phase and structure provenance;
- environment and hardware information;
- simulation and projection recipes;
- canonical product metadata;
- orientation candidates and the selection record;
- processing recipes;
- raw, intermediate, scientific-clean, and gallery products;
- final 16-bit TIFF and PNG exports plus a web preview;
- diagnostic metrics and warnings;
- linked scientific-run decisions;
- software versions, timings, and resource measurements.

Large products live under the ignored `local/` tree. The repository may track
small manifests, recipes, summaries, and deliberately curated gallery outputs.

## Milestone Workflow

### Proof pass

1. Validate the structure source, phase metadata, units, and provenance.
2. Validate Python, WebGPU, and Metal readiness.
3. Generate a moderate-resolution dynamical master pattern.
4. Validate and store the canonical master-pattern metadata.
5. Project a bounded set of symmetry-distinct candidate orientations.
6. Produce a contact sheet and diagnostic comparison.
7. Record the selected orientation and rationale.
8. Run all intended processing stages at proof resolution.

### Final pass

1. Generate or reuse the validated production master pattern.
2. Project the approved orientation with recorded supersampling.
3. Produce raw, acquisition-corrected, scientific-clean, and gallery-crisp
   variants.
4. Export high-bit-depth artifacts and a web preview.
5. Generate the final diagnostic and provenance bundle.
6. Reproduce the selected result from its saved recipe.
7. Complete automated and human acceptance checks.

## Diagnostics and Decisions

Diagnostics support reasoning; they do not automate aesthetic taste. A run may
record:

- saturation and clipping fractions;
- robust intensity percentiles and dynamic range;
- low-, mid-, and high-frequency energy;
- gradient and edge distributions;
- local contrast statistics;
- differences between adjacent processing stages;
- structural similarity against curated references;
- timings and resource use;
- warnings for excessive clipping, halos, or high-frequency amplification.

Three ledgers have distinct purposes:

1. Architecture decisions are durable Markdown records under
   `docs/decisions/`.
2. Scientific-run decisions are machine-readable records in local run bundles.
3. Incubator records preserve future directions under `docs/incubator/`.

Each incubator record includes motivation, current evidence, dependencies,
unresolved questions, linked decisions or experiments, a concise promotion
trigger, and explicit present non-goals.

## Error Handling

The pipeline fails explicitly when:

- phase or structure metadata is invalid or ambiguous;
- required provenance is absent from a final export;
- units or reference frames are absent or incompatible;
- energy or hemisphere semantics are inconsistent;
- arrays violate shape, dtype, or finite-value requirements;
- requested upstream capabilities are unavailable.

GPU unavailability may permit a clearly labeled diagnostic fallback only when
the invoked operation supports one. A fallback must never silently replace the
authoritative milestone recipe. Processing warnings become structured evidence
in the run bundle rather than console-only messages.

## Testing and Validation

### Test-driven development

All production features and fixes follow red-green-refactor:

1. Write one focused behavioral test.
2. Run it and verify that it fails for the expected missing behavior.
3. Write the minimum production code needed to pass.
4. Run the focused test and the appropriate wider suite.
5. Refactor only while the suite remains green.

Exploration may be disposable, but exploratory code cannot become production
code without being reimplemented test-first.

### Fast contract tests

Small synthetic arrays exercise canonical validation, units and frames,
immutable recipe serialization, artifact identity, provenance links,
processing-stage boundaries, explicit errors, and ledger relationships.

### Scientific invariant tests

Tests cover:

- explicit and consistent orientation and detector frames;
- compatible hemisphere and energy semantics;
- shape, dtype, and finite-value guarantees;
- symmetry-equivalent behavior within stated tolerances;
- detector-geometry preservation through supersampling and downsampling;
- immutable source products;
- shared source identity across scientific-clean and gallery variants.

### Adapter tests

Adapters use small real fixtures when licensing permits. Initial fixtures
include a small ebsdsim master pattern and invalid structure/metadata cases. A
compact forsterite SHT fixture is a future cross-reference, not a milestone-one
dependency.

### Numerical and image regressions

GPU results are compared with appropriate tolerances instead of assuming exact
cross-platform pixel equality. Regression evidence includes shape, coordinate
bounds, intensity statistics, deterministic checksums where valid, reference
samples, spatial-frequency summaries, clipping fractions, and structural
similarity. Updating a curated reference requires an explicit decision record.

### Integration and human acceptance

Marked integration tests cover WebGPU discovery, a small dynamical simulation,
kikuchipy loading and projection, complete proof-bundle generation, and saved
recipe reproduction.

Human review remains required for believable EBSD appearance, absence of
sharpening halos or artificial band outlines, retained zone-axis detail,
smooth tonal structure, compelling composition, and a meaningful distinction
between scientific-clean and gallery outputs.

## Repository Structure

The repository remains `/Users/Z/Documents/kikuchi`. The Python distribution
and command namespace are `kikuchi_lab` and `kikuchi-lab`.

```text
kikuchi/
|-- pyproject.toml
|-- README.md
|-- src/kikuchi_lab/
|   |-- sources/
|   |-- model/
|   |-- projection/
|   |-- processing/
|   |-- diagnostics/
|   |-- artifacts/
|   `-- cli/
|-- tests/
|   |-- unit/
|   |-- scientific/
|   |-- adapters/
|   `-- integration/
|-- phases/forsterite/
|-- recipes/
|   |-- proof/
|   `-- gallery/
|-- reference/catalog/
|-- docs/
|   |-- superpowers/specs/
|   |-- work/
|   |-- decisions/
|   `-- incubator/
`-- local/
```

Notebooks may demonstrate or explore the package but do not own canonical
behavior.

## Repo-Native Work Tracking

The tracker uses prefix `KIKU` and the epic-feature-story-task hierarchy.
Initial active scope is:

- `KIKU-E001`: Dynamical Kikuchi companion
  - `KIKU-F001`: Exceptional forsterite pattern
    - repository and environment readiness;
    - phase provenance;
    - canonical master-pattern contract;
    - ebsdsim adapter;
    - detector projection and orientation selection;
    - explicit processing graph;
    - diagnostics and artifact bundle;
    - final high-resolution acceptance.

Frontmatter and acceptance criteria are authoritative. Parent and child links
remain symmetric and are validated by repository-local tracker tooling.

## Ecosystem Strategy

Milestone one uses ebsdsim and kikuchipy directly. The project catalog records,
but does not bulk-vendor, relevant upstream resources:

- [kikuchipy](https://kikuchipy.org/) for EBSD signal handling, projection,
  processing, and related scientific libraries;
- [ebsdsim](https://pypi.org/project/ebsdsim/) for fast dynamical master-pattern
  generation through WebGPU;
- [EMsoftOO](https://github.com/EMsoft-org/EMsoftOO) as a future independent
  Metal-capable dynamical reference;
- [SHTdatabase](https://github.com/EMsoft-org/SHTdatabase) for compact reference
  master-pattern representations, including forsterite at 10-30 kV;
- [SHTfile](https://github.com/EMsoft-org/SHTfile) for the open SHT format;
- [EMSphInx](https://github.com/EMsoft-org/EMSphInx) for spherical-harmonic
  indexing, detector, correlation, and processing ideas;
- [kikuchipy open datasets](https://kikuchipy.org/en/stable/user/open_datasets.html)
  for future real-pattern processing and regression evidence;
- [kikuchipy related projects](https://kikuchipy.org/en/stable/user/related_projects.html)
  as the wider research landscape.

External data catalog entries record URLs, licenses, checksums, expected
layouts, and retrieval instructions. Multi-gigabyte datasets are not required
for milestone-one development.

## Implementation Governance

After this specification is committed and reviewed, a detailed implementation
plan decomposes the milestone into small contract-led tasks. Before execution,
the plan is checked for contradictions, ordering constraints, and suitability
for subagent-driven development.

Production implementation occurs on a local `codex/` branch or isolated
worktree, not directly on the root branch. There is no remote or push step.

For eligible tasks:

1. A focused task brief is generated from the implementation plan.
2. A fresh implementer follows strict TDD and commits the slice.
3. A fresh reviewer evaluates specification compliance and code quality.
4. Important findings go through a fix and re-review loop.
5. Clean completion is recorded in the durable subagent progress ledger and
   repo-native work tracker.
6. A broad final review covers the complete milestone diff.

Tightly coupled work may remain with the coordinating agent when delegation
would damage continuity. Subagent use is a quality mechanism, not a source of
artificial task fragmentation.

## Acceptance Criteria

Milestone one is accepted when all of the following are true:

- the forsterite structure source and simulation inputs are cited, checksummed,
  and validated;
- a dynamical master pattern is generated locally with ebsdsim;
- the master pattern is represented by the project-owned canonical contract;
- one selected orientation is projected at the approved detector geometry and
  supersampling;
- raw, acquisition-corrected, scientific-clean, and gallery-crisp products are
  present and linked to the same source projection;
- every processing transform and parameter is recorded;
- the final scientific-clean and gallery products are exported as 16-bit TIFF
  and PNG plus a web preview;
- diagnostics and structured warnings are included in the run bundle;
- a saved recipe reproduces the selected output within documented tolerances;
- the fast test suite passes cleanly;
- the GPU integration gate passes on the local M2 environment;
- human review accepts the image as crisp, compelling, EBSD-like, and free of
  conspicuous processing artifacts;
- the tracker, decision record, and milestone evidence are current;
- no remote repository or push is required.

## Parked Directions

The following are preserved in the incubator after tracker creation:

- matched kinematical and dynamical diagnostic comparison;
- orientation-variety gallery;
- phase-general simulation;
- orientation selection from EBSD maps and datasets;
- richer detector and acquisition-response modeling;
- 2D relief and spherical 3D-print exports;
- reusable EBSD-pattern processing contracts;
- ebsdx and ebsdx-rs product or plugin integration;
- SHT adapters and spherical-harmonic diagnostics;
- EMsoftOO cross-validation;
- an independent simulation or processing engine;
- richer decision-state diagnostics inspired by decision-PGA.

None of these directions is part of milestone-one acceptance unless promoted
through its recorded evidence gate.

# Atlas Phase Batch Design

**Date:** 2026-07-25

**Status:** User-approved design

## Goal

Promote as many of the next low-ambiguity mineral references as can clear the
complete Kikuchi Atlas parity contract without weakening source provenance,
scientific scope, artifact validation, or review quality.

The ordered batch is:

1. Grossular from COD 9000439.
2. Almandine from COD 1531283.
3. Tremolite from COD 2108838.

A phase is complete only when it has the same nine registered product roles,
source evidence, generated artifacts, acceptance record, and review gates as
the accepted pyrope slice.

## Starting State

The current Atlas contains 12 phases and 122 available products. Calcite,
enstatite, and pyrope are the three most recent nine-product parity additions.
The current `master` branch already contains their Atlas registry and release
metadata records, but some verified calcite and enstatite source, recipe, test,
acceptance, and tracker files remain untracked in the main checkout.

The checkout also contains unrelated quartz, artifact-catalog, work-item, and
rotation changes. Those changes are user work and remain outside this batch.

The repository-wide suite has two known unrelated baseline failures:

- `tests/adapters/test_kikuchipy_kinematical.py::test_adapter_context_keeps_upstream_products_private_and_complete`
- `tests/unit/test_product_status.py::test_product_catalog_has_unique_static_entries_and_tracked_inputs`

Each batch phase must keep its focused gate green and report the current
repository-wide result separately.

## Architecture

### Baseline stabilization

Before new phase work, audit and commit only the existing calcite and enstatite
files required by the tracked Atlas state:

- Original/derived structural sources and `source.yml` records.
- Direct-reflector, kinematical, retained-depth, ridge-globe, and relief-globe
  recipes.
- Source and recipe contract tests.
- Acceptance records and their task/feature links.
- The existing enstatite implementation plan if it is part of the accepted
  handoff.

The stabilization commit must exclude unrelated dirty files. Its review must
prove that every included file is already represented by the current Atlas or
its acceptance/tracking records and that focused calcite/enstatite tests pass.

### Isolated batch workspace

After stabilization, create a linked worktree at:

```text
.worktrees/atlas-phase-batch
```

on branch:

```text
codex/atlas-phase-batch
```

The project-local `.worktrees/` directory is already ignored. The worktree is
created from the stabilized `master` state.

The existing published artifact roots for calcite, enstatite, and pyrope total
approximately 1.1 GB. Seed the worktree with APFS copy-on-write clones of those
phase directories rather than symlinks. This gives the batch an isolated,
writable artifact cache without an immediate full-byte duplicate. New phase
outputs use disjoint phase-specific directories under
`local/atlas-expansion/<phase>/`.

If copy-on-write cloning is unavailable, use a normal verified copy. Do not
share mutable output directories between the main checkout and the batch
worktree.

## Candidate Boundaries

The source-intake ledger identifies these preferred candidates:

| Phase | Candidate | Initial boundary |
| --- | --- | --- |
| Grossular | COD 9000439 | Ca3Al2Si3O12 at 25 C, cubic Ia-3d |
| Almandine | COD 1531283 | Fe3Al2Si3O12, cubic Ia-3d |
| Tremolite | COD 2108838 | 293 K tremolite-family refinement, monoclinic C2/m |

These descriptions are intake hypotheses, not publication claims. Each source
audit must obtain the original CIF, pin its bytes, verify licensing and
citation, and derive the final display name, formula, setting, temperature,
occupancy policy, thermal-factor policy, and scope note from the actual record.

For a natural or non-ideal composition, the Atlas display name and scope must
retain the exact reported composition. A generic group name may not conceal a
specific measured solid solution.

## Per-Phase Data Flow

Only one phase may pass through tracked implementation and Atlas publication at
a time.

### 1. Source intake

- Retrieve the original CIF from the declared source.
- Record its exact SHA-256, source page, license, and primary citation.
- Verify formula, cell, setting, coordinates, occupancies, thermal factors, and
  crystallographic site multiplicities.
- Preserve the original bytes.
- Create a derivative only when the transformation is deterministic,
  scientifically justified, and fully recorded.
- Add a failing source/adapter contract before adding the source record.

### 2. Recipe contracts

- Add direct-art and tied-cohort reflector recipes.
- Add the approved 20 keV Atlas kinematical recipe.
- Add the retained near-depth presentation recipe.
- Add ridge-globe and kinematical intensity-relief recipes.
- Bind all recipe IDs and canonical products to loader-emitted or
  manifest-emitted identities rather than guessed values.

### 3. Scientific intermediates

- Build the direct-art catalog.
- Run direct-versus-simulator reflector parity.
- Build the canonical kinematical master and retained-depth product.
- Build four standard-width orientation templates.
- Build the four-cohort reflector catalog.

Atlas publication remains forbidden if parity fails, a required cohort is
empty, or lineage cannot be verified.

### 4. Presentation and printable products

- Render the direct x-axis rotation.
- Render the retained-depth x-axis rotation.
- Build the reflector-ridge globe.
- Build the kinematical intensity-relief globe.

Both movies must be hash-bound and ffprobe-verified. Both meshes must pass the
repository validator with watertight and winding-consistent geometry. FDM
warnings are preserved as manufacturing advisories and never reframed as proof
of physical printability.

### 5. Atlas publication

Register exactly these nine roles:

1. Standard direct-reflector template, designated hero.
2. Azimuthal-60 direct-reflector template.
3. Tilt-plus-20 direct-reflector template.
4. Oblique-high direct-reflector template.
5. Direct-reflector x-axis rotation.
6. Reflector-ridge globe.
7. Kinematical master.
8. Retained-depth x-axis rotation.
9. Kinematical intensity-relief globe.

Every media, preview, bundle, provenance, and recipe path must exist before the
product record becomes available. No existing phase or product may be removed,
renamed, or mutated to make the counts pass.

### 6. Acceptance and tracking

Create one acceptance record and one completed child task per promoted phase.
The acceptance record must contain:

- Original and derivative hashes.
- Source citation, license, and scientific scope.
- Exact run, product, catalog, recipe, and build IDs.
- Reflector and cohort counts.
- Parity results.
- Animation profiles and hashes.
- Mesh results and FDM advisories.
- Manifest inventory verification.
- Atlas and release-metadata counts.
- Explicit nonclaims.
- Focused and repository-wide test status.

The umbrella phase-expansion feature and source-intake task remain active until
all requested minerals are either promoted or explicitly deferred.

## Concurrency Model

Read-only source triage for later candidates may run in parallel. It may collect
CIFs, citations, license terms, candidate formulas, settings, thermal-factor
coverage, and likely blockers.

Tracked writes, artifact builds, registry edits, and publication are
sequential. One phase must clear its acceptance and independent review gate
before the next phase begins tracked implementation. This avoids shared
registry conflicts, cross-phase artifact contamination, and ambiguous failure
attribution.

## Error and Blocked-Source Policy

A candidate is blocked rather than silently repaired when any of these cannot
be resolved from defensible evidence:

- Exact composition or mineral identity.
- Symmetry setting or basis transformation.
- Occupancy interpretation.
- Missing or incompatible thermal factors.
- Source rights or citation.
- Site multiplicities.
- Direct-versus-simulator reflector parity.
- Artifact lineage or checksum agreement.

Blocked candidates receive a durable intake note explaining the evidence,
failure, nonclaim, and possible promotion trigger. The batch then advances to
the next candidate.

No phase may inherit displacement parameters, occupancies, or composition from
another mineral merely to satisfy the simulation loader.

## Testing and Review

Each phase uses test-driven implementation and task-level independent review.
The final phase slice also receives a broad review against its written plan.

The completion gate includes:

- Source/adapter tests.
- Recipe contract tests.
- Direct and retained-rotation tests.
- Atlas and release-metadata tests.
- Work-item validation.
- Fresh Atlas build.
- Manifest existence, byte-count, and SHA-256 audit.
- Animation hash and ffprobe verification.
- Mesh validation and STL hash verification.
- Diff and formatting checks.
- One repository-wide test run with unrelated failures reported separately.

The acceptance inventory targets are:

| Completion point | Phases | Available products |
| --- | ---: | ---: |
| Current baseline | 12 | 122 |
| Grossular complete | 13 | 131 |
| Almandine complete | 14 | 140 |
| Tremolite complete | 15 | 149 |

These targets apply only if all preceding phases are promoted. If a candidate
is blocked, later expected counts are reduced by one phase and nine products.

## Nonclaims

The batch does not claim that one endmember represents an entire mineral group,
that idealized direct-reflector art is a dynamical detector simulation, that
retained-field animation is per-frame diffraction recomputation, that mesh
validation proves printability, or that source-backed products validate EBSD
indexing or orientation accuracy.

The batch introduces no new diffraction engine. It reuses the existing
source-verification, reflector-parity, kinematical, presentation, globe,
registry, release-audit, and work-tracking boundaries.

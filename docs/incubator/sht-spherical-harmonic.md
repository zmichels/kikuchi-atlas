# SHT Adapters and Spherical-Harmonic Diagnostics

- Status: Incubating
- Boundary: an additional source and analysis seam, not a new milestone source

## Motivation

Open SHT master-pattern files and spherical-harmonic representations may offer
compact reference data, efficient correlation, continuous spherical analysis,
and a route toward map or print products. They could also provide an external
comparison for the ebsdsim-derived canonical master if projection, energy, and
normalization semantics are made explicit.

## Current evidence

- The architecture already reserves source adapters for stored ebsdsim NPZ,
  future EMsoft HDF5, and future SHT inputs while keeping the canonical product
  source-neutral
  ([approved design](../superpowers/specs/2026-07-12-kikuchi-companion-design.md)).
- The present canonical master requires two Lambert hemispheres, energy and
  phase metadata, provenance, and an immutable float array
  ([KIKU-T002](../work/KIKU-T002.md)).
- The ecosystem review recorded SHTdatabase, SHTfile, and EMSphInx as relevant
  future resources, but no SHT fixture, parser, license record, or harmonic
  convention has been admitted to this repository.

## Dependencies

- A small redistributable SHT fixture with authoritative format/version,
  phase, energy, symmetry, projection, normalization, and license metadata.
- A reviewed mapping from SHT coefficients or samples to the canonical
  master-pattern semantics.
- Independent tests for coordinate conventions, truncation behavior, and
  reconstruction error.

## Unresolved questions

- Should the first slice parse an SHT file, reconstruct a canonical raster, or
  expose harmonic diagnostics without raster ownership?
- How should coefficient normalization, basis ordering, symmetry, and energy
  integration enter product identity?
- Can an available forsterite SHT product be compared fairly with the local
  ebsdsim master given different generators and simulation settings?

## Linked decisions and experiments

- [KIKU-T002](../work/KIKU-T002.md) defines the current canonical product and
  persistence behavior.
- [KIKU-T003](../work/KIKU-T003.md) records the authoritative local dynamical
  source path and why native source evidence remains intact.
- [EMsoft cross-validation](emsoft-cross-validation.md) records the related
  independent-source comparison problem.

## Promotion trigger

Promote when one license-cleared SHT fixture has enough documented conventions to reconstruct or diagnose it without guessed phase, energy, projection, or normalization semantics.

## Present non-goals

- Bulk-vendoring the SHTdatabase.
- Treating SHT compression as an independent physical simulation.
- Replacing the accepted ebsdsim master for milestone one.
- Implementing spherical-harmonic indexing or search.

# Enstatite Atlas parity acceptance

Date accepted: 2026-07-24

## Source boundary

- Exact reference: COD 9001593, MgSiO3 orthoenstatite at 0 GPa.
- Structure: `MgSiO3`, space group 61, `P b c a`.
- Tracked CIF SHA-256:
  `9a7e8ca57e3eb4f804fdeb4954566cfaa7b3a61fe24f4931c9c76c1e8228d51d`.
- Scope: one 0 GPa orthoenstatite refinement; not a universal
  orthopyroxene composition, pressure series, detector, indexing, or
  orientation-accuracy reference.

`verify_structure()` accepted the CIF checksum, formula, lattice, coordinates,
occupancies, Uiso values, and all ten site multiplicities. Each independent
site has multiplicity 8, for 80 atoms in the conventional cell.

## Tracked baseline paths

- Source record: `phases/enstatite/source.yml`.
- Direct-reflector recipes:
  `recipes/reflectors/enstatite-art-bands.yml` and
  `recipes/reflectors/enstatite-catalog.yml`.
- Kinematical recipe:
  `recipes/kinematical/enstatite-001-atlas-parity-master.yml`.
- Near-depth presentation recipe:
  `recipes/presentation/enstatite-near-depth-atlas-parity.yml`.
- Reflector-ridge globe recipe:
  `recipes/globes/enstatite-reflector-ridges.yml`.
- Kinematical intensity-relief recipe:
  `recipes/relief/enstatite-atlas-parity-kinematical-intensity.yml`.

## Accepted products

- Zero-master direct catalog:
  `direct-art-catalog-run-069cc023c3e870e8`.
- Simulator parity:
  `reflector-parity-report-80221a9d43129e66`; exact HKL, d-spacing, normal,
  strength, Bragg-angle, weight, and provenance matches; one bounded
  65-by-65 smoke master and no retries.
- Four standard-width orientation templates under
  `local/atlas-expansion/enstatite/templates`.
- Direct x-axis animation: 144 frames, 1024 px, 12 fps, 12 seconds.
- Kinematical bundle: `kinematical-run-5969a144389b170c`, 5,980 signed master
  reflectors and canonical master product `master-5843c7eb03a9a4ed`.
- Near-depth bundle: `near-depth-run-9ec43b243079556c`.
- Retained-field x-axis animation: 144 frames, 1024 px, 12 fps, 12 seconds.
- Reflector-ridge globe:
  `reflector-ridge-globe-build-22ca622745752a1f`; mesh validation passed,
  watertight and winding-consistent.
- Kinematical intensity-relief globe:
  `relief-globe-build-20eecba93ca3a20e`; mesh validation passed, watertight
  and winding-consistent.

The intensity-relief mesh retains its build-time FDM advisory warnings about
small edges, local slope, dynamic range, downward faces, and feature floor.
Those warnings are manufacturing guidance, not hidden as proof of universal
printability.

## Publication checks

- Atlas phase count: 11.
- Atlas product count: 113.
- Structural-source audit count: 11.
- All registered enstatite media, preview, bundle, provenance, and recipe paths
  exist locally.
- Targeted Atlas, release-metadata, parity-recipe, source, animation, and
  tracker tests pass.

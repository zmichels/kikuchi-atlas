# Calcite Atlas parity acceptance

Date accepted: 2026-07-24

## Source boundary

- Exact reference: COD 1547350, 295 K calcite in air.
- Structure: `C1Ca1O3`, space group 167, conventional hexagonal `R -3 c :H`.
- Tracked CIF SHA-256:
  `0fb4f7a3f6f0aeb6e053e0512a1ffa959f3ba1d6f49e7186063324acab3290e7`.
- Scope: one calcite refinement; not a universal carbonate, twinning, strain,
  detector, indexing, or orientation-accuracy reference.

`verify_structure()` accepted the CIF checksum, formula, lattice, coordinates,
occupancies, Uiso values, and 6/6/18 site multiplicities.

## Scoped provenance whitespace waiver

Date adjudicated: 2026-07-25.

The raw upstream source `phases/calcite/COD-1547350.cif` is preserved
byte-for-byte to retain its declared and verified SHA-256
`0fb4f7a3f6f0aeb6e053e0512a1ffa959f3ba1d6f49e7186063324acab3290e7`.
The generic full-range `git diff --check` warning is waived only for the
trailing spaces in that source file at lines 104 and 113; removing them would
change the checksum-pinned scientific source bytes. This waiver does not apply
to any other file: all non-source diffs must continue to pass whitespace
checks.

## Tracked baseline paths

- Source record: `phases/calcite/source.yml`.
- Direct-reflector recipes:
  `recipes/reflectors/calcite-art-bands.yml` and
  `recipes/reflectors/calcite-catalog.yml`.
- Kinematical recipe:
  `recipes/kinematical/calcite-001-atlas-parity-master.yml`.
- Near-depth presentation recipe:
  `recipes/presentation/calcite-near-depth-atlas-parity.yml`.
- Reflector-ridge globe recipe:
  `recipes/globes/calcite-reflector-ridges.yml`.
- Kinematical intensity-relief recipe:
  `recipes/relief/calcite-atlas-parity-kinematical-intensity.yml`.

## Accepted products

- Zero-master direct catalog:
  `direct-art-catalog-run-cd71c68f7449dfd8`.
- Simulator parity:
  `reflector-parity-report-d0891a56d99f358e`; exact HKL, d-spacing, normal,
  strength, Bragg-angle, weight, and provenance matches; one bounded
  65-by-65 smoke master and no retries.
- Four standard-width orientation templates under
  `local/atlas-expansion/calcite/templates`.
- Direct x-axis animation: 144 frames, 1024 px, 12 fps, 12 seconds.
- Kinematical bundle: `kinematical-run-3b6cf9bd8c987327`, 992 signed master
  reflectors and a 2-by-1025-by-1025 canonical field.
- Near-depth bundle: `near-depth-run-23ca45ca5a4ded6f`.
- Retained-field x-axis animation: 144 frames, 1024 px, 12 fps, 12 seconds.
- Reflector-ridge globe:
  `reflector-ridge-globe-build-d4963f20a3e3b35e`; validated subdivision-7
  80 mm STL.
- Kinematical intensity-relief globe:
  `relief-globe-build-62b9e581469c5065`; validated subdivision-7 80 mm STL.

The four-tier ridge catalog uses a calcite-specific normalized-weight cutoff of
0.05 because its high-symmetry selected set has exactly four tied strength
blocks. The underlying 20 keV reflector calculation and 0.7 Å d-spacing cutoff
are unchanged.

## Publication checks

- Atlas phase count: 10.
- Atlas product count: 104.
- Structural-source audit count: 10.
- All registered calcite media, preview, bundle, provenance, and recipe paths
  exist locally.
- Targeted Atlas, release-metadata, parity-recipe, source, and tracker tests
  pass.

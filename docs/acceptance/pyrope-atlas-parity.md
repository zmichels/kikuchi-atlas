# Pyrope Atlas parity acceptance

Date accepted: 2026-07-25

## Source boundary

- Exact reference: COD 9000435, pyrope at 298.15 K (25 deg C), Meagher (1975).
- Structure: `Mg3Al2Si3O12`, space group 230, `I a -3 d`, cubic cell
  `a = 11.456` angstrom; site multiplicities Mg/Al/Si/O = 24/16/24/96.
- Original CIF SHA-256:
  `90c7d0b964653c5d1e32aa944a45430e760f29f3910ff8997a0a3524d4f55932`.
- Deterministic simulation derivative SHA-256:
  `d5235c9c9a5f335eb35e764435f27de32591bc96d3728ce3c241b8462035d7e8`.
- The source record retains the COD scientific-community attribution-use notice
  and the original citation: Meagher, E. P. (1975), *American Mineralogist*
  60, 218-228.
- The derivative preserves coordinates, implicit full occupancies, cell, and
  symmetry operations. It removes the anisotropic loop and uses `B_iso =
  8*pi^2*U_iso`, with missing thermal factors rejected. Al Uiso is retained at
  0.00507 square angstrom; Mg, Si, and O are the trace-derived `(U11 + U22 +
  U33) / 3` values 0.011836666666666667, 0.0036133333333333334, and 0.00596
  square angstrom, respectively.

`verify_structure()` accepted the derivative checksum, formula, lattice,
setting, coordinates, implicit occupancy default of 1.0, thermal factors, and
all 24/16/24/96 site multiplicities.

Scope: this is one 298.15 K pure-Mg garnet endmember reference. It is not a
claim about all garnets, natural pyrope solid solutions, pressure dependence,
detector acquisition, indexing, or orientation accuracy.

## Accepted products and provenance

- Zero-master direct catalog:
  `direct-art-catalog-run-7bf552e7d9662dae`; catalog
  `art-band-catalog-9599672c85b558ce`; 2,972 members, 200 art-eligible.
- Simulator parity: run `reflector-parity-run-b0b8452719e3fdf7`, report
  `reflector-parity-report-87ac3da2dc3aca6c`; passed with retry count 0,
  exact HKL and provenance matches, and zero d-spacing, normal, strength,
  Bragg-angle, and weight errors. The bounded smoke master is 2-by-65-by-65;
  direct and simulator each selected 5,944 signed reflectors.
- Four standard-width orientation templates:
  `pyrope-hemisphere-standard-run-cf3ddb145179cc6e`,
  `pyrope-hemisphere-standard-run-b90e12560a80f8db`,
  `pyrope-hemisphere-standard-run-9c85bbaf883a30b7`, and
  `pyrope-hemisphere-standard-run-124fc32621d4c0b3`.
- Kinematical bundle: `kinematical-run-d30e6a355c2dbdcd`; canonical product
  `master-a7da320394e377ba`, canonical array SHA-256
  `978f9a8aae69a2d058a86d729135209c7ead57e07342cf5c6daad3577487d961`,
  canonical-file SHA-256
  `566f40281f15f3d21998eb4d5d114b0169857d41254a85edf0d526ccf5d6d719`,
  with 5,944 master reflectors.
- Near-depth bundle: `near-depth-run-7ce814adad1aba1d`; treatment recipe
  `recipe-d634552996a51cb1`.
- Direct x-axis animation SHA-256:
  `a8a0a38991c41f82fee3d82382c2a98513c3acc1c24a7ab4fb3d802a4fcb0b61`.
  Near-depth retained-field x-axis animation SHA-256:
  `53d904f1f718e692e085a6d262df486253cf8d2a99380e2678ccf562a62b3aa3`.
  Both are H.264 High, 1024-by-1024, yuv420p, 144 frames at 12 fps, 12 seconds.
- Reflector catalog: `reflector-catalog-build-1ab0d883196b548d`, catalog
  `reflector-catalog-e242a05d8dce8a93`; at threshold 0.10 it contains 560
  total reflectors, 128 eligible reflectors in 13 weight blocks, divided into
  four cohorts of 36/34/27/31.
- Reflector-ridge globe: `reflector-ridge-globe-build-5cfde597411006cd`, STL
  SHA-256 `ecb32b4eb32987be2f832f7918520b42a6b92242219a863f4630869597563f04`.
- Kinematical intensity-relief globe:
  `relief-globe-build-e14176e6772c169c`, STL SHA-256
  `b1aa58e3be5334413d479f93c4ac71118d7195be9bda149458a5922073424c1f`.

## Artifact and mesh verification

All 12 pyrope manifest files were read. Every declared artifact exists and
matches its recorded byte count and SHA-256: 89 manifest-declared files,
including the four animation exports. Both rotation movies also match the
recorded hashes and ffprobe profiles above.

Both STL validations passed with one body, positive volume, no degenerate or
duplicate triangles, watertight geometry, and winding consistency. The ridge
globe has no warnings. The relief globe records FDM advisories, not failures:
minimum edge 0.34642915314104045 mm, minimum triangle altitude
0.2816328196705608 mm, maximum local relief slope 38.360731004821936 degrees,
radial dynamic range 1.1960976794516114 mm, downward-face fraction
0.49923095703125, and configured feature floor 0.8 mm. Physical print
acceptance remains separate from this geometric validation.

## Publication checks

- Atlas build: 12 phases and 122 available products.
- Structural-source audit: 12 tracked sources, including nine CC0 records.
- The nine registered pyrope product roles have existing local media, preview,
  bundle, provenance, and recipe paths.
- Work-item validation and the focused source, Atlas, release-metadata,
  recipe-parity, direct-rotation, and retained-depth-rotation tests pass.

## Repository-wide baseline

The controller-owned full suite completed separately from the focused pyrope
acceptance gate: 2 failed, 1,567 passed, 1 skipped, and 4,383 warnings in
524.51 seconds. The two failures match the pre-existing unrelated baseline:
`tests/adapters/test_kikuchipy_kinematical.py::test_adapter_context_keeps_upstream_products_private_and_complete`
and
`tests/unit/test_product_status.py::test_product_catalog_has_unique_static_entries_and_tracked_inputs`.
Neither test was changed by this pyrope slice.

## Nonclaims

The direct-reflector templates and their animation are crystallographically
sourced plane-trace science art, not dynamical EBSD intensity simulations or
detector acquisitions. The near-depth rotation is a presentation-only active
rotation of retained kinematical and overlap fields, not a per-frame diffraction
simulation. The printable globes are modeled field geometry; their successful
mesh checks are not physical-print, metrology, deformation, or orientation-
measurement validation.

# Spherical intensity-relief globe acceptance

Status: **DONE_WITH_CONCERNS**. The atomic workflow and automated mesh acceptance passed.
Flash Studio has no discovered safe noninteractive inspection seam, so slicer-native import
and repair reporting remain unobserved. No physical print was performed.

## Accepted build

- Build ID: `relief-globe-build-3334895cd23540f5`
- Bundle: [local acceptance bundle](../../local/relief-globes/forsterite-501/relief-globe-build-3334895cd23540f5)
- Manifest: [relief-manifest.json](../../local/relief-globes/forsterite-501/relief-globe-build-3334895cd23540f5/relief-manifest.json)
- Validation: [mesh-validation.json](../../local/relief-globes/forsterite-501/relief-globe-build-3334895cd23540f5/mesh-validation.json)
- Preview: [forsterite-intensity-relief-preview.png](../../local/relief-globes/forsterite-501/relief-globe-build-3334895cd23540f5/forsterite-intensity-relief-preview.png)
- STL: [forsterite-intensity-relief-globe.stl](../../local/relief-globes/forsterite-501/relief-globe-build-3334895cd23540f5/forsterite-intensity-relief-globe.stl)

The source file SHA-256 was verified before loading. It is
`cd056ab4af34aa3695e492f2f6a85f47beb5e97658ef6c5cc4120802ae161c03`; the loaded product is
`master-437f865cd0f68384`, with array SHA-256
`7cefc253da7c1d17babca40cfeab12be1e3b400cf259bd28686df51c78451f2e` and shape
`(2, 501, 501)`. The frame is `crystal:Pnma-derived-from-Pbnm`; north owns the equator;
maximum absolute and normalized seam residuals are both `0.0` against the `1e-6` limit.
The validated master records intensity units `raw dynamical intensity`; the exact source shape,
units, and `callahan-emsoft-square-lambert/v1` transform contract participate in field and build
identity and are repeated in the readable manifest.

## Mapping, filtering, and topology

One global p1–p99 range maps raw values `283.8775329589844`–`636.9645385742188` with gamma
`1.0` and bright-outward direction. The spherical Gaussian filter uses `0.8 mm` FWHM,
`3.0 sigma` cutoff, 19–30 neighbors, and constant residual `6.661338147750939e-16`.

The topology is `icosphere-b542bf2969717758`, subdivision 7, with 163842 vertices, 327680
triangles, and Euler characteristic 2. Direction bytes hash to
`db2d0175bf29ff662f7e3acb16762ebee3687b74ca04e37c7790cf1e98e49a34`; face bytes hash to
`083a26ae07d4840cec1a501161e72f8e372ddd7bb0e6131b704fcedc301d8601`.

## Validation and inspection

The unchanged indexed geometry passes as one watertight, consistently wound, positive-volume
body. It has no duplicate or degenerate triangles. Its radial certificate minimum is
`4.567859649491448`, above tolerance `6.4e-08`; radii span
`40.00063423365049`–`41.2 mm`; maximum possible diameter is `82.4 mm`.

A processed Trimesh STL round-trip independently reported one watertight, winding-consistent
volume with extents `82.12969207763672 x 82.4000015258789 x 82.39990997314453 mm`. This is
automated round-trip evidence, not slicer evidence. The fixed preview was visually inspected:
the globe and relief bands are legible, continuous, and show no obvious equator seam or missing
surface region.

Flash Studio 1.7.11 (`/Applications/Flash Studio.app`) advertises STL as a viewer document type.
Read-only bundle inspection found only its GUI executable and no separate CLI or console slicer.
Because opening or controlling the GUI was explicitly out of scope, dimensions, solid count,
repair behavior, and warnings were not observed in that slicer. This is the remaining acceptance
concern. A physical print, build orientation, supports, infill, material, and printer settings
are explicitly outside this acceptance.

## Runtime and reproducibility

The final reviewed real CLI rebuild completed in `99.01 s` wall time (`30.29 s` user time) on the
acceptance machine. Two
independent full-resolution analytic builds produced identical build IDs and byte-identical
five-file trees. The accepted runtime identity is Python 3.12.13, kikuchi-lab 0.1.0, NumPy
2.4.6, SciPy 1.18.0, kikuchipy 0.13.0, Trimesh 4.12.2, and Matplotlib 3.11.0.

Build identity and the readable manifest share one exact mapping of ten named project contracts:
canonical JSON, binary STL, deterministic NPZ, preview rendering, preview style, validation JSON
schema, manifest schema, manifest inventory, five-file bundle layout, and sorted indented UTF-8
JSON artifact-file serialization with a trailing newline. Focused relief gates
passed with `155 passed, 5 deselected`; the explicit slow workflow gate passed all `3` tests; and
the full fast repository gate passed `595` tests with one environment-dependent skip.

The manifest SHA-256 is
`f9d39c287b0608f4e54c6da2d55d6c29d22e0c98a92b62f3aa0a6f3551b5cd69`. Its four-file inventory
was independently recomputed and matched exactly: STL
`c9c52b5b1e6fe302a2f49dbecb84a4b1432906a9d4f2cfc5626ec0d3734eb1cf` (16384084 bytes),
preview `fefe61d934324cd2d1d9886227404eee79aeda45b9ded09b5c663ca0090ea105`
(150894 bytes), field NPZ
`d17af8175f7f9777c865337c4bd983bee4858290c2f05b6ec73587aa83ace9a1` (27691524 bytes), and
validation JSON `321b6cda725eca35ff50d0fb64b52da4585c39c62b034d3fa4550b94ec435a65`
(1574 bytes).

The complete bundle is exactly five files. Publication fsyncs the staged tree, uses Darwin
`renamex_np(..., RENAME_EXCL)` for atomic no-clobber directory publication, then fsyncs the
parent. Tests prove a racing or pre-existing destination is never overwritten. Rename failure
cleans staging; parent-fsync failure rolls back and re-fsyncs; an unprovable rollback raises an
explicit uncertain-publication error naming the completed path. Failure injection at the final
preview seam also left no partial or completed bundle.

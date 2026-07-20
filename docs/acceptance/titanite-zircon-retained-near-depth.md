# Titanite and Zircon Retained Near-Depth Fields

## Scope

This companion product intentionally extends the dense Ice Ih near-depth
lineage, while keeping the existing direct-reflector tattoo/vector products
unchanged. It supplies a reusable field foundation for two further phases:
synthetic room-temperature titanite and ambient-pressure zircon.

These are **kinematical, presentation-only science-art fields**. They are not
experimental EBSD acquisitions, detector forward models, quantitative indexing
references, or dynamical master patterns.

## Retained Inputs and Static Proofs

| Phase | Source | Base recipe / master run | Near-depth run | Static depth SHA-256 |
| --- | --- | --- | --- | --- |
| Titanite | COD-9000509, synthetic CaTiSiO5 at 298.15 K | `recipes/kinematical/titanite-quiet-master.yml`, `kinematical-run-630cf9676428842e` | `near-depth-run-f01977d809458364` | `6e8c7c39faa5db7b5b39380b69d968f4aa82ba170e226d2b7e3a4d545e2188a8` |
| Zircon | COD-9000684 isotropic-U derivative, ZrSiO4 at 1 atm | `recipes/kinematical/zircon-quiet-master.yml`, `kinematical-run-fe9afb8f5d8f4ba9` | `near-depth-run-b3faf10a1a53d610` | `2b5cb9604bdf5440ac6f9f942080af4b5b5382cda9b06db8f5b84d4d0de3bb93` |

Both source masters are `1025 × 1025` pixels per hemisphere (`half_size: 512`)
and retain raw float32 arrays, source snapshots, reflection catalogs,
projection ledgers, recipes, and manifests.

The static depth treatments use no spatial filter and nearest-neighbor display
of the field. Their additional-overlap expressions preserve exact axial
`hkl/-h-k-l` pairing while preserving distinct harmonic orders:

```text
overlap_raw = max(sum(weight) - max(weight), 0)
weight = (abs(F_hkl) / max(abs(F)))^2
```

- Titanite: 252 signed reflectors collapse to 126 axial bands. Its 26
  retained band-edge paths use the stronger `0.55` relative threshold; the
  central fine-line layer is deliberately disabled.
- Zircon: 378 signed reflectors collapse to 189 axial bands. Its 24 retained
  band-edge reflectors produce 32 exact upper-hemisphere paths at the same
  threshold; its central fine-line layer is deliberately disabled.

## Active X-Axis Rotations

The loops at
`local/idealized-near-depth-rotation/{phase}-x-axis-band-led-v1/` use the
stored master and stored additional-overlap array. Each of the 144 distinct
frames samples the field through an active sample-frame x-axis rotation, with
the same explicit initial Bunge orientation `[17, 31, 43]` degrees.

| Phase | MP4 SHA-256 | GIF SHA-256 |
| --- | --- | --- |
| Titanite | `f439b6591c6f2387b5f694b2f670eaa71d8a7dc79e124dc0091045465e78e82a` | `cc6404e688d9370e0dac015026d3cb17d35b446c652db8a14931441a706852ac` |
| Zircon | `c8ba16eb8e06196965797828925e8393195530cd9cb653de6aa4ae0c4620c465` | `bec8b294d8100702a5a89fdafc7c10fd3f8d96106bb11283398bf00fc3e74e7d` |

Each MP4 validates as 1024 square pixels, 144 frames, 12 fps, and 12 seconds.
The animation-only display intentionally does not redraw the static proof's
edge-overlay paths, so its continuity comes solely from the retained
kinematical and overlap fields; it does not hide any blur or a flattened
2-D image rotation.

## Verification

- `scripts/build_retained_near_depth.py` verifies the stored base recipe,
  source metadata, master product ID, and raw-array SHA-256 before rendering a
  new static derivative.
- `scripts/render_retained_near_depth_rotation.py` validates that the saved
  depth ledger and manifest bind the same master array, then uses bilinear
  directional sampling with `spatial_filter: none`.
- Focused unit and existing near-depth / kinematical workflow tests pass,
  together with Ruff, work-item validation, post-encode MP4 decode checks,
  GIF decode checks, and frame-count inspection.

## Review Gate

The computational and provenance gates are complete. Visual promotion remains
open until the Titanite and Zircon static proofs and rotations are reviewed by
the user alongside the earlier Ice Ih reference.

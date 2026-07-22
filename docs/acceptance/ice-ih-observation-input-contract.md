# Ice Ih detector observation input contract

Status: accepted source-bound observation-package proof, 2026-07-22.

## Objective

Create a portable, machine-verifiable object at the input side of a future
detector-pattern indexer: raw detector values, named camera geometry, explicit
preprocessing, a fixed S2 grid, a coverage mask, and integrity metadata. The
first instance deliberately remains identity-preprocessing only.

## Fixed package

| Element | Evidence |
| --- | --- |
| Input | Checked simulated Ice Ih `kinematical-detector.npy`, stored again inside the package as `observed-detector.npy`. |
| Geometry | The source 1536 x 2048 TSL detector recipe, including PC, tilts, pixel size, binning, and supersampling. |
| Preprocessing | One explicit `identity` stage. The package rejects unrecorded gain normalization, background correction, denoising, blur, or saturation handling. |
| Adapter | Bilinear gnomonic detector-to-fixed-S2 sampling into 1,946 sample-frame directions; 308 are covered. |
| Integrity | Canonical observation manifest, per-file SHA-256 checksums, array-shape checks, and an independent verifier. |

## Result

`local/observations/ice-ih-source-detector-identity-v0.1.0` has observation ID
`detector-observation-5565c09b908ee2c7`. It is the first source-bound example
of the observed-pattern side of the eventual contract, rather than another
simulation-only dictionary product.

## Claim boundary

- The input remains a source-bound simulated kinematical detector field, not
  an acquired EBSD pattern or an Ice Ih reference dataset.
- Identity preprocessing is a deliberate narrow contract, not a claim that
  real acquisition inputs require no background, saturation, or noise policy.
- The package does not perform a match or emit a phase/orientation result.
- `ebsdx-rs` does not yet consume this detector observation package; its
  current resource matcher accepts canonical full-S2 signals only.

## Reproduction

```bash
uv run python scripts/publish_ice_ih_source_observation.py \
  --output local/observations/ice-ih-source-detector-identity-v0.1.0
```

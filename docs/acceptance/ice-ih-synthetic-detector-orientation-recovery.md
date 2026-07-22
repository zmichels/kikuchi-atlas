# Ice Ih synthetic detector orientation recovery

Status: accepted end-to-end synthetic convention proof, 2026-07-21.

## Objective

Exercise the full project-owned path across more than the source identity:
canonical master, named detector geometry, partial-S2 sampling, and masked
candidate ranking. The selected orientations must be visibly distinct in
detector space and recover their exact cached entries without relaxing the
camera coverage or orientation convention.

## Fixed method

| Element | Evidence |
| --- | --- |
| Dictionary | Immutable `ice-ih-spherical-candidate-v0.1.3`, verified before use. |
| Master | The package's checked raw two-hemisphere stereographic master. |
| Orientation selection | Greedy maximum-minimum, sign-invariant quaternion separation beginning at the canonical identity entry. |
| Selected entries | `6577`, `15`, `297`, and `7144`. |
| Detector projection | Declared 1536 x 2048 TSL PC and tilt recipe, raw bilinear master sampling, no display tone or preprocessing. |
| Partial observation | The same declared camera geometry maps to 308 of 1,946 exact sample-frame S2 directions in every case. |
| Ranking | Per-coverage mean-centered normalized cosine, deliberately separate from the strict full-S2 package/Rust metric. |

All four targets are the top candidates with zero direct quaternion error. The
top scores are `0.999959208`, `0.999966178`, `0.999932829`, and `0.999790539`.

## Interpretation

This compact detector-and-ranking sheet closes the first deterministic loop
for multiple orientations. It shows why orientation recovery is meaningful in
the detector image, rather than only as a sparse spherical-vector plot.

## Claim boundary

- Each detector is a reprojection of the same canonical master used to build
  the candidate cache, so the result validates convention consistency rather
  than independent model agreement.
- No acquired pattern, calibration uncertainty, background correction,
  saturation policy, or noise process is included.
- The masked score cannot be compared across arbitrary camera masks and is not
  a current `ebsdx-rs` ranking capability.
- This does not measure phase discrimination or experimental indexing
  accuracy.

## Reproduction

```bash
uv run python scripts/run_ice_ih_synthetic_detector_orientation_recovery.py \
  --output local/dictionaries/ice-ih-synthetic-detector-orientation-recovery-v0.1.0
```

The append-only local bundle holds the four raw detector fields, their
partial-S2 signals and shared coverage mask, cached ranking records,
checksums, and `synthetic-detector-orientation-recovery.png`.

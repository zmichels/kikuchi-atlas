# Ice Ih off-grid detector refinement

Status: accepted held-out synthetic convention proof, 2026-07-21.

## Objective

Exercise the full detector-to-partial-S2 path with truths that are deliberately
absent from the frozen 13,155-entry Ice Ih candidate cache. Demonstrate the
useful next engine rung: a coarse masked-cache seed followed by local,
coverage-preserving refinement from the canonical master.

## Fixed method

| Element | Evidence |
| --- | --- |
| Dictionary | Immutable `ice-ih-spherical-candidate-v0.1.3`, verified before use. |
| Master and detector | Checked raw two-hemisphere kinematical master and the named 1536 x 2048 TSL detector recipe. |
| Held-out truths | Active right-handed `(1.7, -1.3, 2.2)` degree rotation vector composed with cache entries `6577`, `15`, and `297`; each resulting quaternion is confirmed absent from the coarse cache. |
| Partial observation | Raw detector intensity sampled bilinearly onto the same 308 covered directions of the fixed 1,946-direction sample-frame S2 grid. |
| Coarse ranking | Per-coverage mean-centered normalized cosine against the frozen cache. |
| Local refinement | A 4 degree cubical rotation-vector neighborhood about the coarse winner, sampled at 0.5 degree intervals and scored with the same coverage mask. |

## Result

All three held-out detector views improve under the local masked refinement:

| Base cache neighborhood | Coarse angular error | Refined angular error |
| --- | ---: | ---: |
| `6577` | 3.069 degrees | 0.346 degrees |
| `15` | 0.823 degrees | 0.528 degrees |
| `297` | 3.069 degrees | 0.412 degrees |

The retained graphic makes the point visually: visibly distinct raw detector
patterns seed a coarse cache ranking, then retain the same declared camera
footprint during the local improvement step. The append-only bundle keeps raw
detector fields, partial-S2 signals, coverage, full recovery records, figure,
and checksums together.

## Claim boundary

- Every held-out truth is reprojected from the same canonical master used by
  the cache. This validates a coordinate, signal, and local-search convention;
  it is not independent simulation agreement.
- No acquired EBSD pattern, detector calibration uncertainty, background
  correction, saturation model, noise model, phase competition, or experimental
  indexing-accuracy statistic is present.
- The masked metric is camera-footprint-specific. It is not interchangeable
  with the current strict full-S2 package/Rust ranker and does not yet define
  an `ebsdx-rs` detector-pattern interface.

## Reproduction

```bash
uv run python scripts/run_ice_ih_offgrid_detector_refinement.py \
  --output local/dictionaries/ice-ih-offgrid-detector-refinement-v0.1.0
```

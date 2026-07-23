# Ice Ih virtual-camera transfer proof

Status: accepted source-bound geometry-transfer proof, 2026-07-23.

## Objective

Close the first Ice Ih detector-geometry ladder by proving that one canonical
dictionary can support several separately declared detector geometries. Each
virtual camera must generate its own detector field, map it to its own covered
sample-frame S2 directions, and recover known cache entries without treating
different camera footprints as directly comparable scores.

## Fixed method

| Virtual camera | Changed declared quantity | Covered directions | Target entries | Result |
| --- | --- | ---: | --- | --- |
| Nominal | Checked source TSL geometry, PCz 0.60 | 308 / 1,946 | 6577 and 15 | Both first; scores 0.999959208 and 0.999966178 |
| Wide field | PCz 0.45 on the same pixel grid | 390 / 1,946 | 6577 and 15 | Both first; scores 0.999980844 and 0.999930183 |
| Narrow field | PCz 0.82 on the same pixel grid | 196 / 1,946 | 6577 and 15 | Both first; scores 0.999979449 and 0.999990817 |

The target orientations are identity entry `6577` and the most separated
sign-invariant cache entry `15`. The detector fields are raw bilinear
reprojections from the same verified Ice Ih master; each is then bilinearly
sampled back to the fixed S2 direction grid and ranked using masked,
mean-centered normalized cosine *within that profile*.

## Result

All six profile/target combinations recover the exact cache entry first. The
wide and narrow virtual views visibly change their detector pattern framing and
their coverage masks (390 and 196 directions, respectively), while retaining
the same named coordinate convention and specimen-frame transform.

## Claim boundary

- The three views are virtual declared geometries, not calibrated models of
  commercial cameras or a claim of inter-instrument transfer.
- Their scores are not compared against one another: each profile has a
  distinct detector field and coverage mask.
- No acquired EBSD pattern, detector distortion, background model, response
  function, noise model, phase competition, or indexing benchmark is included.

## Reproduction

```bash
uv run python scripts/run_ice_ih_virtual_camera_transfer.py \
  --output local/dictionaries/ice-ih-virtual-camera-transfer-v0.1.2
```

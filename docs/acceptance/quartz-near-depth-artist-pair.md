# Quartz Near-Depth Identity and Oblique Artist Pair Acceptance

- Current work item: [KIKU-T059](../work/KIKU-T059.md)
- Original 24 fps work item: [KIKU-T058](../work/KIKU-T058.md)
- Parent feature: [KIKU-F014](../work/KIKU-F014.md)
- Production state: complete and locally published
- Scientific claim: `presentation_only`

## Outcome

The accepted pair is now true 60 fps at 2048 x 2048 pixels for 24 seconds:
1,440 newly rendered orientations per edition. It retains the smooth grayscale
near-depth field treatment requested for downstream video art. The two editions
bind the same source field, optical treatment, x-axis motion, timing, raster,
and encoding profile. Their controlled difference is initial active
crystal-to-sample Bunge ZXZ orientation:

| Edition | Initial orientation | Visual role |
| --- | --- | --- |
| Identity | `(0, 0, 0)` degrees | Symmetric master/reference composition |
| Oblique | `(17, 31, 43)` degrees | Asymmetric diagonal composition matching the favored pre-rotation |

Every frame is directionally sampled from the retained spherical field. No
flat image is rotated, no motion interpolation is used, and no diffraction
simulation runs per frame. Each loop covers distinct angles in `[0, 360)` at
0.25 degrees per frame; playback returns from frame 1439 to frame 0 without a
stored duplicate endpoint.

## Source lock and claim boundary

| Input | Identity / SHA-256 |
| --- | --- |
| Phase | alpha-quartz, `COD-9012600` |
| Kinematical run | `kinematical-run-9288671de48c1eee` |
| Near-depth run | `near-depth-run-73fd2b3763870e92` |
| Retained master file | `20815afb63d6c293f4ea1e0316d7ba175f96bc1034b682d01e0cf17ebd64e606` |
| Retained overlap file | `6370001482b397036ba599dd3583ea6f3e1f3d18705aebbe918dbc840eec7aa7` |
| Depth-render ledger | `89f3e28ddc29a9353d0bdc24e41f766a0caec333077704391f96618294f22eb7` |
| Treatment recipe | `recipe-2ee98a8c0b29dafc` |

The retained scientific arrays are 1025 square per hemisphere/overlap field.
The 2048-square frames are direct bilinear spherical presentation samples of
those arrays; the raster dimensions do not imply additional simulation
resolution. These are kinematical, presentation-only near-depth science-art
fields, not detector acquisitions or dynamical master patterns.

## Retained invocations

Both commands use the same common arguments:

```text
uv run python scripts/render_retained_near_depth_rotation.py --phase-slug quartz --phase-label Quartz --kinematical-run local/atlas-extension-parity/kinematical/quartz/kinematical-run-9288671de48c1eee --near-depth-run local/atlas-extension-parity/near-depth/quartz/near-depth-run-73fd2b3763870e92 --frames 1440 --fps 60 --size 2048 --viewing-size 2048 --tile-rows 256 --workers 4 --frame-storage stream --export-profile artist-master
```

Identity-specific arguments:

```text
--initial-euler-bunge-deg 0 0 0 --edition-slug identity-60fps --output local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1
```

Oblique-specific arguments:

```text
--initial-euler-bunge-deg 17 31 43 --edition-slug oblique-17-31-43-60fps --output local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1
```

## Retained deliverables

Original production roots (historical invocation evidence):
`local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1`
and
`local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1`.

Current canonical publication packages:
`local/atlas/phases/quartz/products/quartz-direct-reflector-artist-master-x-axis/`,
`local/atlas/phases/quartz/products/quartz-near-depth-artist-master-identity-60fps/`,
and
`local/atlas/phases/quartz/products/quartz-near-depth-artist-master-oblique-17-31-43-60fps/`.

| Edition / artifact | Accepted properties | SHA-256 |
| --- | --- | --- |
| Identity ProRes master | 2048 x 2048, ProRes 422 HQ, 10-bit `yuv422p10le`, 60 fps, 1,440 frames, 24.000 s, 2,440,639,579 bytes | `8c45c5dc7c220ba80f21b7716205e1197c8e9137114baed26d0d54da796a7b5a` |
| Identity viewing copy | 2048 x 2048, H.264 High, 60 fps, 1,440 frames, 24.000 s, 49,363,433 bytes | `a7e3928ad7e4f2236f02af941092497159d8d4dd78bd9dcdc49636ca39060595` |
| Oblique ProRes master | 2048 x 2048, ProRes 422 HQ, 10-bit `yuv422p10le`, 60 fps, 1,440 frames, 24.000 s, 2,448,567,101 bytes | `e7b3ed4f9b18b2f11daf3267e65d3aab8c021a01e9b0289ff62d301dbab77ac2` |
| Oblique viewing copy | 2048 x 2048, H.264 High, 60 fps, 1,440 frames, 24.000 s, 49,017,050 bytes | `eb1f6220435a2ecc5603479a3c6f16dfd0b98aec335097169407421360b33bc4` |

Frames were streamed in order into each editing master with at most four render
tasks in flight; no PNG sequence was retained. Each output retains a frame-zero
`preview.png`, the exact `render-plan.json`, and a checksum/probe-bearing
`manifest.json`. The H.264 copy was derived from the validated ProRes master.

The side-by-side review-only historical evidence is retained at
`local/idealized-near-depth-rotation/quartz-artist-pair-60fps-v1/identity-left-oblique-right.png`
(identity left, oblique right), SHA-256
`27f3b33aa3d2192420f21ebd0948af948a233191549d4a7ad38e05296483c118`.

A concise recipient-facing source/render/pipeline note is retained beside that
proof as `STEVE-KIDDER-QUARTZ-60FPS-NOTES.txt`.

## Superseded local edition

The original 4096-square, 24 fps, 576-frame pair and its PNG sequences remain
available locally under the `quartz-identity-4k-24fps-24s-v1` and
`quartz-oblique-17-31-43-4k-24fps-24s-v1` output roots. They were not deleted;
the artifact catalog now points to the smoother 60 fps editions.

## Verification gates

| Gate | Result |
| --- | --- |
| Original-versus-tiled render parity | PASS: exact pixel equality at bounded test size |
| Frame production | PASS: two ordered streams of 1,440 freshly rendered 2048 x 2048 RGB frames; no temporal interpolation |
| Loop closures | PASS: fresh 360-degree render equals frame zero for each edition; fresh frame 1439 remains distinct |
| Controlled pair | PASS: sources, treatment, timing, and render contracts match; declared orientations and file identities differ |
| Representative visual review | PASS: both frame-zero proofs retain the intended grayscale treatment and are visibly distinct |
| Media facts and decode | PASS: two exact-60-fps ProRes masters and two full-resolution H.264 copies report 1,440 frames and decode completely |
| Focused tests, Ruff, tracker/catalog validation, and `git diff --check` | PASS |

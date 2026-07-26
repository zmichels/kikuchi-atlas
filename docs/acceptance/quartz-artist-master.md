# Alpha-Quartz 4K Direct-Reflector Artist Rotation Bonus Acceptance

- Work item: [KIKU-T056](../work/KIKU-T056.md)
- Parent feature: [KIKU-F006](../work/KIKU-F006.md)
- Production state: complete and locally published
- Scientific claim: `presentation_only`

## Outcome

The alpha-quartz direct-reflector composition is published as a seamless,
edit-friendly x-axis rotation for downstream video art. It reuses the accepted
11-path catalog and saved standard-width selection at active Bunge ZXZ
orientation `(17, 31, 43)` degrees. Each frame is rerendered from the rotated
crystal normals; the workflow never rotates a flattened source image and runs
no new master-pattern simulation.

Relative to the earlier quartz animation, the accepted edition increases the
square frame from 1024 to 4096 pixels, doubles the frame rate from 12 to 24 fps,
and doubles the duration from 12 to 24 seconds. One revolution therefore runs
at half the prior angular speed. The loop contains 576 distinct angles in
`[0, 360)` at 0.625 degrees per frame; playback returns from frame 575 to frame
0 without storing a duplicate endpoint.

## Retained invocation

```text
uv run python scripts/render_direct_reflector_rotation.py --phase quartz --axis x --frames 576 --fps 24 --size 4096 --export-profile artist-master --workers 4 --output local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1
```

The renderer writes `render-plan.json` before generation, resumes existing
frames only when that plan matches exactly, encodes each movie to a partial
path, decodes the partial file end to end, and only then publishes the final
movie name. `--reencode` permits a completed matching frame sequence to be
retained while the movie exports are rebuilt.

## Inputs and claim boundary

| Input | Identity / SHA-256 |
| --- | --- |
| Phase | alpha-quartz, `COD-9012600` |
| Source bundle | `quartz-hemisphere-standard-run-c8e68d027682d562` |
| Art-band catalog | `art-band-catalog-4f9fc8f1789aea65` |
| Selection | `tattoo-selection-e0757d38bd4bd549` |
| `art-band-catalog.json` | `81efa6933e06ffa46bc941e8f7d4213b767c701b306b3cd4d2cfab86bd3938d7` |
| `band-selection-ledger.json` | `11498dbd4895a0767bbc931cd4a8daddc8605d4629f0ddceecb92c02a31854ce` |

This is idealized direct-reflector science art made from crystallographically
sourced plane traces. It is not a dynamical EBSD intensity simulation, an
acquired detector pattern, or a calibrated instrument response.

## Retained deliverables

Original production root (historical invocation evidence):
`local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1`

Current canonical publication package:
`local/atlas/phases/quartz/products/quartz-direct-reflector-artist-master-x-axis/`

| Artifact | Accepted properties | SHA-256 |
| --- | --- | --- |
| `quartz-x-axis-rotation-artist-master.mov` | ProRes 422 HQ, 4096 x 4096, 10-bit `yuv422p10le`, 24 fps, 576 frames, 24.000 s, Rec.709 color matrix, 1,114,663,430 bytes | `f64e56e0352b58c50b83d0d76b675283057b82f48369e1fe6cb210e445bd24a0` |
| `quartz-x-axis-rotation-viewing-copy.mp4` | H.264 High, 2048 x 2048, `yuv420p`, 24 fps, 576 frames, 24.000 s, explicit Rec.709 limited-range signaling, 25,722,314 bytes | `83f86404867bbd957e46c2851d02f7e560c3f67536aaa93ff14a264dfb5b5fe0` |
| `frames/frame-0000.png` through `frame-0575.png` | 576 sequential 4096 x 4096 RGB PNGs, each rendered at 2x supersampling | inventoried by exact sequential-name and image-property validation |
| `manifest.json` | source hashes, selected members, rotation contract, render properties, export hashes, and bounded `ffprobe` facts | retained with product |

## Verification gates

| Gate | Result |
| --- | --- |
| Frame inventory | PASS: 576 sequential 4096 x 4096 RGB PNGs |
| Loop closure | PASS: freshly rendered frame 576 is pixel-identical to frame 0; retained frame 575 is distinct |
| Representative visual review | PASS: frames 0, 144, and 575 have sharp hierarchy, clean circular clipping, and distinct orientations |
| ProRes full decode | PASS: `ffmpeg -v error` returned no errors |
| H.264 full decode | PASS: `ffmpeg -v error` returned no errors |
| Focused rotation tests | PASS: `3 passed` |
| Historical standard export profile | PASS: bounded MP4/GIF smoke render and full MP4 decode |
| Ruff | PASS: `All checks passed!` |
| Work-item validation | PASS: `Validated 71 work items in docs/work` before this acceptance file changed no tracker relationships |
| Product-catalog validation | PASS |
| `git diff --check` | PASS |

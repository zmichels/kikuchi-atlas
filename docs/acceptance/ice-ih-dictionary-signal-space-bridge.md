# Ice Ih dictionary signal-space bridge

Status: accepted explanatory proof, 2026-07-21.

## Purpose

The Ice Ih spherical dictionary uses a small set of explicitly declared
signal spaces. A raw cache-vector diagnostic can look unfamiliar because it
is not intended to resemble a detector pattern. This artifact makes that
distinction inspectable rather than relying on an implied mental model. Its
`v0.1.1` render also overlays the exact declared detector's angular footprint
on the sample-frame sphere.

## Representation map

| Panel | What it is | Frame / geometry | Role today |
| --- | --- | --- | --- |
| Detector projection | Kinematical image-like Kikuchi pattern | Detector pixels | Source visualization only. It is not accepted by the current ranker. |
| Stereographic master | Upper and lower hemisphere intensity fields | Crystal frame | Raw directional source for orientation candidates and refinement. |
| S2 cache signal | 1,946 scalar samples at fixed directions | Sample frame | Exact input to normalized-cosine candidate ranking. The teal region is the declared detector footprint; the cross is its projection-center ray. |

The third panel is intentionally plotted as longitude/latitude samples. It is
an inspectable numerical feature vector, so it is sparse and does **not** look
like an EBSD detector image. The active crystal-to-sample orientation maps the
master field onto those directions as

`I_sample(s) = I_crystal(R_cs^-1 s)`.

## Explicit nonclaims

- The bridge does not calculate or display Hough/Radon space.
- It does not implement detector-to-sphere projection, calibration,
  background/saturation treatment, masking, or interpolation policy.
- The teal footprint is geometry only: it does not resample or compare any
  detector pixel intensity.
- It does not accept acquired detector pixels as dictionary input.
- It is not an acquired-EBSD indexing or accuracy validation.

Those missing pieces are deliberate adapter gates, not silent assumptions in
the canonical-S2 ranker.

## Reproduction

With the checked source run and Ice Ih `v0.1.3` dictionary available under
`local/`, publish a new destination with:

```bash
uv run python scripts/render_ice_ih_dictionary_signal_space_bridge.py \
  --output local/dictionaries/ice-ih-signal-space-bridge-v0.1.1
```

The command verifies the package, verifies the detector and master PNG hashes
against their source run manifest, then writes:

- `ice-ih-signal-space-bridge.png`
- `signal-space-bridge.json` with the dictionary identity, claim boundary, and
  source-file inventory
- `checksums.json`

The `v0.1.1` record also binds the exact detector recipe and records its PC,
tilts, shape, sample-frame footprint vertices, and projection-center ray.

The destination is append-only: an existing output is refused rather than
silently overwritten.

# Ni 24 dB Hough preprocessing sensitivity v0.1

This support study makes one otherwise hidden modeling choice inspectable. It
holds the same seven acquired Ni calibration patterns, source inventory,
published Bruker PC, 50-reflector selection, CPU Hough path, and reference
master constant. Only preprocessing changes.

The study compares three fixed variants:

1. raw patterns;
2. static-background division; and
3. static-background division followed by dynamic-background division.

All orientations are compared with the third variant after cubic symmetry
reduction. Those values are **agreement with a declared reference variant**,
not errors against independently measured truth.

## Reproduce

```bash
uv run python scripts/verify_ni_gain24db_reference_pack.py --allow-download

uv run --with pyebsdindex==0.3.9.2 \
  python scripts/run_ni_gain24db_preprocessing_sensitivity.py \
  --output local/reference-packs/ni-gain24db-preprocessing-sensitivity-v0.1
```

The runner verifies the same 26-file source inventory used by the baseline,
checks the linked baseline recipe digest, and rejects any change from the
recipe-pinned results.

## Checked result

The 2026-07-24 run used recipe digest
`f2af9873c82afeb23a19b8ecef4434316c245bcbbe1eb41bc455d1696b707e20`.

| Variant | 7/7 indexed | Mean fit | Mean confidence | Mean / max cubic-symmetry-reduced delta to all-division |
|---|---:|---:|---:|---:|
| Raw | yes | 0.294912 | 0.741434 | 0.164918° / 0.368841° |
| Static division | yes | 0.261390 | 0.752934 | 0.049757° / 0.234153° |
| Static + dynamic division | yes | 0.267316 | 0.757950 | 0.000000° / 0.000000° |

![Ni fixed Hough preprocessing sensitivity](assets/ni-gain24db-preprocessing-sensitivity-v0.1.png)

The blue traces in the figure are geometrical simulations from the Hough
solutions. The figure visualizes an explicit protocol comparison; it does not
validate the orientations or elevate fit/confidence into universal pattern
quality metrics.

## Contents

| Material | Purpose |
|---|---|
| [Study recipe](../../recipes/reference-pack/ni-gain24db-preprocessing-sensitivity-v0.1.yml) | Pins the exact three variants, common geometry, Hough route, expected metrics, and nonclaims. |
| [Runner](../../scripts/run_ni_gain24db_preprocessing_sensitivity.py) | Verifies the source inventory, performs the fixed comparison, emits JSON, a figure, and output checksums. |
| [Shareable derived figure](assets/ni-gain24db-preprocessing-sensitivity-v0.1.png) | Attributed CC BY 4.0 visual derivative; raw EBSD source files remain upstream. |
| [Baseline pack](ni-gain24db-calibration-hough-v0.1.md) | Supplies the public source pointer, source inventory, master/geometry provenance, and reference baseline. |
| [Acceptance record](../acceptance/ni-gain24db-preprocessing-sensitivity.md) | Retains the result and its scientific interpretation boundary. |

## Claim boundary

- The result is source-bound and has no independent orientation truth.
- Hough fit and confidence are diagnostics from this route, not a broad ranking
  of preprocessing methods or detectors.
- The comparison does not vary gain, instrument, vendor software, geometry,
  reflector set, or phase.
- The compact seven-pattern study is an auditable support slice, not an
  inter-instrument benchmark.

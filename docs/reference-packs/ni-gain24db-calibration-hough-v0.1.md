# Ni 24 dB calibration-pattern Hough Reference Pack v0.1

This lightweight pack is a reproducible **source-bound** baseline for the
openly licensed Ni gain dataset exposed by Kikuchipy. It is useful as a small,
inspectable acquired-pattern test path: source integrity, declared geometry,
preprocessing, reflector selection, and a Hough result all remain explicit.

It does not redistribute the source files. The tracked
[source inventory](../../reference-packs/ni-gain24db-calibration-hough-v0.1.source-inventory.json)
pins their 26 names, sizes, and SHA-256 digests (114,787,781 bytes in total),
while Kikuchipy downloads them from its documented Zenodo-backed source only
when requested.

## Contents

| Material | Purpose |
|---|---|
| [Recipe](../../recipes/reference-pack/ni-gain24db-calibration-hough-v0.1.yml) | Pins source loaders, phase/master, published PC, preprocessing, reflector selection, expected aggregate Hough result, and nonclaims. |
| [Source inventory](../../reference-packs/ni-gain24db-calibration-hough-v0.1.source-inventory.json) | External-data pointer, CC BY 4.0 attribution, and exact source-byte fingerprints. |
| [Verifier](../../scripts/verify_ni_gain24db_reference_pack.py) | Fetches only on `--allow-download`, resolves both Kikuchipy loaders, and rejects missing, extra, resized, or checksum-mismatched cached files. |
| [Baseline runner](../../scripts/build_ni_gain24db_reference_baseline.py) | Reproduces the seven-pattern CPU Hough baseline with `pyebsdindex==0.3.9.2`. |
| [Acceptance record](../acceptance/ni-gain24db-reference-pack-intake.md) | Documents source inspection, result, and the scientific claim boundary. |

## Reproduce

```bash
# Downloads only if the source is absent from the local Kikuchipy cache.
uv run python scripts/verify_ni_gain24db_reference_pack.py --allow-download

# Optional baseline: outputs only into ignored local/.
uv run --with pyebsdindex==0.3.9.2 \
  python scripts/build_ni_gain24db_reference_baseline.py \
  --output local/reference-packs/ni-gain24db-calibration-hough-v0.1
```

The checked 2026-07-24 reproduction indexed 7/7 calibration patterns with
mean fit `0.26731613278388977`, mean confidence
`0.7579495310783386`, and 50 selected reflectors. The recorded recipe digest
is `bb0a99ead5bb5e6b5a6a646eb9b7956fd469bbaae2be8cdc57ffb66b3d40fa5c`.

## Source and method

- The source is the 24 dB (`number=10`) Ni gain acquisition and seven matching
  calibration patterns: NORDIF UF-1100, 20 keV, CC BY 4.0.
- The phase master is Kikuchipy's documented 20 keV, 401 × 401 uint8
  stereographic, EMsoft-origin convenience master.
- The declared Bruker PC is `[0.41835389, 0.22080713, 0.5048758]`, copied from
  the cited Kikuchipy hybrid-indexing workflow before its dynamical refinement.
- Calibration preprocessing is static-background division then
  dynamic-background division; the fixed Hough path selects 50 Ni reflectors.

## Claim boundary

- This is a source-bound calibration reproduction—not independently measured
  orientation ground truth or a phase-identification benchmark.
- It does not re-run nonlinear PC optimization or dynamical refinement.
- The uint8 master is a documented convenience representation, not the
  original float32 EMsoft simulation.
- It establishes neither vendor-format compatibility nor inter-instrument
  transfer.

## Sources

- [Kikuchipy Ni gain dataset API](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.data.ni_gain.html)
- [Kikuchipy Ni calibration-pattern API](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.data.ni_gain_calibration.html)
- [Kikuchipy Ni small master-pattern API](https://kikuchipy.org/en/stable/reference/generated/kikuchipy.data.nickel_ebsd_master_pattern_small.html)
- [Kikuchipy hybrid-indexing workflow](https://kikuchipy.org/en/latest/tutorials/hybrid_indexing.html)

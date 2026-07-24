# Kikuchi Lab Reference Packs

Reference Packs join an acquired-pattern source, declared observation semantics,
a cited master resource, a reproducible processing recipe, and a bounded
baseline result. They are deliberately not another vendor container format or a
generic accuracy leaderboard.

Each released pack retains source provenance and integrity without duplicating
large upstream data in this repository. Raw data remain with their original
provider under the provider's stated terms; this repository supplies a durable
source pointer, exact inventory checksums, a recipe, a verifier, and a
reproduction path.

| Pack | Phase | Status | Boundary |
|---|---|---|---|
| [Ni 24 dB calibration Hough v0.1](ni-gain24db-calibration-hough-v0.1.md) | Ni, Fm-3m | released | source-bound Hough baseline, not independent orientation truth |
| [Ni 24 dB preprocessing sensitivity v0.1](ni-gain24db-preprocessing-sensitivity-v0.1.md) | Ni, Fm-3m | released | three fixed preprocessing variants on the same seven patterns, not a universal preprocessing ranking |

## Use a pack

First fetch only from the upstream provider when the source is absent, then
verify its exact raw-file inventory:

```bash
uv run python scripts/verify_ni_gain24db_reference_pack.py --allow-download
```

Then reproduce the pack's optional CPU Hough baseline into an ignored local
evidence directory:

```bash
uv run --with pyebsdindex==0.3.9.2 \
  python scripts/build_ni_gain24db_reference_baseline.py \
  --output local/reference-packs/ni-gain24db-calibration-hough-v0.1
```

The runner fails if its source dimensions, selected reflector count, indexed
count, or recipe-pinned aggregate result changes. Its local output includes a
numeric report, diagnostic overlay, and output checksums.

## Protocol studies

Reference Packs may also contain explicitly bounded support studies. The first
one holds the Ni source, geometry, reflector set, and Hough route constant and
compares raw, static-background division, and static-plus-dynamic-background
division. It reports the resulting Hough diagnostics and cubic-symmetry-reduced
orientation changes relative to the declared all-division reference; it does
not call one method generally superior.

```bash
uv run --with pyebsdindex==0.3.9.2 \
  python scripts/run_ni_gain24db_preprocessing_sensitivity.py \
  --output local/reference-packs/ni-gain24db-preprocessing-sensitivity-v0.1
```

## Release boundary

No raw source payload, vendor reader, detector-control code, claims of
inter-instrument transfer, or general ranking benchmark is distributed here.
The tracked files make the narrow result inspectable and reproducible without
mistaking it for a universal indexing engine.

# Kikuchi Atlas

The Atlas is the local-first publication layer for Kikuchi Lab. It organizes
phase-specific visual, vector, motion, and printable products while preserving
the source and claim boundaries that made each product possible.

## Browse locally

Build the static pages from tracked phase/product data:

```bash
uv run python scripts/build_atlas.py
open docs/atlas/site/index.html
```

The generated pages link to the ignored `local/` product store when the media
are available on this machine. A missing local artifact is shown as unavailable;
it never means the tracked source, recipe, or phase record has disappeared.

## Atlas states

- `tracked-source` — a checked-in source record and CIF passed source
  verification. It may still lack a particular visual product.
- `candidate-reference` — an intentionally named, citable prospective structure.
  It is visible for planning but cannot be captioned as a rendered,
  dictionary-ready, or indexing-validated phase.

The initial candidate set adds an An52 plagioclase reference, 2M1 muscovite,
and ambient diopside. The exact named materials matter: plagioclase and
clinopyroxene are families, not one universal structure apiece.

`PHASE_REGISTRY.yml` is the data source. The local artifact catalog remains at
[`../products/ARTIFACT_CATALOG.yml`](../products/ARTIFACT_CATALOG.yml).

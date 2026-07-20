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

The generated site has two entry points:

- `index.html` is phase-first. Each phase has the same named product matrix
  before its individual products.
- `products.html` is product-first. It filters the curated release set by phase,
  product family, medium, and free text.

Every card opens its actual SVG, PNG, MP4, or STL first. Its local bundle and
provenance record are secondary links for reproduction and audit. A missing
ignored `local/` artifact is shown as unavailable; it never means the tracked
source, recipe, or phase record has disappeared.

## Product model

`PRODUCT_REGISTRY.yml` is the relational, curated product table. A product can
belong to more than one phase and more than one product family. The current
release treats these as common core families for every source-backed phase:

- direct-reflector hemisphere template;
- orientation variation;
- x-axis rotation study; and
- printable reflector-ridge globe.

Richer intensity-master, depth-field, intensity-relief, and tattoo products
are explicit extensions. They may be incomplete for a phase, but they cannot
masquerade as a different core product type. Candidate phase references show
the same matrix as `blocked by source promotion` until their source contract is
accepted.

## Atlas states

- `tracked-source` — a checked-in source record and CIF passed source
  verification. It may still lack a particular visual product.
- `candidate-reference` — an intentionally named, citable prospective structure.
  It is visible for planning but cannot be captioned as a rendered,
  dictionary-ready, or indexing-validated phase.

The initial candidate set adds an An52 plagioclase reference, 2M1 muscovite,
and ambient diopside. The exact named materials matter: plagioclase and
clinopyroxene are families, not one universal structure apiece.

`PHASE_REGISTRY.yml` names exact phases and source state.
`PRODUCT_REGISTRY.yml` names individual curated products and their relations.
The older [`../products/ARTIFACT_CATALOG.yml`](../products/ARTIFACT_CATALOG.yml)
remains a compact publication-anchor list and is cross-checked during the
Atlas build; it is not the browse database.

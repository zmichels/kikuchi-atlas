# Kikuchi Lab repository map

Kikuchi Lab is a local-first scientific-art workbench.  Its durable unit is a
recipe and a provenance-bearing bundle—not a screenshot or a particular
worktree.

## Core flow

```text
phases/ + reference/catalog/
        │  tracked crystal sources and source records
        ▼
recipes/ ───────────────► src/kikuchi_lab/
                             │
                             ├── sources/, reflectors/, kinematical/
                             │   scientific inputs and bounded simulations
                             ├── spherical_intensity/, near_depth/
                             │   saved scalar fields and presentation layers
                             ├── dictionary/
                             │   portable S2 dictionary resources and validators
                             ├── art_products/, reflector_globe/, relief/
                             │   vector art, animation, and printable geometry
                             └── workflows/, cli/
                                  reproducible publication boundaries
        │
        ▼
scripts/                 explicit render and verification entry points
        │
        ▼
local/                    ignored, machine-local immutable product bundles
```

`docs/products/ARTIFACT_CATALOG.yml` is the stable index of the selected
local products. Run `uv run python scripts/product_status.py` to see which
cataloged media are present in the current checkout without confusing a
missing local render with a missing recipe or source record.

## Product tiers and claim boundaries

| Tier | Main modules | What it represents | What it does not represent |
| --- | --- | --- | --- |
| Dynamical reference | `sources/`, `dynamical_master_rotation.py` | bounded ebsdsim-derived master/presentation proofs | a calibrated detector acquisition or an indexing engine |
| Kinematical master | `kinematical/`, `spherical_intensity/` | reproducible simulated fields and orientation changes | a dynamical intensity prediction |
| Direct-reflector art | `reflectors/`, `art_products/` | crisp, crystallographically sourced plane traces and bands | an EBSD pattern acquisition |
| Retained near-depth field | `near_depth/` | additive, no-blur presentation of a saved simulated field | an independent physical simulation |
| Printable geometry | `habit/`, `relief/`, `reflector_globe/` | source-tied STL products with mesh checks | a material/process acceptance claim |
| Spherical dictionary fixture | `dictionary/`, `recipes/dictionaries/` | explicit-orientation contract and ranking interoperability proof | a calibrated detector library or indexing performance result |

Keep the tier in a product's manifest and public caption. A visually
compelling presentation derivative must not silently inherit a stronger
scientific claim from its source product.

## Stable entry points

- `recipes/` is the canonical input surface.
- `src/kikuchi_lab/` holds reusable engine code; scripts should orchestrate it
  rather than duplicate scientific logic.
- `scripts/render_dynamical_master_rotation.py`,
  `scripts/render_direct_reflector_depth_rotation.py`, and
  `scripts/render_retained_near_depth_rotation.py` are the principal motion
  renderers.
- `scripts/validate_work_items.py` validates planning links;
  `scripts/product_status.py` validates the product catalog's static contract.
- `scripts/build_forsterite_spherical_dictionary_fixture.py` and
  `scripts/verify_spherical_dictionary.py` build and independently validate
  the first portable S2 resource. See `docs/dictionaries/README.md` for the
  strict claim boundary.
- `local/` is deliberately ignored: it contains generated pixels, video,
  meshes, arrays, and manifests that are reproducible from tracked inputs but
  are not assumed to exist in every clone.

## Integration boundary

The stable code line unifies the dynamical-master and spherical-intensity
lineages. The separately committed `codex/spherical-intensity-workbench`
branch is an experimental MTEX/S2 density workbench; it is intentionally not
part of the stable product surface until its separate acceptance gate is met.
See `docs/architecture/INTEGRATION_HISTORY.md` for the tracker-ID collision
resolution and preservation rationale.

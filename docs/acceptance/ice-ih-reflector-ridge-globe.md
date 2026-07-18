# Ice Ih reflector-ridge globe acceptance

Status: **DONE_WITH_CONCERNS**. The deterministic, printer-neutral mesh bundle is
accepted by automated validation and by a visual review of its fixed preview. No
physical print, slicer import, repair result, or slicer success is claimed.

## Accepted bundle

- Build ID: `reflector-ridge-globe-build-8b641d5b8a8110ab`
- Bundle: [published bundle](../../local/ice-reflector-globes/reflector-ridge-globe-build-8b641d5b8a8110ab)
- Catalog ID: `reflector-catalog-2ca281743468ecab`
- Recipe ID: `reflector-ridge-recipe-40e658077c46b698`
- Field ID: `reflector-ridge-field-1752c00dbcd8b3b7`
- Topology ID: `icosphere-b542bf2969717758`

The source-compatible catalog retains 15 selected reflector members across four
tie-preserving cohorts. The field is evaluated at all 163842 subdivision-7
icosphere directions and exported with 327680 unchanged indexed triangles.

## Geometry validation

The single body is watertight and consistently wound, has positive volume, no
duplicate or degenerate triangles, and preserves the positive radial-bijection
contract. Its configured and validated radii span 40.0–43.0 mm: an 80.0 mm base
diameter with outward-only relief bounded by 3.0 mm. Bounds are
`[-43.0, -43.0, -43.0]`–`[43.0, 43.0, 43.0]` mm. The radial certificate minimum
is `4.554770495159523`, above the `6.4e-08` tolerance.

The fixed preview was visually reviewed: the raised blue corridors are
continuous and legible around the sphere, with no obvious missing surface patch
or seam. This preview review is not a slicer or physical-print inspection.

## Inventory and reproducibility

The bundle contains exactly six files. The manifest SHA-256 is
`8223dec397a73a5ab2e29b164da160403f984ae77fe855a9a1dbc66f15157dbe`.

| File | SHA-256 |
| --- | --- |
| `ice-ih-reflector-ridges.stl` | `2245d44a5d8a4afb5791ee66dcbb0c48a955837dde994f8d7daa28dcc388d12a` |
| `ice-ih-reflector-ridges-preview.png` | `f54d5139036787d8c8c85ee8ce9ad95e44c3320527e87028f6c6dc452609acd2` |
| `ridge-field.npz` | `1412c69e96927ca86980205fc3ae4fece1b023267e513bfcc584dcb9ad8b987b` |
| `ridge-ledger.json` | `be14b9e8041dc2d1b9cab07977e42eef476ce07d5ff089d4147a4c4e62b3d6a9` |
| `mesh-validation.json` | `53d55d8a1d6ec7569430e868f5ccc7d7df6947fb75323c8b60b58fc3b76f0ba7` |

Focused red/green evidence: before implementation no reflector-globe workflow
existed; after implementation, `uv run pytest tests/unit/test_reflector_globe_bundle.py
tests/integration/test_ice_reflector_globe.py -q` passed `2 passed`. The real CLI
smoke build regenerated the catalog at `/tmp/ice-reflector-catalog-smoke` and
published this bundle with `kikuchi-lab reflector-globe build`.

# Ice Ih reflector-ridge globe acceptance

Status: **AUTOMATED_EVIDENCE_RECORDED**. The deterministic, printer-neutral mesh
bundle passed automated validation. User visual review of the fixed preview is
pending explicit approval. No physical print, slicer import, repair result,
manufacturability result, or slicer success is claimed.

## Product boundary

This is a reflector-defined, analytic raised-ridge mesh made from the selected
reflector catalog; it is not a dynamical EBSD intensity simulation. It is a
separate product from the intensity-relief globe and does not use a sampled
intensity master for its geometry.

## Accepted bundle

- Build ID: `reflector-ridge-globe-build-cf6eb051b29a78f8`
- Bundle: [published bundle](../../local/ice-reflector-globes/reflector-ridge-globe-build-cf6eb051b29a78f8)
- Source structure ID: `COD-1572233-O-sublattice`
- Catalog ID: `reflector-catalog-2ca281743468ecab`
- Recipe ID: `reflector-ridge-recipe-40e658077c46b698`
- Field ID: `reflector-ridge-field-1752c00dbcd8b3b7`
- Topology ID: `icosphere-b542bf2969717758`

The source-compatible catalog retains 15 selected reflector members from
`COD-1572233-O-sublattice` across four tie-preserving cohorts. The field is
evaluated at all 163842 subdivision-7 icosphere directions and exported with
327680 unchanged indexed triangles.

## Generated geometry evidence

The published binary STL, reloaded after float32 serialization, is one
watertight and consistently wound positive-volume body with no duplicate or
degenerate triangles, and preserves the positive radial-bijection contract.
Its measured radii are `40.000008012665894`–`42.999992026904316` mm, within the
configured 40.0–43.0 mm interval for an 80.0 mm base diameter and outward-only
relief bounded by 3.0 mm. Its measured bounds are
`[-42.9999885559082, -42.9999885559082, -42.9999885559082]`–
`[42.9999885559082, 42.9999885559082, 42.9999885559082]` mm. The radial
certificate minimum is `4.5547612162859155`, above the `6.4e-08` tolerance.

The fixed preview is generated evidence only. Its visual readability is pending
explicit user approval; it has not been used as a slicer or physical-print
inspection.

## Inventory and reproducibility

The bundle contains exactly six files. The manifest SHA-256 is
`8157f45ad9efb91e5debf835af2e077b007403eb149c137100d4faa71fd901d1`.

| File | SHA-256 |
| --- | --- |
| `ice-ih-reflector-ridges.stl` | `42a4b9dc7a779245a5f35cb5755988481ed1a689a84042427458049cbeb43a2d` |
| `ice-ih-reflector-ridges-preview.png` | `3b0278a961d66e42a078a0aad4fa907668ec69ca1562f615959c323ca28d28a5` |
| `ridge-field.npz` | `a5b3523a4bde96eb300cad4fd8bd2638b9b3fe298528296abefabcbf2722d6b8` |
| `ridge-ledger.json` | `389fc209f898d61c541cb8528841823f25585d93901e4be8f79db659a413c5cf` |
| `mesh-validation.json` | `4a2015595baf0e22ccf158e3d725e92cb2c6cd9c451307bab83a4dc835309d45` |

Focused red/green evidence: before implementation no reflector-globe workflow
existed; after implementation, `uv run pytest tests/unit/test_reflector_globe_bundle.py
tests/integration/test_ice_reflector_globe.py -q` passed `2 passed`. The
regression reloads the published STL and checks its measured radial bounds,
watertightness, winding, and single-body status. The real CLI smoke build
regenerated the catalog and published this bundle with `kikuchi-lab
reflector-globe build`.

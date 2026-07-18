# Ice Ih intensity-relief globe acceptance

Status: **AUTOMATED_EVIDENCE_RECORDED**. The separate stereographic-master
intensity globe passed deterministic automated validation. User visual review
of its fixed preview is pending explicit approval. This is not a physical-print,
slicer-import, repair, or manufacturability claim.

## Product boundary

This is an intensity-relief mesh sampled from the raw kinematical master over
its valid stereographic disk domain. It is separate from the reflector-defined
ridge product and does not use its reflector catalog to define the relief.

## Accepted bundle

- Build ID: `ice-intensity-globe-build-9c2b6b2fdb845eea`
- Bundle: [published bundle](../../local/ice-intensity-globes/ice-intensity-globe-build-9c2b6b2fdb845eea)
- Product kind: `intensity_relief`
- Master product ID: `kinematical-64f419545bedcd0c`
- Recipe ID: `ice-intensity-globe-recipe-769cc72ff0cb9891`
- Field ID: `ice-intensity-field-bd3fb3ef2e9c6fc1`
- Topology ID: `icosphere-b542bf2969717758`

The field is sampled directly from the both-hemisphere Ice kinematical
stereographic master `kinematical-64f419545bedcd0c` over its published
`X^2 + Y^2 <= 1` disk, with upper ownership of the true equator; it is not a
Lambert field and does not use reflector-defined ridge data. A single 1st–99th
percentile, gamma-1.0 map is applied across both hemispheres using only disk
samples. The true disk-equator diagnostic has upper ownership, four exact
grid-boundary samples, and zero residual. The bundle has 163842 vertices and
327680 unchanged indexed triangles.

The standalone intensity ledger and manifest retain the master array checksum,
tracked structure ID/checksum and source/simulation settings, kinematical recipe
ID, complete projection ledger, available reflector/catalog evidence, sampling
contract, valid disk domain, and seam diagnostics. No live simulation object is
required to audit the source-to-mesh chain.

## Generated geometry evidence

Automated validation found one watertight, consistently wound, positive-volume
body, with Euler characteristic 2 and no duplicate or degenerate triangles.
The reloaded binary STL radii are `40.00011778863592`–`42.9999917465903` mm.
Its reloaded bounds are `[-42.9999885559082, -42.9999885559082,
-42.9999885559082]`–`[42.9999885559082, 42.9999885559082,
42.9999885559082]` mm and the radial-certificate minimum is
`4.575064230158891`, above the `6.4e-08`
tolerance.

The fixed preview is generated evidence only. Its visual readability is pending
explicit user approval; it is not evidence of slicer behavior or a physical
print.

## Inventory and reproducibility

The bundle contains exactly six files. A second output-root build produced the
same build and field IDs and identical file records.

| File | SHA-256 |
| --- | --- |
| `ice-ih-intensity-relief-preview.png` | `2d356aacc4f40d0906cbf8105173745cb45384602c0784557c0bb6de19f87f30` |
| `ice-ih-intensity-relief.stl` | `7fe481b24402fa4b9a40422d6def6ddca74594bed4ff1b0393c4bb5d30c68bb7` |
| `intensity-field.npz` | `ad64b5bd18f0c7ba2d151abcfc5ea0481e4d57ea0cc2fa1af37fcaef94ce8fea` |
| `intensity-ledger.json` | `4afba73322c4e8f72486783bc391df697de5d28c6fe0a32a9663f4afef9f084d` |
| `mesh-validation.json` | `884ca8f90a104ceaf72d9775036a44812109462a4e66ede752f2a16d5efb790b` |
| `intensity-globe-manifest.json` | `8f10e9ffdf87991d1bbd824759e3786edc71e5cef45fc08384a65f4986cac291` |

Red/green evidence: the initial focused run failed at collection because
`kikuchi_lab.ice_globe` did not exist. After implementation,
`uv run pytest tests/scientific/test_ice_intensity_field.py
tests/integration/test_ice_globe_workflows.py tests/scientific/relief
tests/integration/test_relief_globe_workflow.py -q` passed. It verifies the
master-derived source kind, separation from the reflector-ridge product kind,
and preserves the existing forsterite relief suite.

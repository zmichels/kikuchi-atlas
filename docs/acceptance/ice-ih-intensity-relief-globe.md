# Ice Ih intensity-relief globe acceptance

Status: **DONE_WITH_CONCERNS**. The separate stereographic-master intensity
globe is accepted by deterministic automated validation and visual review of
its fixed preview. This is not a physical-print, slicer-import, repair, or
manufacturability claim.

## Accepted bundle

- Build ID: `ice-intensity-globe-build-f44fb9a91e5dad85`
- Bundle: [published bundle](../../local/ice-intensity-globes/ice-intensity-globe-build-f44fb9a91e5dad85)
- Product kind: `intensity_relief`
- Recipe ID: `ice-intensity-globe-recipe-769cc72ff0cb9891`
- Field ID: `ice-intensity-field-fdb6652eb1dad347`
- Topology ID: `icosphere-b542bf2969717758`

The field is sampled directly from the both-hemisphere Ice kinematical
stereographic master with upper ownership of the equator; it is not a Lambert
field and does not use reflector-defined ridge data. A single 1st–99th
percentile, gamma-1.0 map is applied across both hemispheres. The bundle has
163842 vertices and 327680 unchanged indexed triangles.

## Geometry and preview review

Automated validation found one watertight, consistently wound, positive-volume
body, with Euler characteristic 2 and no duplicate or degenerate triangles.
The reloaded binary STL radii are `40.00010557700384`–`42.99999154763094` mm.
Its reloaded bounds are `[-42.9999885559082, -42.9999885559082,
-42.9999885559082]`–`[42.9999885559082, 42.9999885559082,
42.9999885559082]` mm and the radial-certificate minimum is
`4.5744198191033725`, above the `6.4e-08`
tolerance.

The fixed preview was visually reviewed: the intensity-derived relief is
continuous across the visible sphere, with strong equatorial structure and no
obvious missing surface patch. This visual check remains only a preview review,
not a claim about slicer behavior or a physical print.

## Inventory and reproducibility

The bundle contains exactly six files. A second output-root build produced the
same build and field IDs and identical file records.

| File | SHA-256 |
| --- | --- |
| `ice-ih-intensity-relief-preview.png` | `e9190fb739eaa528c7f51ca29527d2e9c3ff96ddea50c9128ac41b4184a4722d` |
| `ice-ih-intensity-relief.stl` | `57c6d1c45720180e2c6cfd2477347b884a8ba2fea92292c2ba6bd27f1ce656ff` |
| `intensity-field.npz` | `754ade35e858aea12e31a2e29c84325f7b1f9865ae76ddd936f23c4fe971fabd` |
| `intensity-ledger.json` | `afc470f7e631e72a4ffe9cd104fbd0d227cba4ad758d186bba9c7e376f2c2188` |
| `mesh-validation.json` | `5d177914e610d3ba81bcf97f8fab78cc749be0d37747f95524971d3dd63028f6` |
| `intensity-globe-manifest.json` | `54a901da9f6a4541fd7e7995854cb1ec80ab145b8a17dd27a79e72b848862c6d` |

Red/green evidence: the initial focused run failed at collection because
`kikuchi_lab.ice_globe` did not exist. After implementation,
`uv run pytest tests/scientific/test_ice_intensity_field.py
tests/integration/test_ice_globe_workflows.py tests/scientific/relief
tests/integration/test_relief_globe_workflow.py -q` passed. It verifies the
master-derived source kind, separation from the reflector-ridge product kind,
and preserves the existing forsterite relief suite.

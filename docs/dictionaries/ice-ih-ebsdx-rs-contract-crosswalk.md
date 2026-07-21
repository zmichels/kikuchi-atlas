# Ice Ih package to `ebsdx-rs` contract crosswalk

Status: audited against the local draft contract on 2026-07-21. This is an
honest producer-side crosswalk, not a claim that `ebsdx-rs` can already index
detector images with this resource.

Package assessed: `ice-ih-spherical-candidate-v0.1.2`, built from
`recipes/dictionaries/ice-ih-spherical-candidate-v0.1.2.yml`.

| Contract area | `v0.1.2` state | Boundary / next action |
| --- | --- | --- |
| Identity, immutable manifest, checksums, license, CFF, citation, repository | Present and independently checked by the Ice package verifier. | Add a public release artifact before treating the local package as a distributable download. |
| Canonical spherical signal and orientations | Present: raw two-hemisphere master, 13,155 `wxyz` crystal-to-sample entries, and 1,946 S2 directions. | `ebsdx-rs` now authenticates the package and its declared conventions; NPY sampling/projection remains a later adapter. |
| Orientation and signal conventions | Present: `6/mmm` cubochoric fundamental region, active right-handed `wxyz`, row mean-center/L2 normalization, bilinear upper-equator policy, and a duplicate/coverage record. | Consumer must preserve these values exactly. |
| Phase identity | Present: Ice Ih average oxygen sublattice, `P 63/m m c` No. 194, cited COD source, lattice parameters, and a standard symmetry-setting reference. | A future multi-phase catalog needs per-phase source records of the same quality. |
| Physics provenance | Present: source master identity, source run/recipe hashes, 20 keV energy, oxygen-only scope, and generation/postprocessing metadata. | Pin an immutable source-builder release commit when its producer is released. |
| Matching compatibility | Present for canonical signals: exact S2 grid, normalized cosine, and named input normalization. | Detector dtype, mask, background/saturation policy, and detector-to-sphere projection are deliberately absent until an explicit adapter recipe exists. |
| Runtime geometry | Explicitly not fixed: the package is detector-independent. | `ebsdxr dictionary-resource-preflight --require-runtime --runtime-recipe <json>` now rejects absent geometry or unnamed preprocessing; it never infers either. |
| Validation | Present: checksum inventory plus a held-out 3.54-degree synthetic orientation whose full-master refinement improves the coarse angular diagnostic. | Add the contract's tiny convention/phase-symmetry fixture set before calling the resource integration-ready. |
| Acquired EBSD performance | Not claimed. | Requires declared reference patterns, detector geometry, preprocessing products, and a separately reviewed benchmark. |

## Current integration verdict

The package is a valid **canonical dictionary producer proof**: it is portable,
provenance-bound, verifier-tested, has the draft contract's detector-independent
manifest fields, and has no hidden detector model. `ebsdx-rs` now independently
preflights its manifest and every inventoried payload, then requires a named
runtime geometry/preprocessing recipe before a future matcher may proceed. It
is not yet a detector-to-sphere adapter or an indexing result.

## Promotion gate

Before an `ebsdx-rs` registration command produces Ice Ih indexing results,
add an explicit detector-to-sphere preprocessing/projection adapter. It must
preserve this package's direction grid, quaternion convention, and
normalization exactly; the landed preflight is the gate that prevents it from
silently guessing geometry or transforms.

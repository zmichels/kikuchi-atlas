# Ice Ih package to `ebsdx-rs` contract crosswalk

Status: audited against the local draft contract on 2026-07-21. This is an
honest producer-side crosswalk, not a claim that `ebsdx-rs` can already index
detector images with this resource.

Package assessed: `ice-ih-spherical-candidate-v0.1.3`, built from
`recipes/dictionaries/ice-ih-spherical-candidate-v0.1.3.yml`.

| Contract area | `v0.1.3` state | Boundary / next action |
| --- | --- | --- |
| Identity, immutable manifest, checksums, license, CFF, citation, repository | Present and independently checked by the Ice package verifier. | Add a public release artifact before treating the local package as a distributable download. |
| Canonical spherical signal and orientations | Present: raw crystal-frame two-hemisphere master, 13,155 `wxyz` crystal-to-sample entries, and 1,946 sample-frame S2 directions. | `ebsdx-rs` authenticates the package and ranks an observed NPY signal only after its C-order direction-grid payload is byte-identical to the packaged grid; detector projection remains a later adapter. |
| Orientation and signal conventions | Present: `6/mmm` cubochoric fundamental region, active right-handed `wxyz`, explicit master/cache frame labels, row mean-center/L2 normalization, bilinear upper-equator policy, and a duplicate/coverage record. | Consumer must preserve these values exactly. |
| Phase identity | Present: Ice Ih average oxygen sublattice, `P 63/m m c` No. 194, cited COD source, lattice parameters, and a standard symmetry-setting reference. | A future multi-phase catalog needs per-phase source records of the same quality. |
| Physics provenance | Present: source master identity, source run/recipe hashes, 20 keV energy, oxygen-only scope, and generation/postprocessing metadata. | Pin an immutable source-builder release commit when its producer is released. |
| Matching compatibility | Present for canonical signals: exact S2 grid, normalized cosine, and named input normalization. A Python-only same-source detector-to-partial-S2 geometry proof now records bilinear sampling and a coverage mask. A source-bound detector observation package now serializes raw numeric input, named geometry, explicit identity preprocessing, directions, partial signal, coverage, manifest, and checksums. | The proof uses a coverage-specific masked cosine score, not the current full-S2 `ebsdx-rs` metric. The new package is not yet an `ebsdx-rs` input type; acquired detector dtype, mask, background/saturation policy, and an interoperable adapter recipe remain open. |
| Runtime geometry | Explicitly not fixed: the package is detector-independent. Python now has finite candidate geometry ranking that compares candidates only on their common S2 coverage mask. | `ebsdxr dictionary-resource-preflight --require-runtime --runtime-recipe <json>` now rejects absent geometry, sample-frame convention, or unnamed preprocessing; it never infers any of them. The Rust runtime has no detector-to-S2 or geometry-search execution yet. |
| Validation | Present: checksum inventory plus a held-out 3.54-degree synthetic orientation whose full-master refinement improves the coarse angular diagnostic. | The Rust canonical matcher reproduces coarse entry `6952` at score `0.6117760946` (the producer record is `0.6117761135` under its float32 path); add the contract's tiny convention/phase-symmetry fixture set before calling the resource integration-ready. |
| Acquired EBSD performance | Not claimed. | Requires declared reference patterns, detector geometry, preprocessing products, and a separately reviewed benchmark. |

## Current integration verdict

The package is a valid **canonical dictionary producer proof**: it is portable,
provenance-bound, verifier-tested, has the draft contract's detector-independent
manifest fields, and has no hidden detector model. `ebsdx-rs` independently
preflights its manifest and every inventoried payload, then executes a
deterministic canonical-S2 ranking only when the observed grid matches the
package byte-for-byte. It remains neither a detector-to-sphere adapter nor an
acquired-pattern indexing result.

## Partial-S2 adapter evidence

`scripts/run_ice_ih_detector_to_s2_adapter_proof.py` maps the checked 20 keV
simulated detector pattern through its exact TSL PC and tilt geometry onto 308
of the package's 1,946 sample-frame directions. Using a separate masked,
per-coverage cosine metric, it ranks the source run's identity candidate first
at `0.999549817`. This is a useful geometry and convention proof, not an
acquired-EBSD result or a Rust consumer capability: the detector was generated
from the same source run and the score cannot be compared across masks.

## Master-to-detector congruence evidence

`scripts/run_ice_ih_master_detector_congruence.py` makes the inverse
direction explicit: it maps every pixel of the same declared detector through
the sample-to-detector transform and samples the byte-identical canonical
master in that direction. Its 3,145,728-pixel source-bound proof records a
centered cosine of `0.998537216` and a normalized RMS difference of
`0.054088520`. It verifies a coordinate bridge between the checked
kinematical products; it does not create an independent simulator comparison,
detector calibration, acquired-data result, or Rust matching capability.

## Promotion gate

Before an `ebsdx-rs` registration command produces Ice Ih indexing results,
add an explicit detector-to-sphere preprocessing/projection adapter. It must
preserve this package's direction grid, quaternion convention, and
normalization exactly; the landed preflight is the gate that prevents it from
silently guessing geometry or transforms.

# Spherical dictionary resources

This directory describes reproducible, portable dictionary resources. It is a
separate product line from the [Kikuchi Atlas](../atlas/README.md): the Atlas
is a browsable visual and printable collection, while a dictionary resource is
machine-readable data intended to be consumed by an explicitly declared
matching workflow.

## First resource: forsterite S2 fixture

`recipes/dictionaries/forsterite-spherical-fixture.yml` binds a small fixture
to one exact, cited forsterite S2 field. Build it locally with:

```bash
uv run python scripts/build_forsterite_spherical_dictionary_fixture.py
uv run python scripts/verify_spherical_dictionary.py \
  local/dictionaries/forsterite-spherical-fixture-v0.1.0
```

The package contains the canonical spherical signal, explicit active
crystal-to-sample orientations, a pattern for each orientation, checksums,
license/citation material, and a ranking fixture. It is deliberately tiny:
26 cube-shell directions and three quarter-turn orientations. The build is
instant because it samples an existing checked S2 field; it does not rerun any
diffraction calculation.

The interchange shape follows the local
[`ebsdx-rs` spherical dictionary resource contract](../../ebsdx-rs/docs/spherical-dictionary-resource-contract.md).
The generated package remains ignored under `local/`; tracked code, recipe,
tests, and this document make it reproducible.

## Flagship resource: Ice Ih candidate dictionary

The scientific flagship is now the Ice Ih average-oxygen-sublattice dictionary.
It uses a source-bound 1025-by-1025 two-hemisphere kinematical master as its
canonical signal, plus a fast `6/mmm`-reduced spherical candidate cache. The
cache is intentionally detector-independent: an eventual detector-to-sphere
adapter must declare geometry and preprocessing instead of silently assuming
them.

Build and verify it locally with:

```bash
uv run python scripts/build_ice_ih_spherical_dictionary.py
uv run python scripts/verify_ice_ih_spherical_dictionary.py \
  local/dictionaries/ice-ih-spherical-candidate-v0.1.3
```

`v0.1.3` embeds a deterministic held-out spherical signal, its expected coarse
candidate, and full-master local-refinement diagnostics. Its canonical master
is explicitly crystal-frame, while cache directions and observed spherical
signals are explicitly sample-frame; the active crystal-to-sample quaternions
connect the two. The verifier reruns that recovery from package bytes; it is an
integrity and frame check, not an acquired-pattern accuracy result. See
[the `ebsdx-rs` contract crosswalk](ice-ih-ebsdx-rs-contract-crosswalk.md)
for the exact interoperability state.

The companion Rust engine can now execute the canonical-S2 portion of the
resource after its independent preflight. Supply a spherical observed signal
and the exact direction-grid NPY—not detector pixels:

```bash
ebsdxr dictionary-resource-rank <dictionary.manifest.json> \
  --observed-spherical-signal <observed-s2.npy> \
  --observed-direction-grid <directions.npy> --top-k 8 --json
```

The command requires byte-identical C-order direction-grid payloads, applies
the declared mean-center/L2 normalization, and ranks normalized cosine scores
with stable entry-index tie ordering. It remains a canonical S2 matcher; it
does not project detector patterns or claim acquired-pattern accuracy.

### Why the cache diagnostic looks unlike a Kikuchi pattern

The ranking diagnostic plots the cache as a sparse longitude/latitude scatter
because it is a 1,946-value S2 feature vector, not a detector image and not a
Hough/Radon accumulator. The checked local signal-space bridge places all
three relevant representations together—the kinematical detector projection,
the crystal-frame stereographic master, and the exact sample-frame vector
input—with their roles and excluded adapter boundary stated in the output:

```bash
uv run python scripts/render_ice_ih_dictionary_signal_space_bridge.py \
  --output local/dictionaries/ice-ih-signal-space-bridge-v0.1.1
```

See [the signal-space bridge acceptance record](../acceptance/ice-ih-dictionary-signal-space-bridge.md)
for its source run, input identity, declared camera-footprint overlay, and
nonclaims.

### Detector-to-S2 geometry proof

The next proof maps raw pixels from the checked simulated Ice detector through
its declared gnomonic geometry onto only the cache directions that the camera
actually covers. It then ranks candidates with a coverage-specific masked
cosine metric:

```bash
uv run python scripts/run_ice_ih_detector_to_s2_adapter_proof.py
```

The published local bundle preserves the partial S2 values, coverage mask,
pixel coordinates, ranking record, source detector/recipe identities, and a
three-panel visual proof. It is self-consistency evidence for one simulated
source run; it is not acquired-pattern validation and is deliberately
separate from the strict full-S2 `ebsdxr dictionary-resource-rank` contract.
See [the adapter proof acceptance record](../acceptance/ice-ih-detector-to-s2-adapter-proof.md).

### Master-to-detector congruence proof

The complementary proof reprojects the raw two-hemisphere canonical master
back into every declared detector pixel, then compares it with the checked
raw kinematical detector array:

```bash
uv run python scripts/run_ice_ih_master_detector_congruence.py
```

For the source-bound Ice Ih fixture, the full 1536 x 2048 detector field has
a centered cosine of `0.998537216` against the direct master reprojection.
The visual record includes the two pattern fields, their normalized residual,
and a pixelwise congruence panel. This checks the project-owned coordinate
bridge; it does not independently validate physics, calibrate a detector, or
measure acquired-pattern accuracy. See [the congruence acceptance
record](../acceptance/ice-ih-master-detector-congruence.md).

### Orientation-varied synthetic detector recovery

The first end-to-end orientation proof deliberately chooses four separated
cache entries, reprojects the canonical master to the same named detector, and
returns each partial-S2 signal to the cache ranker:

```bash
uv run python scripts/run_ice_ih_synthetic_detector_orientation_recovery.py
```

Entries `6577`, `15`, `297`, and `7144` all recover themselves first using the
same 308-direction coverage mask, with scores from `0.999790539` to
`0.999966178`. The compact visual bundle is useful for reviewing how genuine
orientation changes look in detector space while keeping the ranker output
legible. It remains a synthetic convention/integrity proof—not an acquired
pattern benchmark or an independent simulation comparison. See [the recovery
acceptance record](../acceptance/ice-ih-synthetic-detector-orientation-recovery.md).

The resource is a kinematical oxygen-sublattice candidate search. It does not
yet claim acquired-pattern calibration or distinguish Ice Ic, stacking-
disordered ice, amorphous ice, high-pressure polymorphs, or detailed hydrogen
order.

## Claim boundary

The fixture is not a detector-projected pattern library, a calibrated EBSD
acquisition model, or a performance claim for dictionary indexing. It defines
no detector geometry, experimental background model, camera response,
preprocessing transform, interpolation, or generic orientation grid.

Promotion to a scientific dictionary product needs a separately reviewed
recipe with detector/projection metadata, an explicit preprocessing contract,
a materially denser orientation and S2 sampling plan, and validation against
declared experimental reference patterns.

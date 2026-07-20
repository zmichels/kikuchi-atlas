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

## Claim boundary

The fixture is not a detector-projected pattern library, a calibrated EBSD
acquisition model, or a performance claim for dictionary indexing. It defines
no detector geometry, experimental background model, camera response,
preprocessing transform, interpolation, or generic orientation grid.

Promotion to a scientific dictionary product needs a separately reviewed
recipe with detector/projection metadata, an explicit preprocessing contract,
a materially denser orientation and S2 sampling plan, and validation against
declared experimental reference patterns.

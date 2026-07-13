import json

import numpy as np
import pytest

from kikuchi_lab.model.persistence import load_master_product, save_master_product
from kikuchi_lab.model.products import MasterPatternProduct


def product():
    return MasterPatternProduct.from_array(
        np.arange(50, dtype=np.float32).reshape(2, 5, 5),
        metadata={
            "phase": {
                "name": "forsterite",
                "formula": "Mg2SiO4",
                "space_group": {"number": 62, "setting": "Pnma"},
                "lattice": {
                    "values": [4.75, 10.20, 5.98, 90, 90, 90],
                    "units": "angstrom",
                },
            },
            "source_structure": {
                "identifier": "COD-9000319",
                "sha256": "a" * 64,
                "provenance": {
                    "uri": "https://www.crystallography.net/cod/9000319.cif",
                    "license": "COD copying policy",
                    "citation": "Kirfel et al. (2005)",
                },
            },
            "generator": {"name": "ebsdsim", "version": "0.1.8"},
            "simulation": {
                "recipe_id": "recipe-1234567890abcdef",
                "recipe_sha256": "b" * 64,
                "voltage_kv": 20.0,
            },
            "projection": "lambert",
            "hemisphere_order": ["north", "south"],
            "energy_kev": 20.0,
            "intensity_units": "relative",
            "coordinate_frame": "crystal",
            "provenance_links": [
                "source-1234567890abcdef",
                "recipe-1234567890abcdef",
            ],
        },
    )


def test_master_product_round_trip_preserves_evidence(tmp_path):
    original = product()
    path = save_master_product(tmp_path / "master.npz", original)
    restored = load_master_product(path)

    np.testing.assert_array_equal(restored.intensity, original.intensity)
    assert restored.metadata_dict() == original.metadata_dict()
    assert restored.intensity.flags.writeable is False
    assert restored.array_sha256 == original.array_sha256
    assert restored.product_id == original.product_id


def test_product_identity_does_not_depend_on_npz_path(tmp_path):
    first = load_master_product(save_master_product(tmp_path / "a.npz", product()))
    second = load_master_product(save_master_product(tmp_path / "b.npz", product()))

    assert first.product_id == second.product_id


def test_load_rejects_unknown_schema_version(tmp_path):
    path = save_master_product(tmp_path / "master.npz", product())
    with np.load(path, allow_pickle=False) as archive:
        intensity = archive["intensity"]
        metadata = json.loads(str(archive["meta_json"].item()))
    metadata["schema_version"] = 999
    np.savez_compressed(path, intensity=intensity, meta_json=json.dumps(metadata))

    with pytest.raises(ValueError, match="schema version"):
        load_master_product(path)


def test_load_rejects_corrupted_array_hash(tmp_path):
    path = save_master_product(tmp_path / "master.npz", product())
    with np.load(path, allow_pickle=False) as archive:
        intensity = archive["intensity"].copy()
        metadata = str(archive["meta_json"].item())
    intensity[0, 0, 0] += 1
    np.savez_compressed(path, intensity=intensity, meta_json=metadata)

    with pytest.raises(ValueError, match="checksum"):
        load_master_product(path)


def test_load_rejects_corrupted_product_id(tmp_path):
    path = save_master_product(tmp_path / "master.npz", product())
    with np.load(path, allow_pickle=False) as archive:
        intensity = archive["intensity"]
        metadata = json.loads(str(archive["meta_json"].item()))
    metadata["product_id"] = "master-deadbeefdeadbeef"
    np.savez_compressed(path, intensity=intensity, meta_json=json.dumps(metadata))

    with pytest.raises(ValueError, match="product identity"):
        load_master_product(path)


def test_load_rejects_metadata_array_shape_that_disagrees_with_payload(tmp_path):
    path = save_master_product(tmp_path / "master.npz", product())
    with np.load(path, allow_pickle=False) as archive:
        intensity = archive["intensity"]
        metadata = json.loads(str(archive["meta_json"].item()))
    metadata["metadata"]["array"]["shape"] = [2, 99, 99]
    np.savez_compressed(path, intensity=intensity, meta_json=json.dumps(metadata))

    with pytest.raises(ValueError, match="array shape"):
        load_master_product(path)

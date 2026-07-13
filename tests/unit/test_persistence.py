import json
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model import persistence
from kikuchi_lab.model.persistence import load_master_product, save_master_product
from kikuchi_lab.model.products import MasterPatternProduct


def product():
    source_structure = {
        "identifier": "COD-9000319",
        "sha256": "a" * 64,
        "provenance": {
            "uri": "https://www.crystallography.net/cod/9000319.cif",
            "license": "COD copying policy",
            "citation": "Kirfel et al. (2005)",
        },
    }
    source_structure["source_id"] = stable_id("source", source_structure)
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
            "source_structure": source_structure,
            "generator": {"name": "ebsdsim", "version": "0.1.8"},
            "simulation": {
                "recipe_id": "recipe-bbbbbbbbbbbbbbbb",
                "recipe_sha256": "b" * 64,
                "voltage_kv": 20.0,
            },
            "projection": "lambert",
            "hemisphere_order": ["north", "south"],
            "energy_kev": 20.0,
            "intensity_units": "relative",
            "coordinate_frame": "crystal",
            "provenance_links": [
                source_structure["source_id"],
                "recipe-bbbbbbbbbbbbbbbb",
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


def test_save_appends_npz_and_returns_an_existing_path(tmp_path):
    returned = save_master_product(tmp_path / "master", product())

    assert returned == tmp_path / "master.npz"
    assert returned.is_file()
    assert not (tmp_path / "master").exists()


def test_save_uses_same_directory_temporary_file_and_atomic_replace(tmp_path, monkeypatch):
    observed = {}
    real_savez = persistence.np.savez_compressed
    real_replace = persistence.os.replace

    def record_save(file, **arrays):
        observed["temporary"] = Path(file.name)
        return real_savez(file, **arrays)

    def record_replace(source, destination):
        observed["replace"] = (source, destination)
        return real_replace(source, destination)

    monkeypatch.setattr(persistence.np, "savez_compressed", record_save)
    monkeypatch.setattr(persistence.os, "replace", record_replace)

    returned = save_master_product(tmp_path / "master.npz", product())

    temporary = observed["temporary"]
    assert temporary.parent == tmp_path
    assert temporary != returned
    assert observed["replace"] == (temporary, returned)
    assert returned.is_file()
    assert not temporary.exists()


def test_failed_atomic_save_preserves_existing_target_and_cleans_temporary_file(
    tmp_path, monkeypatch
):
    target = save_master_product(tmp_path / "master.npz", product())
    original_bytes = target.read_bytes()

    def fail_after_partial_write(file, **_arrays):
        file.write(b"partial")
        file.flush()
        raise RuntimeError("injected write failure")

    monkeypatch.setattr(persistence.np, "savez_compressed", fail_after_partial_write)

    with pytest.raises(RuntimeError, match="injected"):
        save_master_product(target, product())

    assert target.read_bytes() == original_bytes
    assert list(tmp_path.iterdir()) == [target]


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


@pytest.mark.parametrize("envelope", [None, [], "metadata", 1])
def test_load_rejects_non_object_json_envelope_as_value_error(tmp_path, envelope):
    path = tmp_path / "bad.npz"
    np.savez_compressed(path, intensity=np.zeros((2, 2, 2)), meta_json=json.dumps(envelope))

    with pytest.raises(ValueError, match="JSON object"):
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

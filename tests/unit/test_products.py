import numpy as np
import pytest

from kikuchi_lab.model.products import DetectorPatternProduct, MasterPatternProduct
from kikuchi_lab.model.provenance import SourceRecord


def valid_metadata(**changes):
    source = SourceRecord(
        uri="https://www.crystallography.net/cod/9000319.cif",
        sha256="a" * 64,
        license="COD copying policy",
        citation="Kirfel et al. (2005)",
    )
    source_structure = {
        "identifier": "COD-9000319",
        "sha256": source.sha256,
        "provenance": {
            "uri": source.uri,
            "license": source.license,
            "citation": source.citation,
        },
    }
    source_structure["source_id"] = source.source_id
    metadata = {
        "phase": {
            "name": "forsterite",
            "formula": "Mg2SiO4",
            "space_group": {"number": 62, "setting": "Pnma"},
            "lattice": {"values": [4.75, 10.20, 5.98, 90, 90, 90], "units": "angstrom"},
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
    }
    metadata.update(changes)
    return metadata


def test_master_pattern_owns_a_read_only_float32_array():
    source = np.arange(18, dtype=np.float64).reshape(2, 3, 3)
    product = MasterPatternProduct.from_array(source, metadata=valid_metadata())
    source[:] = -1

    assert product.intensity.dtype == np.float32
    assert product.intensity.flags.writeable is False
    assert product.intensity[0, 0, 0] == 0
    assert product.metadata_dict()["array"] == {
        "shape": [2, 3, 3],
        "dtype": "float32",
        "sha256": product.array_sha256,
    }


def test_master_pattern_accepts_exact_source_record_identity():
    source = SourceRecord(
        uri="https://www.crystallography.net/cod/9000319.cif",
        sha256="a" * 64,
        license="COD copying policy",
        citation="Kirfel et al. (2005)",
    )
    product = MasterPatternProduct.from_array(np.ones((2, 3, 3)), metadata=valid_metadata())

    assert product.metadata_dict()["source_structure"]["source_id"] == source.source_id
    assert source.source_id in product.metadata_dict()["provenance_links"]


def test_master_pattern_array_cannot_be_made_writeable_again():
    product = MasterPatternProduct.from_array(np.ones((2, 3, 3)), metadata=valid_metadata())
    identity = product.product_id

    with pytest.raises(ValueError):
        product.intensity.setflags(write=True)
    assert product.product_id == identity
    assert product.array_sha256 == product.metadata_dict()["array"]["sha256"]


def test_master_pattern_public_constructor_cannot_bypass_validation():
    with pytest.raises(TypeError, match="from_array"):
        MasterPatternProduct()
    with pytest.raises(TypeError):
        MasterPatternProduct(
            intensity=np.full((2, 3, 3), np.nan),
            metadata={},
            array_sha256="fake",
            product_id="master-fake",
        )


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_master_pattern_rejects_nonfinite_intensity(value):
    intensity = np.zeros((2, 3, 3))
    intensity[0, 0, 0] = value

    with pytest.raises(ValueError, match="finite"):
        MasterPatternProduct.from_array(intensity, metadata=valid_metadata())


def test_master_pattern_rejects_wrong_hemisphere_shape():
    with pytest.raises(ValueError, match="north.*south|shape"):
        MasterPatternProduct.from_array(np.zeros((1, 3, 3)), metadata=valid_metadata())


@pytest.mark.parametrize(
    "changes",
    [
        {"intensity_units": None},
        {"coordinate_frame": None},
        {"hemisphere_order": ["south", "north"]},
        {"energy_kev": 15.0},
    ],
)
def test_master_pattern_rejects_missing_units_frame_or_inconsistent_energy(changes):
    with pytest.raises(ValueError):
        MasterPatternProduct.from_array(
            np.zeros((2, 3, 3), dtype=np.float32), metadata=valid_metadata(**changes)
        )


@pytest.mark.parametrize(
    "missing",
    [
        "phase",
        "source_structure",
        "generator",
        "simulation",
        "projection",
        "hemisphere_order",
        "provenance_links",
    ],
)
def test_master_pattern_rejects_materially_incomplete_metadata(missing):
    metadata = valid_metadata()
    metadata.pop(missing)

    with pytest.raises(ValueError, match=missing):
        MasterPatternProduct.from_array(np.zeros((2, 3, 3)), metadata=metadata)


@pytest.mark.parametrize(
    "path",
    [
        ("phase", "formula"),
        ("phase", "space_group"),
        ("phase", "lattice"),
        ("source_structure", "sha256"),
        ("source_structure", "provenance"),
        ("generator", "version"),
        ("simulation", "recipe_sha256"),
    ],
)
def test_master_pattern_rejects_incomplete_nested_metadata(path):
    metadata = valid_metadata()
    metadata[path[0]].pop(path[1])

    with pytest.raises(ValueError):
        MasterPatternProduct.from_array(np.zeros((2, 3, 3)), metadata=metadata)


@pytest.mark.parametrize(
    ("container", "key", "value"),
    [
        ("space_group", "number", "62"),
        ("space_group", "number", True),
        ("simulation", "voltage_kv", "20.0"),
        ("simulation", "voltage_kv", True),
        ("root", "energy_kev", "20.0"),
        ("root", "energy_kev", True),
    ],
)
def test_master_pattern_rejects_noncanonical_numeric_metadata(container, key, value):
    metadata = valid_metadata()
    if container == "space_group":
        metadata["phase"]["space_group"][key] = value
    elif container == "simulation":
        metadata["simulation"][key] = value
    else:
        metadata[key] = value

    with pytest.raises(ValueError):
        MasterPatternProduct.from_array(np.zeros((2, 3, 3)), metadata=metadata)


def test_master_pattern_rejects_recipe_id_that_disagrees_with_recipe_sha():
    metadata = valid_metadata()
    metadata["simulation"]["recipe_id"] = "recipe-0000000000000000"

    with pytest.raises(ValueError, match="recipe_id"):
        MasterPatternProduct.from_array(np.zeros((2, 3, 3)), metadata=metadata)


@pytest.mark.parametrize("link_kind", ["recipe", "source"])
def test_master_pattern_requires_consistent_recipe_and_source_provenance_links(link_kind):
    metadata = valid_metadata()
    expected = (
        metadata["simulation"]["recipe_id"]
        if link_kind == "recipe"
        else metadata["source_structure"]["source_id"]
    )
    metadata["provenance_links"].remove(expected)

    with pytest.raises(ValueError, match=f"{link_kind}.*provenance_links"):
        MasterPatternProduct.from_array(np.zeros((2, 3, 3)), metadata=metadata)


def test_master_pattern_rejects_source_id_that_disagrees_with_source_record():
    metadata = valid_metadata()
    metadata["source_structure"]["source_id"] = "source-0000000000000000"

    with pytest.raises(ValueError, match="source_id"):
        MasterPatternProduct.from_array(np.zeros((2, 3, 3)), metadata=metadata)


def test_master_product_identity_depends_on_array_and_metadata_not_source_buffer():
    first = MasterPatternProduct.from_array(np.ones((2, 3, 3)), metadata=valid_metadata())
    second = MasterPatternProduct.from_array(np.ones((2, 3, 3)), metadata=valid_metadata())
    changed = MasterPatternProduct.from_array(np.ones((2, 3, 3)) * 2, metadata=valid_metadata())

    assert first.product_id == second.product_id
    assert first.product_id != changed.product_id
    assert len(first.array_sha256) == 64


def test_product_metadata_is_plain_json_and_immutable():
    product = MasterPatternProduct.from_array(
        np.ones((2, 3, 3)), metadata=valid_metadata(energy_kev=np.float64(20.0))
    )

    assert isinstance(product.metadata_dict()["energy_kev"], float)
    with pytest.raises(TypeError):
        product.metadata["energy_kev"] = 30


def test_master_product_equality_and_hash_do_not_compare_ndarrays():
    first = MasterPatternProduct.from_array(np.ones((2, 3, 3)), metadata=valid_metadata())
    same = MasterPatternProduct.from_array(np.ones((2, 3, 3)), metadata=valid_metadata())
    different = MasterPatternProduct.from_array(np.ones((2, 3, 3)) * 2, metadata=valid_metadata())

    assert first == same
    assert hash(first) == hash(same)
    assert first != different
    assert len({first, same, different}) == 2


def test_detector_pattern_owns_array_and_references_projection_inputs():
    source = np.arange(12, dtype=np.float64).reshape(3, 4)
    product = DetectorPatternProduct.from_array(
        source,
        master_product_id="master-1234567890abcdef",
        projection_recipe_id="recipe-1234567890abcdef",
        metadata={
            "energy_kev": 20.0,
            "intensity_units": "relative",
            "detector_frame": "ebsd_detector",
        },
    )
    source[:] = -1

    assert product.intensity.shape == (3, 4)
    assert product.intensity.dtype == np.float32
    assert product.intensity.flags.writeable is False
    assert product.master_product_id == "master-1234567890abcdef"
    assert product.projection_recipe_id == "recipe-1234567890abcdef"
    assert product.intensity[0, 0] == 0


def test_detector_pattern_array_cannot_be_made_writeable_again():
    product = DetectorPatternProduct.from_array(
        np.ones((3, 4)),
        master_product_id="master-1234567890abcdef",
        projection_recipe_id="recipe-1234567890abcdef",
        metadata={
            "energy_kev": 20.0,
            "intensity_units": "relative",
            "detector_frame": "ebsd_detector",
        },
    )
    identity = product.product_id

    with pytest.raises(ValueError):
        product.intensity.setflags(write=True)
    assert product.product_id == identity


def test_detector_pattern_public_constructor_cannot_bypass_validation():
    with pytest.raises(TypeError, match="from_array"):
        DetectorPatternProduct()
    with pytest.raises(TypeError):
        DetectorPatternProduct(
            intensity=np.array([[np.nan]]),
            master_product_id="fake",
            projection_recipe_id="fake",
            metadata={},
            array_sha256="fake",
            product_id="detector-fake",
        )


def test_detector_pattern_rejects_nonfinite_or_missing_frame():
    with pytest.raises(ValueError, match="finite"):
        DetectorPatternProduct.from_array(
            np.array([[np.inf]]),
            master_product_id="master-1234567890abcdef",
            projection_recipe_id="recipe-1234567890abcdef",
            metadata={"energy_kev": 20.0, "intensity_units": "relative", "detector_frame": "x"},
        )
    with pytest.raises(ValueError, match="detector_frame"):
        DetectorPatternProduct.from_array(
            np.ones((2, 2)),
            master_product_id="master-1234567890abcdef",
            projection_recipe_id="recipe-1234567890abcdef",
            metadata={"energy_kev": 20.0, "intensity_units": "relative"},
        )


def test_detector_product_equality_and_hash_do_not_compare_ndarrays():
    kwargs = {
        "master_product_id": "master-1234567890abcdef",
        "projection_recipe_id": "recipe-1234567890abcdef",
        "metadata": {
            "energy_kev": 20.0,
            "intensity_units": "relative",
            "detector_frame": "ebsd_detector",
        },
    }
    first = DetectorPatternProduct.from_array(np.ones((2, 2)), **kwargs)
    same = DetectorPatternProduct.from_array(np.ones((2, 2)), **kwargs)
    different = DetectorPatternProduct.from_array(np.zeros((2, 2)), **kwargs)

    assert first == same
    assert hash(first) == hash(same)
    assert first != different
    assert len({first, same, different}) == 2

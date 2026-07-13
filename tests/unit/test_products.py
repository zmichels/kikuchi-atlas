import numpy as np
import pytest

from kikuchi_lab.model.products import DetectorPatternProduct, MasterPatternProduct


def valid_metadata(**changes):
    metadata = {
        "source_id": "source-1234567890abcdef",
        "phase_id": "phase-1234567890abcdef",
        "simulation_recipe_id": "recipe-1234567890abcdef",
        "projection": "lambert",
        "hemisphere_order": ["north", "south"],
        "simulation_voltage_kv": 20.0,
        "energy_kev": 20.0,
        "intensity_units": "relative",
        "coordinate_frame": "crystal",
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

import json
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.model import DetectorPatternProduct
from kikuchi_lab.processing import load_processing_recipe, run_graph


REPO_ROOT = Path(__file__).parents[2]


def detector_projection() -> DetectorPatternProduct:
    yy, xx = np.indices((96, 128), dtype=np.float32)
    image = 0.7 + 0.002 * xx + 0.25 * np.exp(-((yy - 0.6 * xx - 8) ** 2) / 12)
    return DetectorPatternProduct.from_array(
        image,
        master_product_id="master-test",
        projection_recipe_id="recipe-projection-test",
        metadata={
            "intensity_units": "arbitrary",
            "detector_frame": "EDAX-TSL:RD-TD-ND",
            "energy_kev": 20.0,
            "detector": {
                "shape": [48, 64],
                "supersampled_shape": [96, 128],
                "physical_extent_um": [480.0, 640.0],
                "supersampling": 2,
            },
            "supersampling": 2,
            "downsampled": False,
        },
    )


def test_graph_keeps_scientific_and_gallery_sources_identical():
    projected = detector_projection()
    scientific_recipe = load_processing_recipe(
        REPO_ROOT / "recipes/proof/scientific-clean.yml"
    )
    gallery_recipe = load_processing_recipe(REPO_ROOT / "recipes/gallery/gallery-crisp.yml")

    scientific = run_graph(projected, scientific_recipe)
    gallery = run_graph(projected, gallery_recipe)

    assert scientific.source_projection_id == projected.product_id
    assert gallery.source_projection_id == projected.product_id
    assert scientific.source_projection_id == gallery.source_projection_id
    assert scientific.product_id != gallery.product_id
    np.testing.assert_array_equal(projected.intensity, detector_projection().intensity)


def test_graph_is_ordered_deterministic_serializable_and_immutable():
    projected = detector_projection()
    recipe = load_processing_recipe(REPO_ROOT / "recipes/gallery/gallery-crisp.yml")

    first = run_graph(projected, recipe)
    second = run_graph(projected, recipe)

    assert first.product_id == second.product_id
    assert [stage.record.name for stage in first.stages] == [
        stage.name for stage in recipe.stages
    ]
    assert first.stages[0].record.input_id.startswith("image-")
    assert all(
        left.record.output_id == right.record.input_id
        for left, right in zip(first.stages, first.stages[1:], strict=False)
    )
    assert not first.final_intensity.flags.writeable
    assert all(not stage.intensity.flags.writeable for stage in first.stages)
    with pytest.raises(TypeError):
        first.geometry["supersampling"] = 99
    json.dumps(first.to_dict())


def test_downsample_matches_detector_physical_supersampling_geometry():
    projected = detector_projection()
    recipe = load_processing_recipe(REPO_ROOT / "recipes/proof/scientific-clean.yml")

    result = run_graph(projected, recipe)

    assert projected.intensity.shape == (96, 128)
    assert result.final_intensity.shape == (48, 64)
    assert result.to_dict()["geometry"] == {
        "source_shape": [96, 128],
        "output_shape": [48, 64],
        "physical_extent_um": [480.0, 640.0],
        "supersampling": 2,
    }


def test_source_projection_is_not_a_processing_intermediate_or_replaced():
    projected = detector_projection()
    source_copy = projected.intensity.copy()
    recipe = load_processing_recipe(REPO_ROOT / "recipes/gallery/gallery-crisp.yml")

    result = run_graph(projected, recipe)

    assert all(stage.record.output_id != projected.product_id for stage in result.stages)
    assert result.product_id != projected.product_id
    np.testing.assert_array_equal(projected.intensity, source_copy)

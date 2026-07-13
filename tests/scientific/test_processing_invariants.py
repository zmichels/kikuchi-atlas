import json
from pathlib import Path

import numpy as np
import pytest
import yaml

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


def test_robust_percentile_graph_reports_outlier_clipping_at_clahe_boundary():
    projected = detector_projection()
    mutable = projected.intensity.copy()
    mutable[0, 0] = -100.0
    mutable[-1, -1] = 100.0
    metadata = projected.metadata_dict()
    metadata.pop("array")
    outlier_projection = DetectorPatternProduct.from_array(
        mutable,
        master_product_id=projected.master_product_id,
        projection_recipe_id=projected.projection_recipe_id,
        metadata=metadata,
    )
    preset = load_processing_recipe(REPO_ROOT / "recipes/gallery/gallery-crisp.yml")

    result = run_graph(outlier_projection, preset)

    names = [stage.record.name for stage in result.stages]
    normalize = result.stages[names.index("robust_normalize")]
    clahe = result.stages[names.index("local_contrast")]
    assert normalize.record.parameters == {
        "low_percentile": 1.0,
        "high_percentile": 99.0,
    }
    assert normalize.intensity.min() < 0.0
    assert normalize.intensity.max() > 1.0
    assert clahe.record.parameters["input_domain"] == "clip_0_1"
    assert clahe.record.diagnostics["input_clipped_fraction"] > 0.001
    assert "clipping_fraction" in [warning.code for warning in clahe.record.warnings]


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


def test_checked_in_presets_roundtrip_metadata_but_share_computational_identity(tmp_path):
    path = REPO_ROOT / "recipes/proof/scientific-clean.yml"
    preset = load_processing_recipe(path)
    payload = preset.to_dict()

    assert payload["schema_version"] == 1
    assert payload["name"] == "scientific-clean"
    assert payload["intent"].startswith("restrained acquisition-style")
    assert payload == yaml.safe_load(path.read_text(encoding="utf-8"))

    renamed = dict(payload)
    renamed["name"] = "renamed-display-label"
    renamed["intent"] = "Different prose; identical computation."
    renamed_path = tmp_path / "renamed.yml"
    renamed_path.write_text(yaml.safe_dump(renamed), encoding="utf-8")
    renamed_preset = load_processing_recipe(renamed_path)
    assert renamed_preset.recipe_id == preset.recipe_id


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"name": "missing", "intent": "missing schema", "stages": []}, "schema_version"),
        (
            {"schema_version": 2, "name": "future", "intent": "unknown", "stages": []},
            "schema_version",
        ),
        (
            {"schema_version": True, "name": "bool", "intent": "invalid", "stages": []},
            "schema_version",
        ),
        ({"schema_version": 1, "intent": "missing name", "stages": []}, "name"),
        ({"schema_version": 1, "name": "missing-intent", "stages": []}, "intent"),
    ],
)
def test_preset_loader_rejects_invalid_contract(tmp_path, payload, message):
    path = tmp_path / "preset.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_processing_recipe(path)

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from kikuchi_lab.model import DetectorPatternProduct
from kikuchi_lab.processing import load_processing_recipe, run_graph
import kikuchi_lab.processing.stages as stages_module


REPO_ROOT = Path(__file__).parents[2]


def detector_projection(
    shape: tuple[int, int] = (48, 64), supersampling: int = 2
) -> DetectorPatternProduct:
    supersampled_shape = tuple(value * supersampling for value in shape)
    yy, xx = np.indices(supersampled_shape, dtype=np.float32)
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
                "shape": list(shape),
                "supersampled_shape": list(supersampled_shape),
                "physical_extent_um": [value * 10.0 for value in shape],
                "supersampling": supersampling,
            },
            "supersampling": supersampling,
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
    assert result.stages[-1].record.parameters["shape"] == (48, 64)


@pytest.mark.parametrize(
    ("shape", "supersampling"),
    [((30, 50), 3), ((24, 40), 1)],
)
def test_symbolic_detector_native_shape_resolves_per_source(shape, supersampling):
    projected = detector_projection(shape=shape, supersampling=supersampling)
    preset = load_processing_recipe(REPO_ROOT / "recipes/proof/scientific-clean.yml")

    result = run_graph(projected, preset)

    assert result.final_intensity.shape == shape
    assert result.stages[-1].record.parameters["shape"] == shape
    assert result.resolved_recipe_id == result.processing_recipe_id
    assert result.resolved_recipe_id != preset.recipe_id


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
    assert payload["stages"][-1]["parameters"]["shape"] == "detector_native"


def test_advisory_threshold_and_prose_change_evidence_not_product_identity(monkeypatch):
    projected = detector_projection()
    preset = load_processing_recipe(REPO_ROOT / "recipes/gallery/gallery-crisp.yml")

    baseline = run_graph(projected, preset)
    monkeypatch.setattr(stages_module, "CLIPPING_FRACTION_WARNING", 0.5)
    threshold_changed = run_graph(projected, preset)
    monkeypatch.setattr(stages_module, "CLIPPING_FRACTION_WARNING", 0.001)
    monkeypatch.setattr(
        stages_module,
        "CLIPPING_WARNING_MESSAGE",
        "Advisory wording changed without changing computation.",
    )
    prose_changed = run_graph(projected, preset)

    assert baseline.product_id == threshold_changed.product_id == prose_changed.product_id
    assert baseline.evidence_id != threshold_changed.evidence_id
    assert baseline.evidence_id != prose_changed.evidence_id
    assert np.array_equal(baseline.final_intensity, threshold_changed.final_intensity)
    assert np.array_equal(baseline.final_intensity, prose_changed.final_intensity)


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


@pytest.mark.parametrize(
    "parameters",
    [
        {"sigma_px": "18.0", "epsilon": 1e-6},
        {"sigma_px": True, "epsilon": 1e-6},
    ],
)
def test_yaml_loader_rejects_non_numeric_background_parameters(tmp_path, parameters):
    payload = {
        "schema_version": 1,
        "name": "invalid-numeric",
        "intent": "prove strict YAML types",
        "stages": [{"name": "background_divide", "parameters": parameters}],
    }
    path = tmp_path / "preset.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises((TypeError, ValueError), match="numeric|number"):
        load_processing_recipe(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [("scales_px", "1.0"), ("gains", b"1")],
)
def test_yaml_loader_rejects_string_and_byte_detail_sequences(tmp_path, field, value):
    parameters = {"scales_px": [1.0], "gains": [0.5]}
    parameters[field] = value
    payload = {
        "schema_version": 1,
        "name": "invalid-sequence",
        "intent": "prove strict YAML sequence types",
        "stages": [{"name": "multiscale_detail", "parameters": parameters}],
    }
    path = tmp_path / "preset.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises((TypeError, ValueError), match="sequence"):
        load_processing_recipe(path)

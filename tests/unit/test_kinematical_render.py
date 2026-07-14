from dataclasses import replace
from importlib.metadata import version
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from kikuchi_lab.kinematical import (
    KinematicalExecution,
    execute_kinematical,
    load_kinematical_recipe,
)
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.render import (
    asinh_tone_map,
    circular_stereographic_field,
    render_kinematical_figures,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"
RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"
FIGURE_NAMES = {
    "kinematical-stereographic-bands.svg",
    "kinematical-spherical-bands.png",
    "kinematical-detector-overlay.png",
    "etched-master-balanced.png",
    "etched-master-quiet.png",
    "reflector-selection.png",
}


@pytest.fixture(scope="module")
def small_render_inputs():
    record = load_structure_record(SOURCE)
    loaded = load_kinematical_recipe(RECIPE)
    recipe = replace(
        loaded,
        half_size=16,
        detector=replace(loaded.detector, shape=(96, 128)),
        figure_size_px=320,
    )
    simulation, context = simulate_kinematical_arrays(record, recipe)
    return record, recipe, simulation, context


@pytest.fixture(scope="module")
def small_kinematical_execution(small_render_inputs) -> KinematicalExecution:
    record, recipe, _, _ = small_render_inputs
    return execute_kinematical(record, recipe)


def test_asinh_tone_map_is_pointwise_monotonic_and_does_not_move_pixels() -> None:
    image = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]], dtype=np.float32)
    original = image.copy()

    toned = asinh_tone_map(image, percentiles=(0.0, 100.0), scale=7.0)

    normalized = image.astype(np.float64) / 5.0
    expected = 0.035 + 0.90 * np.arcsinh(7.0 * normalized) / np.arcsinh(7.0)
    assert toned.shape == image.shape
    assert toned.dtype == np.float32
    np.testing.assert_array_equal(image, original)
    np.testing.assert_allclose(toned, expected.astype(np.float32), rtol=0, atol=1e-7)
    assert np.all(np.diff(toned.ravel()) > 0)
    assert toned[0, 0] == pytest.approx(0.035)
    assert toned[-1, -1] == pytest.approx(0.935)


def test_asinh_tone_map_rejects_a_zero_width_percentile_window() -> None:
    with pytest.raises(ValueError, match="positive width"):
        asinh_tone_map(np.ones((3, 3)), percentiles=(0.5, 99.5), scale=7.0)


def test_circular_stereographic_field_only_masks_outside_the_unit_disk() -> None:
    image = np.arange(25, dtype=np.float32).reshape(5, 5)

    field = circular_stereographic_field(image)

    np.testing.assert_array_equal(field.data, image)
    np.testing.assert_array_equal(
        np.ma.getmaskarray(field),
        np.array(
            [
                [True, True, False, True, True],
                [True, False, False, False, True],
                [False, False, False, False, False],
                [True, False, False, False, True],
                [True, True, False, True, True],
            ]
        ),
    )


def test_etched_master_keeps_master_and_overlay_selection_separate(
    small_kinematical_execution: KinematicalExecution,
) -> None:
    execution = small_kinematical_execution

    assert load_kinematical_recipe(RECIPE).promoted_style == "quiet"
    assert set(execution.figures) == FIGURE_NAMES
    assert execution.simulation.reflector_catalog["master"]["relative_factor"] == 0.03
    assert execution.simulation.reflector_catalog["overlays"]["balanced"]["relative_factor"] == 0.14
    assert execution.simulation.reflector_catalog["overlays"]["quiet"]["relative_factor"] == 0.22


def test_all_six_real_figures_have_the_requested_format_and_canvas(
    small_kinematical_execution: KinematicalExecution,
) -> None:
    figures = small_kinematical_execution.figures

    svg = figures["kinematical-stereographic-bands.svg"]
    assert svg.lstrip().startswith(b"<?xml")
    assert b"<svg" in svg
    assert b"<path" in svg
    for name in FIGURE_NAMES - {"kinematical-stereographic-bands.svg"}:
        payload = figures[name]
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(BytesIO(payload)) as image:
            assert image.size == (320, 320)
            assert image.getbbox() is not None
            extrema = image.convert("L").getextrema()
            assert extrema[0] < extrema[1]


def test_detector_overlay_is_not_obscured_by_filled_annotation_markers(
    small_kinematical_execution: KinematicalExecution,
) -> None:
    payload = small_kinematical_execution.figures["kinematical-detector-overlay.png"]
    with Image.open(BytesIO(payload)) as image:
        rgb = np.asarray(image.convert("RGB"))

    near_white_fraction = np.mean(np.all(rgb > 245, axis=-1))
    assert near_white_fraction < 0.10


def test_rendering_is_byte_deterministic_and_does_not_mutate_scientific_arrays(
    small_render_inputs,
) -> None:
    _, recipe, simulation, context = small_render_inputs
    master_before = simulation.master_stereographic.intensity.copy()
    lambert_before = simulation.master_lambert.intensity.copy()
    detector_before = simulation.detector.intensity.copy()

    first = render_kinematical_figures(context, simulation, recipe)
    second = render_kinematical_figures(context, simulation, recipe)

    assert first == second
    np.testing.assert_array_equal(simulation.master_stereographic.intensity, master_before)
    np.testing.assert_array_equal(simulation.master_lambert.intensity, lambert_before)
    np.testing.assert_array_equal(simulation.detector.intensity, detector_before)


def test_projection_ledger_records_fixed_spherical_camera_and_renderers(
    small_render_inputs,
) -> None:
    _, _, simulation, _ = small_render_inputs
    spherical = simulation.projection_ledger["projections"]["spherical"]

    assert spherical["projection"] == "spherical"
    assert spherical["backend"] == "matplotlib"
    assert set(spherical["camera_deg"]) == {"elevation", "azimuth", "roll"}
    assert spherical["renderer_versions"] == {
        "kikuchipy": version("kikuchipy"),
        "matplotlib": version("matplotlib"),
    }

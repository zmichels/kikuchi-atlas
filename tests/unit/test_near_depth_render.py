from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.render import render_kinematical_figures
from kikuchi_lab.near_depth import load_near_depth_recipe
from kikuchi_lab.near_depth.overlap import compute_overlap_field
from kikuchi_lab.near_depth.render import render_near_depth, render_quiet_control
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases" / "ice-ih" / "source.yml"
BASE_RECIPE = ROOT / "recipes" / "kinematical" / "ice-ih-oxygen-quiet-proof.yml"
TREATMENT_RECIPE = (
    ROOT / "recipes" / "presentation" / "ice-ih-near-depth-stepped.yml"
)


@pytest.fixture(scope="module")
def small_ice_render_inputs():
    source = load_structure_record(SOURCE)
    loaded_base = load_kinematical_recipe(BASE_RECIPE)
    base = replace(
        loaded_base,
        half_size=16,
        detector=replace(loaded_base.detector, shape=(96, 128)),
        figure_size_px=320,
    )
    treatment = replace(load_near_depth_recipe(TREATMENT_RECIPE), figure_size_px=320)
    simulation, context = simulate_kinematical_arrays(source, base)
    overlap = compute_overlap_field(
        context.master_simulator.reflectors,
        size=simulation.master_stereographic.intensity.shape[-1],
        relative_factor=treatment.overlap_relative_factor,
        weight_exponent=treatment.weight_exponent,
        normalization_percentile=treatment.normalization_percentile,
    )
    quiet = render_kinematical_figures(context, simulation, base)[
        "etched-master-quiet.png"
    ]
    return context, simulation, base, treatment, overlap, quiet


def test_renderer_emits_approved_png_inventory_and_sizes(
    small_ice_render_inputs,
) -> None:
    result = render_near_depth(*small_ice_render_inputs)

    assert set(result.figures) == {
        "etched-master-near-depth-stepped.png",
        "quiet-vs-near-depth-stepped.png",
    }
    expected_sizes = {
        "etched-master-near-depth-stepped.png": (320, 320),
        "quiet-vs-near-depth-stepped.png": (640, 320),
    }
    for name, payload in result.figures.items():
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(BytesIO(payload)) as image:
            assert image.size == expected_sizes[name]
            assert image.convert("L").getextrema()[0] < image.convert("L").getextrema()[1]
    with Image.open(BytesIO(result.diagnostic_png)) as image:
        assert image.size == (320, 320)


def test_quiet_control_reuses_the_existing_renderer_byte_for_byte(
    small_ice_render_inputs,
) -> None:
    context, simulation, base, _, _, quiet = small_ice_render_inputs

    control = render_quiet_control(
        context,
        simulation,
        base,
        figure_size_px=320,
    )

    assert control == quiet


def test_depth_disk_uses_the_same_inset_as_the_quiet_control(
    small_ice_render_inputs,
) -> None:
    result = render_near_depth(*small_ice_render_inputs)
    quiet = small_ice_render_inputs[-1]

    def non_background_bounds(payload: bytes) -> tuple[int, int, int, int]:
        with Image.open(BytesIO(payload)) as image:
            rgb = np.asarray(image.convert("RGB"))
        mask = np.any(rgb != np.array([16, 21, 25], dtype=np.uint8), axis=-1)
        rows, columns = np.nonzero(mask)
        return columns.min(), rows.min(), columns.max(), rows.max()

    assert non_background_bounds(
        result.figures["etched-master-near-depth-stepped.png"]
    ) == non_background_bounds(quiet)


def test_renderer_propagates_exact_boundary_then_center_styles(
    small_ice_render_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kikuchi_lab.near_depth.render as module

    observed: list[tuple[str, dict[str, object]]] = []
    real_draw = module._draw_paths

    def spy_draw(*args, mode, style, **kwargs):
        observed.append((mode, style.to_dict()))
        return real_draw(*args, mode=mode, style=style, **kwargs)

    monkeypatch.setattr(module, "_draw_paths", spy_draw)
    render_near_depth(*small_ice_render_inputs)

    assert observed == [
        (
            "bands",
            {
                "relative_factor": 0.34,
                "width_pt": 0.38,
                "alpha": 0.48,
                "casing_width_pt": 0.82,
                "casing_alpha": 0.30,
            },
        ),
        (
            "lines",
            {
                "relative_factor": 0.22,
                "width_pt": 0.42,
                "alpha": 0.62,
                "casing_width_pt": 0.82,
                "casing_alpha": 0.38,
            },
        ),
    ]


def test_renderer_is_deterministic_and_does_not_mutate_inputs(
    small_ice_render_inputs,
) -> None:
    context, simulation, base, treatment, overlap, quiet = small_ice_render_inputs
    master_before = simulation.master_stereographic.intensity.copy()
    raw_before = overlap.raw.copy()
    normalized_before = overlap.normalized.copy()
    quiet_hash = sha256(quiet).hexdigest()

    first = render_near_depth(context, simulation, base, treatment, overlap, quiet)
    second = render_near_depth(context, simulation, base, treatment, overlap, quiet)

    assert first.figures == second.figures
    assert first.diagnostic_png == second.diagnostic_png
    assert first.ledger == second.ledger
    np.testing.assert_array_equal(simulation.master_stereographic.intensity, master_before)
    np.testing.assert_array_equal(overlap.raw, raw_before)
    np.testing.assert_array_equal(overlap.normalized, normalized_before)
    assert sha256(quiet).hexdigest() == quiet_hash


def test_depth_ledger_is_explicitly_presentation_only(
    small_ice_render_inputs,
) -> None:
    result = render_near_depth(*small_ice_render_inputs)

    assert result.ledger["scientific_claim"] == "presentation_only"
    assert result.ledger["spatial_filter"] == "none"
    assert result.ledger["interpolation"] == "nearest"
    assert result.ledger["optical_depth"]["equation"] == (
        "L_max * (1 - exp(-(-log(1 - B/L_max) + gain * overlap_normalized)))"
    )
    assert result.ledger["vector_layers"]["boundary"]["mode"] == "bands"
    assert result.ledger["vector_layers"]["center"]["mode"] == "lines"

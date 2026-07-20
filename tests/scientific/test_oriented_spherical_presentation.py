from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.render import asinh_tone_map
from kikuchi_lab.near_depth import load_near_depth_recipe
from kikuchi_lab.near_depth.overlap import apply_optical_depth, compute_overlap_field
from kikuchi_lab.sources.structure import load_structure_record
from kikuchi_lab.spherical_intensity.presentation import (
    build_presentation_source,
    evaluate_presentation,
)


ROOT = Path(__file__).parents[2]


@lru_cache(maxsize=1)
def _ice_inputs():
    base_path = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
    base = replace(
        load_kinematical_recipe(base_path),
        half_size=32,
        figure_size_px=480,
    )
    source_path = (base_path.parent / base.source_record).resolve()
    structure = load_structure_record(source_path)
    simulation, context = simulate_kinematical_arrays(structure, base)
    treatment = load_near_depth_recipe(
        ROOT / "recipes/presentation/ice-ih-near-depth-stepped-field-led.yml"
    )
    return simulation, context, base, treatment


def _ice_source():
    simulation, context, base, treatment = _ice_inputs()
    return build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        base,
        treatment,
    )


def test_identity_upper_matches_existing_field_led_recipe() -> None:
    simulation, context, ice_base_recipe, ice_treatment = _ice_inputs()
    source = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        ice_base_recipe,
        ice_treatment,
    )
    size = simulation.master_stereographic.intensity.shape[-1]
    overlap = compute_overlap_field(
        context.master_simulator.reflectors,
        size=size,
        relative_factor=ice_treatment.overlap_relative_factor,
        weight_exponent=ice_treatment.weight_exponent,
        normalization_percentile=ice_treatment.normalization_percentile,
    )
    base = asinh_tone_map(
        simulation.master_stereographic.intensity[0],
        percentiles=ice_base_recipe.tone_percentiles,
        scale=ice_base_recipe.tone_asinh_scale,
    )
    expected = apply_optical_depth(
        base,
        overlap.normalized,
        gain=ice_treatment.optical_depth_gain,
        luminance_ceiling=ice_treatment.luminance_ceiling,
    )

    actual = evaluate_presentation(source, source.upper_directions)

    np.testing.assert_allclose(
        actual,
        expected[source.upper_valid],
        rtol=0.0,
        atol=2e-7,
    )


@pytest.mark.parametrize("layer", ["center", "boundary"])
def test_presentation_rejects_enabled_vector_layers(layer: str) -> None:
    simulation, context, base, treatment = _ice_inputs()
    with_overlay = replace(
        treatment,
        **{layer: replace(getattr(treatment, layer), enabled=True)},
    )

    with pytest.raises(ValueError, match="vector overlays must be disabled"):
        build_presentation_source(
            simulation.master_stereographic.intensity,
            context.master_simulator.reflectors,
            base,
            with_overlay,
        )


def test_arbitrary_antipodal_directions_preserve_order_and_repetitions() -> None:
    source = _ice_source()
    first = source.upper_directions[5]
    second = source.upper_directions[127]
    directions = np.stack([first, -first, second, first, -second])

    values = evaluate_presentation(source, directions)
    individually = np.concatenate(
        [evaluate_presentation(source, direction[None, :]) for direction in directions]
    )

    np.testing.assert_array_equal(values, individually)
    assert values[0] == values[3]
    assert values.dtype == np.float32
    assert np.all((0.0 <= values) & (values <= source.ceiling))


def test_source_and_ledger_are_immutable_and_presentation_only() -> None:
    source = _ice_source()

    for array in (
        source.toned_master,
        source.band_weights,
        source.upper_directions,
        source.upper_valid,
        source.axial_bands.normals,
    ):
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.flat[0] = 0

    with pytest.raises(TypeError):
        source.ledger["spatial_filter"] = "gaussian"

    assert source.ledger["scientific_claim"] == "presentation_only"
    assert source.ledger["base_tone"] == "pointwise_asinh"
    assert source.ledger["spatial_filter"] == "none"
    assert source.ledger["interpolation"] == "bilinear"
    assert source.ledger["center_overlay"] is False
    assert source.ledger["boundary_overlay"] is False
    assert all(
        fragment not in key for key in source.ledger for fragment in ("blur", "glow", "line")
    )
    assert not hasattr(source, "pixel_band_cube")
    assert not hasattr(source, "vector_paths")


def test_build_does_not_modify_the_scientific_master() -> None:
    simulation, context, base, treatment = _ice_inputs()
    master = simulation.master_stereographic.intensity
    before = master.copy()

    build_presentation_source(
        master,
        context.master_simulator.reflectors,
        base,
        treatment,
    )

    np.testing.assert_array_equal(master, before)
    assert master.tobytes() == before.tobytes()


@pytest.mark.parametrize(
    ("transform", "message"),
    [
        (lambda master: master.astype(np.float64), "float32"),
        (lambda master: master[0], r"shape \(2, N, N\)"),
        (
            lambda master: np.full_like(master, np.nan),
            "finite",
        ),
    ],
)
def test_build_rejects_invalid_scientific_masters(transform, message: str) -> None:
    simulation, context, base, treatment = _ice_inputs()
    invalid = transform(simulation.master_stereographic.intensity)

    with pytest.raises(ValueError, match=message):
        build_presentation_source(
            invalid,
            context.master_simulator.reflectors,
            base,
            treatment,
        )


@pytest.mark.parametrize(
    ("directions", "message"),
    [
        (np.zeros((2, 2)), r"shape \(M, 3\)"),
        (np.array([[np.nan, 0.0, 1.0]]), "finite"),
        (np.array([[0.0, 0.0, 2.0]]), "unit vectors"),
    ],
)
def test_evaluation_rejects_invalid_crystal_directions(
    directions: np.ndarray,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate_presentation(_ice_source(), directions)

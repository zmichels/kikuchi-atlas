from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from kikuchipy.simulations import KikuchiPatternSimulator
from orix.projections import InverseStereographicProjection

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _enumerate_reflectors,
    _phase_from_record,
    _select_reflectors,
)
from kikuchi_lab.near_depth.overlap import (
    accumulate_additional_overlap,
    apply_optical_depth,
    collapse_antipodal_reflectors,
    compute_overlap_field,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases" / "ice-ih" / "source.yml"
RECIPE = ROOT / "recipes" / "kinematical" / "ice-ih-oxygen-quiet-proof.yml"


@pytest.fixture(scope="module")
def ice_quiet_reflectors():
    record = load_structure_record(SOURCE)
    recipe = load_kinematical_recipe(RECIPE)
    enumerated = _enumerate_reflectors(_phase_from_record(record), recipe)
    return _select_reflectors(enumerated, 0.22, recipe.energy_kev)


def test_additional_overlap_is_zero_for_empty_and_single_band_fields() -> None:
    directions = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])

    empty = accumulate_additional_overlap(
        directions=directions,
        normals=np.empty((0, 3)),
        half_width_sines=np.empty(0),
        weights=np.empty(0),
    )
    single = accumulate_additional_overlap(
        directions=directions,
        normals=np.array([[0.0, 1.0, 0.0]]),
        half_width_sines=np.array([0.1]),
        weights=np.array([1.0]),
    )

    np.testing.assert_array_equal(empty, [0.0, 0.0])
    np.testing.assert_array_equal(single, [0.0, 0.0])


def test_intersection_depth_is_sum_minus_strongest_band() -> None:
    result = accumulate_additional_overlap(
        directions=np.array([[0.0, 0.0, 1.0]]),
        normals=np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.0 / np.sqrt(2.0), 1.0 / np.sqrt(2.0), 0.0],
            ]
        ),
        half_width_sines=np.array([0.1, 0.1, 0.1]),
        weights=np.array([1.0, 0.5, 0.25]),
    )

    assert result[0] == pytest.approx(0.75)


def test_ice_antipodal_collapse_is_deterministic_and_preserves_orders(
    ice_quiet_reflectors,
) -> None:
    forward = collapse_antipodal_reflectors(ice_quiet_reflectors)
    reverse = collapse_antipodal_reflectors(ice_quiet_reflectors[::-1])

    assert ice_quiet_reflectors.size == 524
    assert len({tuple(np.rint(hkl).astype(int)) for hkl in ice_quiet_reflectors.hkl}) == 426
    assert forward.hkl.shape == (213, 3)
    np.testing.assert_array_equal(forward.hkl, reverse.hkl)
    np.testing.assert_allclose(forward.normals, reverse.normals, rtol=0, atol=1e-14)
    np.testing.assert_allclose(forward.theta_radian, reverse.theta_radian)
    np.testing.assert_allclose(forward.structure_factor_abs, reverse.structure_factor_abs)
    assert (0, 0, 2) in map(tuple, forward.hkl)
    assert (0, 0, 6) in map(tuple, forward.hkl)


def test_analytic_boundary_matches_kikuchipy_plotted_bragg_boundary(
    ice_quiet_reflectors,
) -> None:
    pair = ice_quiet_reflectors[
        np.array(
            [tuple(int(round(v)) for v in hkl) in {(0, 0, 2), (0, 0, -2)}
             for hkl in ice_quiet_reflectors.hkl]
        )
    ]
    figure = KikuchiPatternSimulator(pair).plot(
        projection="stereographic",
        mode="bands",
        hemisphere="upper",
        return_figure=True,
        backend="matplotlib",
    )
    boundary = figure.axes[0].lines[0]
    x = np.asarray(boundary.get_xdata(), dtype=np.float64)
    y = np.asarray(boundary.get_ydata(), dtype=np.float64)
    directions = np.asarray(
        InverseStereographicProjection(pole=-1).xy2vector(x, y).data,
        dtype=np.float64,
    )
    normal = np.asarray(pair.unit.data[0], dtype=np.float64)

    np.testing.assert_allclose(
        np.abs(directions @ normal),
        np.sin(float(pair.theta[0])),
        rtol=0,
        atol=2e-12,
    )


def test_real_ice_overlap_field_is_finite_bounded_and_positive(
    ice_quiet_reflectors,
) -> None:
    field = compute_overlap_field(
        ice_quiet_reflectors,
        size=65,
        relative_factor=0.22,
        weight_exponent=2.0,
        normalization_percentile=99.5,
    )

    assert field.raw.shape == (65, 65)
    assert field.raw.dtype == np.float32
    assert field.normalized.dtype == np.float32
    assert field.valid_disk.dtype == np.bool_
    assert field.axial_band_count == 213
    assert np.isfinite(field.raw).all()
    assert np.isfinite(field.normalized).all()
    assert field.normalization_value > 0
    assert np.max(field.raw) > 0
    assert np.min(field.normalized) == 0
    assert np.max(field.normalized) == 1
    np.testing.assert_array_equal(field.raw[~field.valid_disk], 0.0)
    np.testing.assert_array_equal(field.normalized[~field.valid_disk], 0.0)


def test_optical_depth_is_identity_at_zero_monotonic_and_below_ceiling() -> None:
    base = np.array([0.2, 0.2, 0.8], dtype=np.float32)
    overlap = np.array([0.0, 0.5, 1.0], dtype=np.float32)

    result = apply_optical_depth(
        base,
        overlap,
        gain=0.28,
        luminance_ceiling=0.985,
    )

    assert result.dtype == np.float32
    assert result[0] == base[0]
    assert base[1] < result[1] < result[2] < 0.985
    assert np.isfinite(result).all()


def test_optical_depth_rejects_base_above_ceiling() -> None:
    with pytest.raises(ValueError, match="exceeds luminance ceiling"):
        apply_optical_depth(
            np.array([0.99]),
            np.array([0.5]),
            gain=0.28,
            luminance_ceiling=0.985,
        )

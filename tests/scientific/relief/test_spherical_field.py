from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import kikuchi_lab.relief.field as field_module
from kikuchi_lab.model.persistence import load_master_product
from kikuchi_lab.relief.field import (
    DirectionalSamples,
    build_spherical_scalar_field,
    directions_to_lambert_square,
    interpolate_sample_ledger,
    lambert_square_to_directions,
    sample_spherical_field,
)
from kikuchi_lab.relief.recipes import load_relief_globe_recipe
from tests.relief_fixtures import analytic_master_product, expectation_for


def test_lambert_landmarks_and_round_trip():
    square = np.array([[0, 0], [1, 0], [0, 1], [-1, 0], [0, -1]], dtype=float)
    directions = lambert_square_to_directions(square[:, 0], square[:, 1], hemisphere=1)
    assert np.allclose(directions[0], [0, 0, 1], atol=1e-14, rtol=0)
    assert np.allclose(
        directions[1:],
        [[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]],
        atol=1e-14,
        rtol=0,
    )
    assert np.allclose(directions_to_lambert_square(directions), square, atol=1e-14, rtol=0)


def test_project_mapping_matches_pinned_kikuchipy_reference():
    from kikuchipy.signals.util._master_pattern import _vector2lambert

    rng = np.random.default_rng(7142026)
    directions = rng.normal(size=(128, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    expected = _vector2lambert(directions) / np.sqrt(np.pi / 2.0)
    assert np.allclose(directions_to_lambert_square(directions), expected, atol=2e-14, rtol=0)


@pytest.mark.parametrize("hemisphere", [-1, 1])
def test_inverse_lambert_round_trip_covers_interior_quadrants(hemisphere):
    square = np.array(
        [
            [0.62, 0.17],
            [0.19, 0.58],
            [-0.61, 0.16],
            [-0.18, 0.54],
            [-0.57, -0.21],
            [-0.16, -0.63],
            [0.59, -0.14],
            [0.22, -0.56],
        ],
        dtype=np.float64,
    )

    directions = lambert_square_to_directions(square[:, 0], square[:, 1], hemisphere=hemisphere)

    assert np.all(np.sign(directions[:, 2]) == hemisphere)
    assert np.allclose(np.linalg.norm(directions, axis=1), 1.0, atol=2e-15, rtol=0)
    assert np.allclose(directions_to_lambert_square(directions), square, atol=2e-14, rtol=0)


def test_field_owns_one_equator_and_exact_source_identity():
    master = analytic_master_product(size=9)
    field = build_spherical_scalar_field(master, expectation_for(master))
    boundary_count = 4 * 9 - 4
    assert len(field.raw_values) == 2 * 9 * 9 - boundary_count
    assert field.master_product_id == master.product_id
    assert field.seam.maximum_normalized_residual == 0.0
    assert field.seam.equator_owner == "north"
    assert not field.directions.flags.writeable
    assert field.intensity_units == "raw dynamical intensity"
    assert field.source_array_shape == (2, 9, 9)
    assert field.lambert_transform_contract == (
        "callahan-emsoft-square-lambert/v1"
    )
    assert all(type(value) is int for value in field.source_array_shape)


def test_field_identity_changes_with_lambert_transform_contract(monkeypatch):
    master = analytic_master_product(size=9)
    expected = expectation_for(master)
    original = build_spherical_scalar_field(master, expected)
    monkeypatch.setattr(
        field_module,
        "LAMBERT_TRANSFORM_CONTRACT",
        "callahan-emsoft-square-lambert/test-change",
    )

    changed = build_spherical_scalar_field(master, expected)

    assert changed.field_id != original.field_id
    assert changed.lambert_transform_contract.endswith("/test-change")


def test_transform_field_and_sample_arrays_are_immutable_float64_or_int64():
    directions = lambert_square_to_directions([0.0], [0.0], hemisphere=1)
    square = directions_to_lambert_square(directions)
    master = analytic_master_product(size=9)
    field = build_spherical_scalar_field(master, expectation_for(master))
    sampled = sample_spherical_field(field, directions)

    float_arrays = [
        directions,
        square,
        field.north_grid,
        field.south_grid,
        field.directions,
        field.raw_values,
        sampled.directions,
        sampled.raw_values,
        sampled.weights,
    ]
    int_arrays = [
        field.source_hemisphere,
        field.source_rows,
        field.source_columns,
        sampled.hemisphere,
        sampled.source_rows,
        sampled.source_columns,
    ]
    assert all(array.dtype == np.float64 for array in float_arrays)
    assert all(array.dtype == np.int64 for array in int_arrays)
    assert all(not array.flags.writeable for array in float_arrays + int_arrays)


def test_bilinear_sampling_recovers_selected_source_nodes():
    master = analytic_master_product(size=9)
    field = build_spherical_scalar_field(master, expectation_for(master))
    indices = np.array([0, 10, 40, 72, 80])
    sampled = sample_spherical_field(field, field.directions[indices])
    assert np.allclose(sampled.raw_values, field.raw_values[indices], atol=2e-6, rtol=0)
    assert np.allclose(sampled.weights.sum(axis=1), 1.0, atol=1e-15, rtol=0)


def test_fractional_interpolation_ledger_uses_corner_order_and_hemisphere():
    north = np.array([[0.0, 10.0, 20.0], [100.0, 110.0, 120.0], [200.0, 210.0, 220.0]])
    south = north + 1000.0
    samples = DirectionalSamples(
        directions=np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]),
        raw_values=np.zeros(2),
        hemisphere=np.array([1, -1]),
        source_rows=np.array([[0, 1], [1, 2]]),
        source_columns=np.array([[1, 2], [0, 1]]),
        weights=np.array([[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]]),
    )

    result = interpolate_sample_ledger(north, south, samples)

    assert np.allclose(result, [77.0, 1143.0], atol=1e-13, rtol=0)


@pytest.mark.parametrize(
    ("ledger_name", "component", "invalid_index"),
    [
        ("rows", 0, -1),
        ("rows", 0, 3),
        ("rows", 1, -1),
        ("rows", 1, 3),
        ("columns", 0, -1),
        ("columns", 0, 3),
        ("columns", 1, -1),
        ("columns", 1, 3),
    ],
)
def test_interpolation_ledger_rejects_every_out_of_bounds_index(
    ledger_name, component, invalid_index
):
    rows = np.array([[0, 1]])
    columns = np.array([[0, 1]])
    ledger = rows if ledger_name == "rows" else columns
    ledger[0, component] = invalid_index
    samples = DirectionalSamples(
        directions=np.array([[0.0, 0.0, 1.0]]),
        raw_values=np.zeros(1),
        hemisphere=np.array([1]),
        source_rows=rows,
        source_columns=columns,
        weights=np.array([[0.25, 0.25, 0.25, 0.25]]),
    )

    with pytest.raises(ValueError, match="indices exceed grid bounds"):
        interpolate_sample_ledger(np.zeros((3, 3)), np.ones((3, 3)), samples)


def test_field_rejects_equator_mismatch():
    master = analytic_master_product(size=9, seam_offset=0.1)
    with pytest.raises(ValueError, match="equator seam residual"):
        build_spherical_scalar_field(master, expectation_for(master))


def test_real_501_master_has_one_exact_equator():
    source = Path(
        "/Users/Z/Documents/kikuchi/local/benchmarks/forsterite-resolution-501/"
        "COD-9000319-ebsdsim.bundle/master-437f865cd0f68384.npz"
    )
    if not source.is_file():
        pytest.skip("local 501 master product is unavailable")
    master = load_master_product(source)
    recipe = load_relief_globe_recipe("recipes/relief/forsterite-intensity-globe.yml")
    field = build_spherical_scalar_field(master, recipe.source)
    assert master.intensity.shape == (2, 501, 501)
    assert len(field.raw_values) == 500002
    assert field.seam.maximum_normalized_residual == 0.0

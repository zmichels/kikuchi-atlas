from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.model.persistence import load_master_product
from kikuchi_lab.relief.field import (
    build_spherical_scalar_field,
    directions_to_lambert_square,
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


def test_field_owns_one_equator_and_exact_source_identity():
    master = analytic_master_product(size=9)
    field = build_spherical_scalar_field(master, expectation_for(master))
    boundary_count = 4 * 9 - 4
    assert len(field.raw_values) == 2 * 9 * 9 - boundary_count
    assert field.master_product_id == master.product_id
    assert field.seam.maximum_normalized_residual == 0.0
    assert field.seam.equator_owner == "north"
    assert not field.directions.flags.writeable


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

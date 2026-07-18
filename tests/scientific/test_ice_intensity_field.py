from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.ice_globe.intensity import (
    build_ice_intensity_field,
    sample_stereographic_grid,
)
from kikuchi_lab.kinematical.contracts import (
    KinematicalArrayProduct,
    KinematicalSimulation,
)
from kikuchi_lab.workflows.ice_kinematical import simulate_ice_kinematical


ROOT = Path(__file__).parents[2]
KINEMATICAL_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"


def _simulation(master: np.ndarray) -> KinematicalSimulation:
    return KinematicalSimulation(
        KinematicalArrayProduct.from_array(
            "test stereographic master",
            master,
            metadata={"projection": "stereographic", "hemisphere": "both"},
        ),
        reflector_catalog={},
        projection_ledger={},
    )


def test_ice_intensity_field_comes_from_master_values_not_reflector_ridges() -> None:
    field = build_ice_intensity_field(simulate_ice_kinematical(KINEMATICAL_RECIPE))

    assert field.source_kind == "kinematical_stereographic_master"
    assert field.field_id.startswith("ice-intensity-field-")
    assert field.raw_values.ptp() > 0.0


def test_intensity_raw_values_are_only_the_unit_stereographic_disk() -> None:
    upper = np.arange(25, dtype=np.float32).reshape(5, 5)
    lower = upper + 100.0
    # These pixels are outside X^2 + Y^2 <= 1 and must never become global
    # percentile inputs just because they are inside the square image raster.
    coordinates = np.linspace(-1.0, 1.0, 5)
    outside = coordinates[:, None] ** 2 + coordinates[None, :] ** 2 > 1.0
    upper[outside], lower[outside] = -1_000_000.0, 1_000_000.0
    equator = coordinates[:, None] ** 2 + coordinates[None, :] ** 2 == 1.0
    lower[equator] = upper[equator]

    field = build_ice_intensity_field(_simulation(np.stack((upper, lower))))

    valid = ~outside
    expected = np.concatenate((upper[valid], lower[valid & ~equator]))
    assert np.array_equal(field.raw_values, expected)
    assert len(field.raw_values) == 22
    assert np.percentile(field.raw_values, 1.0) > -1_000_000.0
    assert np.percentile(field.raw_values, 99.0) < 1_000_000.0


def test_equator_is_upper_owned_and_only_true_disk_boundary_is_diagnosed() -> None:
    upper = np.arange(25, dtype=np.float32).reshape(5, 5)
    lower = upper + 100.0
    coordinates = np.linspace(-1.0, 1.0, 5)
    squared_radius = coordinates[:, None] ** 2 + coordinates[None, :] ** 2
    equator, outside = squared_radius == 1.0, squared_radius > 1.0
    # Square-border but off-disk disagreement is irrelevant to the equator.
    lower[equator] = upper[equator]
    lower[outside] += 10_000.0
    field = build_ice_intensity_field(_simulation(np.stack((upper, lower))))

    assert field.seam.equator_owner == "upper"
    assert field.seam.boundary_count == int(np.count_nonzero(equator)) == 4
    assert field.seam.maximum_absolute_residual == 0.0
    assert all(np.count_nonzero(field.raw_values == value) == 1 for value in upper[equator])

    lower[equator] += 1.0
    with pytest.raises(ValueError, match="equator seam residual"):
        build_ice_intensity_field(_simulation(np.stack((upper, lower))))


def test_sampling_near_disk_edge_ignores_square_corner_values() -> None:
    upper = np.ones((5, 5), dtype=np.float32)
    lower = np.ones((5, 5), dtype=np.float32)
    coordinates = np.linspace(-1.0, 1.0, 5)
    outside = coordinates[:, None] ** 2 + coordinates[None, :] ** 2 > 1.0
    upper[outside], lower[outside] = 1_000_000.0, 1_000_000.0
    field = build_ice_intensity_field(_simulation(np.stack((upper, lower))))

    # This point maps near the circular edge; ordinary square-grid bilinear
    # interpolation would mix in the invalid high-valued corner at (1, 1).
    q = np.array([0.75, 0.50])
    radius_squared = float(q @ q)
    direction = np.array(
        [
            2.0 * q[0],
            2.0 * q[1],
            1.0 - radius_squared,
        ]
    ) / (1.0 + radius_squared)

    value = sample_stereographic_grid(
        field,
        [direction],
        upper_grid=field.upper_grid,
        lower_grid=field.lower_grid,
    )[0]

    assert value == pytest.approx(1.0)

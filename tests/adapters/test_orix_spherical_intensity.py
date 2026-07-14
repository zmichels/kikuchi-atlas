"""Direct parity checks against the public orix stereographic projections."""

from importlib import import_module
from pathlib import Path
import sys

import numpy as np

from orix.projections import InverseStereographicProjection, StereographicProjection
from orix.vector import Vector3d


sys.path.insert(0, str(Path(__file__).parents[1]))
small_spherical_build = import_module("spherical_fixtures").small_spherical_build


def test_cardinal_vectors_match_public_orix() -> None:
    upper = InverseStereographicProjection(pole=-1).xy2vector(
        np.array([0.0, 1.0]), np.array([0.0, 0.0])
    )
    lower = InverseStereographicProjection(pole=1).xy2vector(
        np.array([0.0, 1.0]), np.array([0.0, 0.0])
    )
    np.testing.assert_allclose(upper.data, [[0, 0, 1], [1, 0, 0]], atol=1e-15)
    np.testing.assert_allclose(lower.data, [[0, 0, -1], [1, 0, 0]], atol=1e-15)


def test_exported_vectors_are_the_public_orix_mapping_in_exact_source_order() -> None:
    build = small_spherical_build()
    size = 5
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    tolerance = 32 * np.finfo(np.float64).eps
    radius_squared = x_grid * x_grid + y_grid * y_grid
    inside = radius_squared <= 1.0 + tolerance
    equator = np.abs(radius_squared - 1.0) <= tolerance
    expected = np.concatenate(
        [
            InverseStereographicProjection(pole=-1)
            .xy2vector(x_grid[inside], y_grid[inside])
            .data,
            InverseStereographicProjection(pole=1)
            .xy2vector(x_grid[inside & ~equator], y_grid[inside & ~equator])
            .data,
        ]
    )
    np.testing.assert_array_equal(build.field.xyz, expected)


def test_exported_vectors_round_trip_with_public_orix() -> None:
    build = small_spherical_build()
    for hemisphere, pole in ((1, -1), (-1, 1)):
        selected = build.field.hemisphere == hemisphere
        vectors = Vector3d(build.field.xyz[selected])
        x, y = StereographicProjection(pole=pole).vector2xy(vectors)
        round_trip = InverseStereographicProjection(pole=pole).xy2vector(x, y)
        cross = np.linalg.norm(np.cross(vectors.data, round_trip.data), axis=1)
        dot = np.sum(vectors.data * round_trip.data, axis=1)
        angular = np.arctan2(cross, dot)
        assert float(np.max(angular, initial=0.0)) <= 1e-10

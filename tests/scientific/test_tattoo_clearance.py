from __future__ import annotations

import importlib
import math
from types import ModuleType

import numpy as np
import pytest

from kikuchi_lab.art_products.contracts import TattooGeometry, TattooPath


def _vector() -> ModuleType:
    return importlib.import_module("kikuchi_lab.art_products.tattoo_vector")


def _path(index: int, points: list[list[float]], *, width_mm: float = 0.8) -> TattooPath:
    if index < 4:
        tier = "dominant"
    elif index < 8:
        tier = "secondary"
    else:
        tier = "fine"
    return TattooPath(
        member_id=f"member-{index:02d}",
        tier=tier,
        width_mm=width_mm,
        points_mm=points,
        score_components={"strength": 1.0},
        selection_reason="deliberate physical-clearance fixture",
    )


def _radial_path(index: int) -> TattooPath:
    angle = (index + 0.5) * math.pi / 13.0
    direction = np.array([math.cos(angle), math.sin(angle)])
    center = np.array([72.5, 72.5])
    endpoints = np.vstack((center - 60.0 * direction, center + 60.0 * direction))
    return _path(index, endpoints.tolist())


def _geometry(*leading: TattooPath) -> TattooGeometry:
    paths = list(leading)
    paths.extend(_radial_path(index) for index in range(len(paths), 11))
    return TattooGeometry(
        schema_version=1,
        catalog_id="catalog-clearance-test",
        orientation_id="orientation-clearance-test",
        artboard_size_mm=145.0,
        paths=tuple(paths),
        projection="upper_specimen_stereographic_center_trace",
    )


def test_true_transverse_crossings_are_clearance_exempt() -> None:
    geometry = _geometry()

    assert _vector().validate_tattoo_geometry(geometry) is None


@pytest.mark.parametrize(
    ("first_points", "second_points"),
    [
        ([[10.0, 20.0], [20.0, 20.0]], [[20.0, 20.0], [20.0, 30.0]]),
        (
            [[10.0, 20.0], [30.0, 20.0]],
            [[15.0, 25.0], [20.0, 20.0], [25.0, 25.0]],
        ),
    ],
    ids=("endpoint-contact", "tangent-contact"),
)
def test_endpoint_and_tangent_contacts_are_not_crossing_exempt(
    first_points: list[list[float]],
    second_points: list[list[float]],
) -> None:
    geometry = _geometry(_path(0, first_points), _path(1, second_points))

    with pytest.raises(ValueError, match="noncrossing edge gap"):
        _vector().validate_tattoo_geometry(geometry)


def test_collinear_contact_is_not_crossing_exempt() -> None:
    first = _path(0, [[10.0, 20.0], [30.0, 20.0]])
    second = _path(1, [[20.0, 20.0], [40.0, 20.0]])

    with pytest.raises(ValueError, match="noncrossing edge gap"):
        _vector().validate_tattoo_geometry(_geometry(first, second))


def test_noncrossing_edge_gap_of_1_49_mm_fails() -> None:
    first = _path(0, [[10.0, 40.0], [135.0, 40.0]])
    second = _path(1, [[10.0, 42.29], [135.0, 42.29]])

    with pytest.raises(
        ValueError,
        match=r"noncrossing edge gap 1\.490000 mm is below 1\.500000 mm",
    ):
        _vector().validate_tattoo_geometry(_geometry(first, second))


def test_endpoint_clearance_of_1_99_mm_fails_after_edge_gap_passes() -> None:
    ending_path = _path(0, [[10.0, 50.0], [50.0, 50.0]])
    unrelated_path = _path(1, [[52.39, 40.0], [52.39, 60.0]])

    with pytest.raises(
        ValueError,
        match=r"endpoint clearance 1\.990000 mm is below 2\.000000 mm",
    ):
        _vector().validate_tattoo_geometry(_geometry(ending_path, unrelated_path))


def test_closed_path_fails_validation() -> None:
    closed = _path(0, [[10.0, 10.0], [20.0, 20.0], [10.0, 10.0]])

    with pytest.raises(ValueError, match="path must be open"):
        _vector().validate_tattoo_geometry(_geometry(closed))


def test_duplicate_consecutive_points_fail_validation() -> None:
    duplicated = _path(
        0,
        [[10.0, 10.0], [20.0, 20.0], [20.0, 20.0], [30.0, 30.0]],
    )

    with pytest.raises(ValueError, match="duplicate consecutive points"):
        _vector().validate_tattoo_geometry(_geometry(duplicated))

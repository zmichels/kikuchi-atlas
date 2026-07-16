from __future__ import annotations

import importlib
import math
from types import ModuleType

import numpy as np
import pytest

from kikuchi_lab.art_products.contracts import (
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)


_CENTER = np.array([72.5, 72.5])
_INNER_RADIUS_MM = 63.8


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
    endpoints = np.vstack(
        (
            _CENTER - _INNER_RADIUS_MM * direction,
            _CENTER + _INNER_RADIUS_MM * direction,
        )
    )
    return _path(index, endpoints.tolist())


def _horizontal_chord(y: float) -> list[list[float]]:
    half_width = math.sqrt(
        _INNER_RADIUS_MM**2 - (y - float(_CENTER[1])) ** 2
    )
    return [
        [float(_CENTER[0]) - half_width, y],
        [float(_CENTER[0]) + half_width, y],
    ]


def _boundary() -> TattooBoundary:
    return TattooBoundary(
        schema_version=1,
        role="stereographic_hemisphere_boundary",
        scientific_claim="noncrystallographic_projection_primitive",
        center_mm=(72.5, 72.5),
        outer_diameter_mm=132.0,
        width_mm=2.2,
        ink="#000000",
    )


def _geometry(*leading: TattooPath) -> TattooGeometry:
    paths = list(leading)
    paths.extend(_radial_path(index) for index in range(len(paths), 11))
    return TattooGeometry(
        schema_version=1,
        catalog_id="catalog-clearance-test",
        orientation_id="orientation-clearance-test",
        artboard_size_mm=145.0,
        boundary=_boundary(),
        paths=tuple(paths),
        projection="upper_specimen_stereographic_center_trace",
    )


def test_true_transverse_crossings_are_clearance_exempt() -> None:
    geometry = _geometry()

    assert _vector().validate_tattoo_geometry(geometry) is None


@pytest.mark.parametrize(
    ("first_points", "second_points"),
    [
        (
            [[8.7, 72.5], [136.3, 72.5]],
            [[136.3, 72.5], [72.5, 8.7]],
        ),
        (
            [[8.7, 72.5], [136.3, 72.5]],
            [
                [
                    72.5 - _INNER_RADIUS_MM / math.sqrt(2.0),
                    72.5 - _INNER_RADIUS_MM / math.sqrt(2.0),
                ],
                [72.5, 72.5],
                [
                    72.5 + _INNER_RADIUS_MM / math.sqrt(2.0),
                    72.5 - _INNER_RADIUS_MM / math.sqrt(2.0),
                ],
            ],
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
    first = _path(0, [[8.7, 72.5], [136.3, 72.5]])
    second = _path(1, [[136.3, 72.5], [8.7, 72.5]])

    with pytest.raises(ValueError, match="noncrossing edge gap"):
        _vector().validate_tattoo_geometry(_geometry(first, second))


def test_noncrossing_edge_gap_of_1_49_mm_fails() -> None:
    first = _path(0, _horizontal_chord(60.0))
    second = _path(1, _horizontal_chord(62.29))

    with pytest.raises(
        ValueError,
        match=r"noncrossing edge gap 1\.490000 mm is below 1\.500000 mm",
    ):
        _vector().validate_tattoo_geometry(_geometry(first, second))


def test_endpoint_clearance_of_1_99_mm_fails_after_edge_gap_passes() -> None:
    ending_path = _path(0, _horizontal_chord(74.89))
    unrelated_path = _path(1, _horizontal_chord(72.5))

    with pytest.raises(
        ValueError,
        match=r"endpoint clearance 1\.990000 mm is below 2\.000000 mm",
    ):
        _vector().validate_tattoo_geometry(_geometry(ending_path, unrelated_path))


def test_closed_path_fails_validation() -> None:
    closed = _path(0, [[8.7, 72.5], [72.5, 72.5], [8.7, 72.5]])

    with pytest.raises(ValueError, match="path must be open"):
        _vector().validate_tattoo_geometry(_geometry(closed))


def test_duplicate_consecutive_points_fail_validation() -> None:
    duplicated = _path(
        0,
        [[8.7, 72.5], [72.5, 72.5], [72.5, 72.5], [136.3, 72.5]],
    )

    with pytest.raises(ValueError, match="duplicate consecutive points"):
        _vector().validate_tattoo_geometry(_geometry(duplicated))

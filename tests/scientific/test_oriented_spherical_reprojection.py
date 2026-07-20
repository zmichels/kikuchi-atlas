from __future__ import annotations

import numpy as np
import pytest
from orix.projections import InverseStereographicProjection

from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix
from kikuchi_lab.spherical_intensity.reprojection import (
    inverse_rotate_directions,
    reproject_hemisphere,
    sample_stereographic_channel,
    stereographic_grid,
    stereographic_grid_rows,
)


def indexed_master(size: int) -> np.ndarray:
    values = np.arange(2 * size * size, dtype=np.float32)
    return values.reshape(2, size, size)


def test_identity_returns_source_upper_and_lower_arrays_exactly() -> None:
    master = indexed_master(9)

    for index, hemisphere in enumerate(("upper", "lower")):
        result = reproject_hemisphere(
            master,
            Orientation((0.0, 0.0, 0.0)),
            hemisphere=hemisphere,
            size=9,
            tile_rows=3,
        )

        np.testing.assert_array_equal(
            result.values[result.valid], master[index][result.valid]
        )
        assert (
            result.values[result.valid].tobytes()
            == master[index][result.valid].tobytes()
        )
        assert result.ledger["identity_source_grid_fast_path"] is True
        assert result.ledger["equator_owner"] == "upper"
        assert result.ledger["spatial_filter"] == "none"

    lower = reproject_hemisphere(
        master,
        Orientation((0.0, 0.0, 0.0)),
        hemisphere="lower",
        size=9,
        tile_rows=3,
    )
    rim = ((4, 0), (0, 4), (4, 8), (8, 4))
    for row, column in rim:
        assert lower.valid[row, column]
        assert lower.values[row, column] == master[1, row, column]
        assert lower.source_hemisphere[row, column] == -1
    assert lower.ledger["identity_source_plane_equator_exception"] == (
        "requested_source_plane_including_lower_display_rim"
    )


def test_bilinear_sampler_reproduces_exact_source_nodes() -> None:
    master = indexed_master(9)
    directions = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])

    sampled, hemisphere_index = sample_stereographic_channel(master, directions)

    np.testing.assert_array_equal(
        sampled, [master[0, 4, 4], master[1, 4, 4]]
    )
    np.testing.assert_array_equal(hemisphere_index, [0, 1])


def test_bilinear_sampler_matches_linear_source_plane_between_nodes() -> None:
    size = 9
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinate, coordinate)
    master = np.stack(
        [10.0 + 2.0 * x - 3.0 * y, -4.0 + 0.5 * x + 2.0 * y]
    ).astype(np.float32)
    source_xy = np.array([[0.13, -0.21], [-0.33, 0.27], [0.6, 0.8]])
    directions = np.concatenate(
        [
            np.asarray(
                InverseStereographicProjection(pole=-1)
                .xy2vector(source_xy[[0, 2], 0], source_xy[[0, 2], 1])
                .data,
                dtype=np.float64,
            ),
            np.asarray(
                InverseStereographicProjection(pole=1)
                .xy2vector(source_xy[[1], 0], source_xy[[1], 1])
                .data,
                dtype=np.float64,
            ),
        ]
    )

    sampled, owner = sample_stereographic_channel(master, directions)

    expected = np.array(
        [
            10.0 + 2.0 * 0.13 - 3.0 * -0.21,
            10.0 + 2.0 * 0.6 - 3.0 * 0.8,
            -4.0 + 0.5 * -0.33 + 2.0 * 0.27,
        ]
    )
    np.testing.assert_allclose(sampled, expected, rtol=0.0, atol=1e-6)
    np.testing.assert_array_equal(owner, [0, 0, 1])


def test_sampler_reproduces_linear_xyz_values_at_exact_source_nodes() -> None:
    size = 9
    upper = stereographic_grid(size, "upper")
    lower = stereographic_grid(size, "lower")
    master = np.zeros((2, size, size), dtype=np.float32)
    master[0, upper.valid] = (
        7.0
        + 2.0 * upper.directions[upper.valid, 0]
        - 3.0 * upper.directions[upper.valid, 1]
        + 5.0 * upper.directions[upper.valid, 2]
    )
    master[1, lower.valid] = (
        7.0
        + 2.0 * lower.directions[lower.valid, 0]
        - 3.0 * lower.directions[lower.valid, 1]
        + 5.0 * lower.directions[lower.valid, 2]
    )
    nodes = np.stack([upper.directions[3, 5], lower.directions[5, 3]])

    sampled, owner = sample_stereographic_channel(master, nodes)

    expected = 7.0 + 2.0 * nodes[:, 0] - 3.0 * nodes[:, 1] + 5.0 * nodes[:, 2]
    np.testing.assert_allclose(sampled, expected, rtol=0.0, atol=1e-6)
    np.testing.assert_array_equal(owner, [0, 1])


def test_arbitrary_orientation_pullback_uses_upper_equator_owner() -> None:
    orientation = Orientation((17.0, 31.0, 43.0))
    crystal_equator = np.array([[1.0, 0.0, 0.0]])
    specimen = crystal_equator @ orientation_matrix(orientation).T

    pulled = inverse_rotate_directions(specimen, orientation)
    sampled, owner = sample_stereographic_channel(indexed_master(9), pulled)

    np.testing.assert_allclose(pulled, crystal_equator, rtol=0.0, atol=5e-13)
    np.testing.assert_array_equal(sampled, [indexed_master(9)[0, 4, 8]])
    np.testing.assert_array_equal(owner, [0])


def test_arbitrary_rotation_assigns_every_valid_pixel_once() -> None:
    result = reproject_hemisphere(
        indexed_master(17),
        Orientation((17.0, 31.0, 43.0)),
        hemisphere="upper",
        size=33,
        tile_rows=5,
    )

    assert set(np.unique(result.source_hemisphere[result.valid])) == {-1, 1}
    assert np.isfinite(result.values[result.valid]).all()
    assert np.count_nonzero(result.source_hemisphere[~result.valid]) == 0
    assert np.count_nonzero(result.values[~result.valid]) == 0
    assert not bool(result.valid[0, 0])
    assert result.ledger["identity_source_grid_fast_path"] is False
    assert result.ledger["identity_source_plane_equator_exception"] == "not_applicable"


def test_identity_resampling_uses_general_upper_equator_owner() -> None:
    result = reproject_hemisphere(
        indexed_master(9),
        Orientation((0.0, 0.0, 0.0)),
        hemisphere="lower",
        size=17,
        tile_rows=4,
    )

    assert result.ledger["identity_source_grid_fast_path"] is False
    for row, column in ((8, 0), (0, 8), (8, 16), (16, 8)):
        assert result.valid[row, column]
        assert result.source_hemisphere[row, column] == 1


def test_row_tiling_does_not_change_reprojected_values_or_ownership() -> None:
    master = indexed_master(17)
    orientation = Orientation((17.0, 31.0, 43.0))
    reference = reproject_hemisphere(
        master,
        orientation,
        hemisphere="lower",
        size=31,
        tile_rows=31,
    )

    for tile_rows in (1, 7):
        tiled = reproject_hemisphere(
            master,
            orientation,
            hemisphere="lower",
            size=31,
            tile_rows=tile_rows,
        )
        np.testing.assert_array_equal(tiled.valid, reference.valid)
        np.testing.assert_array_equal(tiled.values, reference.values)
        np.testing.assert_array_equal(
            tiled.source_hemisphere, reference.source_hemisphere
        )


def test_deadline_is_checked_once_per_bounded_row_tile() -> None:
    calls: list[int] = []

    reproject_hemisphere(
        indexed_master(9),
        Orientation((0.0, 0.0, 0.0)),
        hemisphere="upper",
        size=9,
        tile_rows=4,
        check_deadline=lambda: calls.append(len(calls)),
    )

    assert calls == [0, 1, 2]


def test_stereographic_row_tile_matches_the_complete_grid() -> None:
    complete = stereographic_grid(17, "lower")
    tile = stereographic_grid_rows(17, "lower", 4, 11)

    np.testing.assert_array_equal(tile.x, complete.x[4:11])
    np.testing.assert_array_equal(tile.y, complete.y[4:11])
    np.testing.assert_array_equal(tile.valid, complete.valid[4:11])
    np.testing.assert_array_equal(
        tile.directions[tile.valid], complete.directions[4:11][tile.valid]
    )
    np.testing.assert_allclose(
        np.linalg.norm(tile.directions[tile.valid], axis=1),
        1.0,
        rtol=0.0,
        atol=5e-13,
    )
    assert np.isnan(tile.directions[~tile.valid]).all()


@pytest.mark.parametrize(
    "source",
    [
        np.zeros((9, 9), dtype=np.float32),
        np.zeros((1, 9, 9), dtype=np.float32),
        np.zeros((2, 8, 9), dtype=np.float32),
    ],
)
def test_sampler_rejects_invalid_source_shapes(source: np.ndarray) -> None:
    with pytest.raises(ValueError, match=r"shape \(2, N, N\)"):
        sample_stereographic_channel(source, np.array([[0.0, 0.0, 1.0]]))


@pytest.mark.parametrize(
    "source",
    [
        np.zeros((2, 9, 9), dtype=np.float64),
        np.zeros((2, 9, 9), dtype=np.int32),
    ],
)
def test_reprojection_rejects_non_float32_source_channels(source: np.ndarray) -> None:
    with pytest.raises(ValueError, match="float32"):
        reproject_hemisphere(
            source,
            Orientation((0.0, 0.0, 0.0)),
            hemisphere="upper",
            size=9,
            tile_rows=3,
        )


def test_sampler_rejects_nonfinite_source_or_directions() -> None:
    master = indexed_master(9)
    master[0, 4, 4] = np.nan
    with pytest.raises(ValueError, match="finite numeric"):
        sample_stereographic_channel(master, np.array([[0.0, 0.0, 1.0]]))
    with pytest.raises(ValueError, match="shape .* finite"):
        sample_stereographic_channel(
            indexed_master(9), np.array([[np.nan, 0.0, 1.0]])
        )


def test_sampler_and_inverse_rotation_reject_nonunit_directions() -> None:
    direction = np.array([[2.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="unit"):
        sample_stereographic_channel(indexed_master(9), direction)
    with pytest.raises(ValueError, match="unit"):
        inverse_rotate_directions(direction, Orientation((17.0, 31.0, 43.0)))


@pytest.mark.parametrize("hemisphere", ["", "UPPER", "both"])
def test_grid_and_reprojection_reject_unknown_hemispheres(hemisphere: str) -> None:
    with pytest.raises(ValueError, match="upper or lower"):
        stereographic_grid(9, hemisphere)
    with pytest.raises(ValueError, match="upper or lower"):
        reproject_hemisphere(
            indexed_master(9),
            Orientation((0.0, 0.0, 0.0)),
            hemisphere=hemisphere,
            size=9,
            tile_rows=3,
        )


@pytest.mark.parametrize("row_start,row_stop", [(-1, 2), (0, 0), (8, 10), (4, 3)])
def test_grid_rejects_rows_outside_the_requested_output(
    row_start: int, row_stop: int
) -> None:
    with pytest.raises(ValueError, match="outside the output grid"):
        stereographic_grid_rows(9, "upper", row_start, row_stop)


@pytest.mark.parametrize("tile_rows", [0, -1, 10, 1.5, True])
def test_reprojection_rejects_unbounded_or_noninteger_tiles(tile_rows: object) -> None:
    with pytest.raises(ValueError, match="tile_rows"):
        reproject_hemisphere(
            indexed_master(9),
            Orientation((0.0, 0.0, 0.0)),
            hemisphere="upper",
            size=9,
            tile_rows=tile_rows,  # type: ignore[arg-type]
        )

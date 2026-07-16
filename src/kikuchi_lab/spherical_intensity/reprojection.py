"""Fixed specimen-frame stereographic pullback with direct bilinear sampling."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
from orix.projections import InverseStereographicProjection

from kikuchi_lab.model.recipes import Orientation

from .orientation import orientation_matrix


_DISK_TOLERANCE = 32 * np.finfo(np.float64).eps
_DIRECTION_TOLERANCE = 5e-13
_SOURCE_BOUNDARY_TOLERANCE = 5e-12
_HEMISPHERES = {"upper", "lower"}


@dataclass(frozen=True)
class StereographicGrid:
    """One complete or row-tiled stereographic specimen display grid."""

    x: np.ndarray
    y: np.ndarray
    directions: np.ndarray
    valid: np.ndarray


@dataclass(frozen=True)
class ReprojectedHemisphere:
    """One fixed-frame hemisphere and its source-ownership ledger."""

    values: np.ndarray
    valid: np.ndarray
    source_hemisphere: np.ndarray
    ledger: Mapping[str, object]


def _validate_size(size: int) -> None:
    if type(size) is not int or size < 2:
        raise ValueError("stereographic grid size must be an integer of at least 2")


def _validate_hemisphere(hemisphere: str) -> None:
    if hemisphere not in _HEMISPHERES:
        raise ValueError("stereographic hemisphere must be upper or lower")


def _validated_source(source: np.ndarray) -> np.ndarray:
    master = np.asarray(source)
    if (
        master.ndim != 3
        or master.shape[0] != 2
        or master.shape[1] != master.shape[2]
        or master.shape[1] < 2
    ):
        raise ValueError("source channel must have shape (2, N, N) with N at least 2")
    if not np.issubdtype(master.dtype, np.number) or not np.isfinite(master).all():
        raise ValueError("source channel must contain finite numeric values")
    return master


def stereographic_grid(size: int, hemisphere: str) -> StereographicGrid:
    """Construct one complete fixed-frame stereographic hemisphere grid."""
    return stereographic_grid_rows(size, hemisphere, 0, size)


def stereographic_grid_rows(
    size: int,
    hemisphere: str,
    row_start: int,
    row_stop: int,
) -> StereographicGrid:
    """Construct a bounded row tile of a fixed stereographic grid."""
    _validate_size(size)
    _validate_hemisphere(hemisphere)
    if (
        type(row_start) is not int
        or type(row_stop) is not int
        or not 0 <= row_start < row_stop <= size
    ):
        raise ValueError("stereographic row tile is outside the output grid")

    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinate, coordinate[row_start:row_stop])
    valid = x * x + y * y <= 1.0 + _DISK_TOLERANCE
    pole = -1 if hemisphere == "upper" else 1
    directions = np.full((row_stop - row_start, size, 3), np.nan, dtype=np.float64)
    directions[valid] = np.asarray(
        InverseStereographicProjection(pole=pole)
        .xy2vector(x[valid], y[valid])
        .data,
        dtype=np.float64,
    )
    return StereographicGrid(x=x, y=y, directions=directions, valid=valid)


def inverse_rotate_directions(
    specimen_directions: np.ndarray,
    orientation: Orientation,
) -> np.ndarray:
    """Pull unit specimen directions back through ``G_cs^-1`` into crystal space."""
    specimen = np.asarray(specimen_directions, dtype=np.float64)
    if specimen.ndim != 2 or specimen.shape[1] != 3 or not np.isfinite(specimen).all():
        raise ValueError("specimen directions must have shape (M, 3) and be finite")
    if not np.allclose(
        np.linalg.norm(specimen, axis=1),
        1.0,
        rtol=0.0,
        atol=_DIRECTION_TOLERANCE,
    ):
        raise ValueError("specimen directions must be unit vectors within 5e-13")

    crystal = specimen @ orientation_matrix(orientation)
    if not np.isfinite(crystal).all():
        raise ValueError("inverse-oriented crystal directions must be finite")
    if not np.allclose(
        np.linalg.norm(crystal, axis=1),
        1.0,
        rtol=0.0,
        atol=_DIRECTION_TOLERANCE,
    ):
        raise ValueError("inverse-oriented crystal directions must remain unit vectors")
    return crystal


def sample_stereographic_channel(
    source: np.ndarray,
    crystal_directions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Directly bilinear-sample upper/lower stereographic source planes."""
    master = _validated_source(source)
    directions = np.asarray(crystal_directions, dtype=np.float64)
    if (
        directions.ndim != 2
        or directions.shape[1] != 3
        or not np.isfinite(directions).all()
    ):
        raise ValueError("crystal directions must have shape (M, 3) and be finite")
    if not np.allclose(
        np.linalg.norm(directions, axis=1),
        1.0,
        rtol=0.0,
        atol=_DIRECTION_TOLERANCE,
    ):
        raise ValueError("crystal directions must be unit vectors within 5e-13")

    return _sample_validated_stereographic_channel(master, directions)


def _sample_validated_stereographic_channel(
    master: np.ndarray,
    directions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample inputs already validated at the public or tiled boundary."""

    hemisphere_index = np.where(directions[:, 2] >= -_DISK_TOLERANCE, 0, 1)
    pole = np.where(hemisphere_index == 0, -1.0, 1.0)
    denominator = 1.0 - pole * directions[:, 2]
    if np.any(denominator <= 0.0):
        raise ValueError("stereographic projection denominator must be positive")
    x = directions[:, 0] / denominator
    y = directions[:, 1] / denominator
    if (
        np.any(np.abs(x) > 1.0 + _SOURCE_BOUNDARY_TOLERANCE)
        or np.any(np.abs(y) > 1.0 + _SOURCE_BOUNDARY_TOLERANCE)
    ):
        raise ValueError("stereographic source coordinates fall outside the source square")

    size = master.shape[-1]
    column = np.clip((x + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    row = np.clip((y + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    c0 = np.floor(column).astype(np.int64)
    r0 = np.floor(row).astype(np.int64)
    c1 = np.minimum(c0 + 1, size - 1)
    r1 = np.minimum(r0 + 1, size - 1)
    dc = column - c0
    dr = row - r0
    values = (
        (1.0 - dr) * (1.0 - dc) * master[hemisphere_index, r0, c0]
        + (1.0 - dr) * dc * master[hemisphere_index, r0, c1]
        + dr * (1.0 - dc) * master[hemisphere_index, r1, c0]
        + dr * dc * master[hemisphere_index, r1, c1]
    )
    if not np.isfinite(values).all():
        raise ValueError("bilinear stereographic samples must be finite")
    return values, hemisphere_index.astype(np.int8)


def reproject_hemisphere(
    source: np.ndarray,
    orientation: Orientation,
    *,
    hemisphere: str,
    size: int,
    tile_rows: int,
    check_deadline: Callable[[], None] | None = None,
) -> ReprojectedHemisphere:
    """Evaluate ``I_sample(s) = I_crystal(G_cs^-1 s)`` in bounded row tiles."""
    master = _validated_source(source)
    _validate_size(size)
    _validate_hemisphere(hemisphere)
    if type(tile_rows) is not int or not 1 <= tile_rows <= size:
        raise ValueError("tile_rows must be an integer within the output grid")
    if check_deadline is not None and not callable(check_deadline):
        raise ValueError("check_deadline must be callable")

    values = np.zeros((size, size), dtype=np.float32)
    valid = np.zeros((size, size), dtype=bool)
    source_hemisphere = np.zeros((size, size), dtype=np.int8)
    identity_fast_path = (
        orientation.euler_bunge_deg == (0.0, 0.0, 0.0)
        and master.shape[-1] == size
    )

    for row_start in range(0, size, tile_rows):
        if check_deadline is not None:
            check_deadline()
        row_stop = min(row_start + tile_rows, size)
        grid = stereographic_grid_rows(size, hemisphere, row_start, row_stop)
        tile_valid = grid.valid
        valid[row_start:row_stop] = tile_valid
        tile_values = values[row_start:row_stop]
        tile_owners = source_hemisphere[row_start:row_stop]

        if identity_fast_path:
            source_index = 0 if hemisphere == "upper" else 1
            source_tile = master[source_index, row_start:row_stop]
            tile_values[tile_valid] = source_tile[tile_valid]
            tile_owners[tile_valid] = 1 if source_index == 0 else -1
        else:
            specimen = grid.directions[tile_valid]
            pulled = inverse_rotate_directions(specimen, orientation)
            sampled, owner = _sample_validated_stereographic_channel(master, pulled)
            tile_values[tile_valid] = sampled.astype(np.float32)
            tile_owners[tile_valid] = np.where(owner == 0, 1, -1)

    ledger = {
        "projection": "stereographic",
        "display_frame": "EDAX-TSL:RD-TD-ND",
        "hemisphere": hemisphere,
        "interpolation": "bilinear",
        "spatial_filter": "none",
        "equator_owner": "upper",
        "identity_source_grid_fast_path": identity_fast_path,
        "identity_source_plane_equator_exception": (
            "requested_source_plane_including_lower_display_rim"
            if identity_fast_path
            else "not_applicable"
        ),
        "tile_rows": tile_rows,
    }
    return ReprojectedHemisphere(values, valid, source_hemisphere, ledger)

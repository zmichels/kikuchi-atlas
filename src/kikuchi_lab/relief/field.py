"""Project-owned spherical fields from square Lambert master patterns.

The forward and inverse transforms implement the Callahan/EMsoft square
Lambert equal-area mapping used by the pinned kikuchipy 0.13.0 reference.  The
implementation here is independent plain-NumPy code; no private dependency API
crosses the production boundary.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import numpy as np

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.products import MasterPatternProduct

from .recipes import ReliefSourceExpectation

_SQRT_PI_HALF = np.sqrt(np.pi / 2.0)
_SQRT_PI_OVER_2 = np.sqrt(np.pi) / 2.0
_TWO_OVER_SQRT_PI = 2.0 / np.sqrt(np.pi)
_SEAM_TOLERANCE = 1e-6
_EQUATOR_TOLERANCE = 1e-14
_TRANSFORM_CONTRACT = "callahan-emsoft-square-lambert/v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def immutable_float_array(value: object) -> np.ndarray:
    """Return an immutable, owned float64 array."""
    converted = np.array(value, dtype=np.float64, order="C", copy=True)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.float64).reshape(converted.shape)


def _immutable_int_array(value: object) -> np.ndarray:
    converted = np.array(value, dtype=np.int64, order="C", copy=True)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.int64).reshape(converted.shape)


@dataclass(frozen=True)
class SeamDiagnostics:
    equator_owner: str
    boundary_count: int
    maximum_absolute_residual: float
    maximum_normalized_residual: float
    tolerance: float


@dataclass(frozen=True)
class SphericalScalarField:
    field_id: str
    master_product_id: str
    master_array_sha256: str
    projection: str
    coordinate_frame: str
    north_grid: np.ndarray
    south_grid: np.ndarray
    directions: np.ndarray
    raw_values: np.ndarray
    source_hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    seam: SeamDiagnostics


@dataclass(frozen=True)
class DirectionalSamples:
    directions: np.ndarray
    raw_values: np.ndarray
    hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    weights: np.ndarray


def directions_to_lambert_square(directions: object) -> np.ndarray:
    """Map finite nonzero Cartesian directions onto normalized Lambert squares."""
    vectors = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or np.any(norms <= 0):
        raise ValueError("directions must be finite nonzero vectors")
    unit = vectors / norms[:, None]
    result = np.zeros((len(unit), 2), dtype=np.float64)
    for index, (x, y, z) in enumerate(unit):
        root = np.sqrt(2.0 * (1.0 - abs(z)))
        if root == 0.0:
            continue
        if abs(y) <= abs(x):
            sign = np.copysign(1.0, x)
            result[index, 0] = sign * root * _SQRT_PI_OVER_2
            result[index, 1] = sign * root * _TWO_OVER_SQRT_PI * np.arctan(y / x)
        else:
            sign = np.copysign(1.0, y)
            result[index, 0] = sign * root * _TWO_OVER_SQRT_PI * np.arctan(x / y)
            result[index, 1] = sign * root * _SQRT_PI_OVER_2
    return immutable_float_array(result / _SQRT_PI_HALF)


def lambert_square_to_directions(x: object, y: object, hemisphere: int) -> np.ndarray:
    """Map normalized Lambert-square coordinates onto one unit hemisphere."""
    if hemisphere not in (-1, 1):
        raise ValueError("hemisphere must be +1 north or -1 south")
    x_array, y_array = np.broadcast_arrays(
        np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    )
    if not np.isfinite(x_array).all() or not np.isfinite(y_array).all():
        raise ValueError("Lambert coordinates must be finite")
    if np.any(np.abs(x_array) > 1.0) or np.any(np.abs(y_array) > 1.0):
        raise ValueError("Lambert coordinates must lie in [-1, 1]")
    xi = x_array.ravel() * _SQRT_PI_HALF
    yi = y_array.ravel() * _SQRT_PI_HALF
    cart = np.zeros((len(xi), 3), dtype=np.float64)
    for index, (left, up) in enumerate(zip(xi, yi, strict=True)):
        if max(abs(left), abs(up)) == 0.0:
            cart[index] = (0.0, 0.0, float(hemisphere))
        elif abs(left) <= abs(up):
            q = 2.0 * up * np.sqrt(np.pi - up * up) / np.pi
            angle = left * np.pi * 0.25 / up
            cart[index] = (
                q * np.sin(angle),
                q * np.cos(angle),
                hemisphere * (1.0 - 2.0 * up * up / np.pi),
            )
        else:
            q = 2.0 * left * np.sqrt(np.pi - left * left) / np.pi
            angle = up * np.pi * 0.25 / left
            cart[index] = (
                q * np.cos(angle),
                q * np.sin(angle),
                hemisphere * (1.0 - 2.0 * left * left / np.pi),
            )
    cart /= np.linalg.norm(cart, axis=1, keepdims=True)
    return immutable_float_array(cart)


def _validate_master(
    master: MasterPatternProduct, expected: ReliefSourceExpectation
) -> tuple[np.ndarray, dict[str, object]]:
    if not isinstance(master, MasterPatternProduct):
        raise TypeError("master must be a MasterPatternProduct")
    if not isinstance(expected, ReliefSourceExpectation):
        raise TypeError("expected must be a ReliefSourceExpectation")
    if master.product_id != expected.product_id:
        raise ValueError("master product ID disagrees with source expectation")
    if master.array_sha256 != expected.array_sha256:
        raise ValueError("master array SHA-256 disagrees with source expectation")
    if not isinstance(expected.file_sha256, str) or not _SHA256.fullmatch(expected.file_sha256):
        raise ValueError("source file SHA-256 expectation is required")

    intensity = np.asarray(master.intensity)
    if (
        intensity.ndim != 3
        or intensity.shape[0] != 2
        or intensity.shape[1] != intensity.shape[2]
        or intensity.shape[1] < 3
        or intensity.shape[1] % 2 != 1
    ):
        raise ValueError("master intensity must have shape (2, N, N) for odd N >= 3")
    metadata = master.metadata_dict()
    if metadata.get("projection") != "Lambert square equal-area":
        raise ValueError("master projection must be Lambert square equal-area")
    if metadata.get("hemisphere_order") != ["north", "south"]:
        raise ValueError("master hemisphere order must be north then south")
    coordinate_frame = metadata.get("coordinate_frame")
    if not isinstance(coordinate_frame, str) or not coordinate_frame:
        raise ValueError("master coordinate frame is required")
    return intensity, metadata


def build_spherical_scalar_field(
    master: MasterPatternProduct, expected: ReliefSourceExpectation
) -> SphericalScalarField:
    """Build one deterministic spherical field, with north owning the equator."""
    intensity, metadata = _validate_master(master, expected)
    north_grid = immutable_float_array(intensity[0])
    south_grid = immutable_float_array(intensity[1])
    size = north_grid.shape[0]

    boundary = np.zeros((size, size), dtype=bool)
    boundary[[0, -1], :] = True
    boundary[:, [0, -1]] = True
    boundary_count = int(np.count_nonzero(boundary))
    absolute_residual = np.abs(north_grid[boundary] - south_grid[boundary])
    maximum_absolute_residual = float(np.max(absolute_residual))
    canonical_values = np.concatenate((north_grid.ravel(), south_grid[~boundary]))
    scale = max(float(np.ptp(canonical_values)), float(np.finfo(np.float64).eps))
    maximum_normalized_residual = maximum_absolute_residual / scale
    if maximum_normalized_residual > _SEAM_TOLERANCE:
        raise ValueError(
            "equator seam residual exceeds tolerance: "
            f"{maximum_normalized_residual:.17g} > {_SEAM_TOLERANCE:.17g}"
        )
    seam = SeamDiagnostics(
        equator_owner="north",
        boundary_count=boundary_count,
        maximum_absolute_residual=maximum_absolute_residual,
        maximum_normalized_residual=maximum_normalized_residual,
        tolerance=_SEAM_TOLERANCE,
    )

    grid = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(grid, grid)
    north_directions = lambert_square_to_directions(x.ravel(), y.ravel(), hemisphere=1)
    south_directions = lambert_square_to_directions(x[~boundary], y[~boundary], hemisphere=-1)
    directions = immutable_float_array(np.concatenate((north_directions, south_directions), axis=0))
    raw_values = immutable_float_array(canonical_values)

    rows, columns = np.indices((size, size))
    source_rows = _immutable_int_array(np.concatenate((rows.ravel(), rows[~boundary])))
    source_columns = _immutable_int_array(np.concatenate((columns.ravel(), columns[~boundary])))
    source_hemisphere = _immutable_int_array(
        np.concatenate(
            (
                np.ones(size * size, dtype=np.int64),
                -np.ones(np.count_nonzero(~boundary), dtype=np.int64),
            )
        )
    )
    identity = {
        "master": {
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "file_sha256": expected.file_sha256,
        },
        "projection": metadata["projection"],
        "coordinate_frame": metadata["coordinate_frame"],
        "transform_contract": _TRANSFORM_CONTRACT,
        "seam": asdict(seam),
    }
    return SphericalScalarField(
        field_id=stable_id("spherical-field", identity),
        master_product_id=master.product_id,
        master_array_sha256=master.array_sha256,
        projection=str(metadata["projection"]),
        coordinate_frame=str(metadata["coordinate_frame"]),
        north_grid=north_grid,
        south_grid=south_grid,
        directions=directions,
        raw_values=raw_values,
        source_hemisphere=source_hemisphere,
        source_rows=source_rows,
        source_columns=source_columns,
        seam=seam,
    )


def interpolate_sample_ledger(
    north_grid: np.ndarray,
    south_grid: np.ndarray,
    samples: DirectionalSamples,
) -> np.ndarray:
    """Evaluate the deterministic bilinear ledger against aligned grids."""
    north = np.asarray(north_grid, dtype=np.float64)
    south = np.asarray(south_grid, dtype=np.float64)
    if north.shape != south.shape or north.ndim != 2 or north.shape[0] != north.shape[1]:
        raise ValueError("sample grids must be aligned square arrays")
    if not np.isfinite(north).all() or not np.isfinite(south).all():
        raise ValueError("sample grids must contain only finite values")
    count = len(samples.directions)
    if samples.source_rows.shape != (count, 2):
        raise ValueError("sample row ledger must have shape (N, 2)")
    if samples.source_columns.shape != (count, 2):
        raise ValueError("sample column ledger must have shape (N, 2)")
    if samples.weights.shape != (count, 4):
        raise ValueError("sample weight ledger must have shape (N, 4)")
    if not np.isin(samples.hemisphere, (-1, 1)).all():
        raise ValueError("sample hemisphere ledger must contain only -1 and +1")
    row0, row1 = samples.source_rows.T
    col0, col1 = samples.source_columns.T
    if (
        np.any(samples.source_rows < 0)
        or np.any(samples.source_rows >= north.shape[0])
        or np.any(samples.source_columns < 0)
        or np.any(samples.source_columns >= north.shape[1])
    ):
        raise ValueError("sample ledger indices exceed grid bounds")
    corners = np.empty((count, 4), dtype=np.float64)
    for owner, grid in ((1, north), (-1, south)):
        owned = np.flatnonzero(samples.hemisphere == owner)
        corners[owned, 0] = grid[row0[owned], col0[owned]]
        corners[owned, 1] = grid[row1[owned], col0[owned]]
        corners[owned, 2] = grid[row0[owned], col1[owned]]
        corners[owned, 3] = grid[row1[owned], col1[owned]]
    return immutable_float_array(np.einsum("ij,ij->i", corners, samples.weights))


def sample_spherical_field(field: SphericalScalarField, directions: object) -> DirectionalSamples:
    """Sample a spherical field and retain its complete bilinear ledger."""
    vectors = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or np.any(norms <= 0):
        raise ValueError("directions must be finite nonzero vectors")
    unit = vectors / norms[:, None]
    hemisphere = np.where(unit[:, 2] >= -_EQUATOR_TOLERANCE, 1, -1)
    coordinates = directions_to_lambert_square(unit)
    size = field.north_grid.shape[0]
    pixels = np.clip((coordinates + 1.0) * (size - 1) / 2.0, 0.0, size - 1)
    column_pixel, row_pixel = pixels.T
    row0 = np.floor(row_pixel).astype(np.int64)
    row1 = np.minimum(row0 + 1, size - 1)
    col0 = np.floor(column_pixel).astype(np.int64)
    col1 = np.minimum(col0 + 1, size - 1)
    row_fraction = row_pixel - row0
    column_fraction = column_pixel - col0
    weights = np.column_stack(
        (
            (1.0 - row_fraction) * (1.0 - column_fraction),
            row_fraction * (1.0 - column_fraction),
            (1.0 - row_fraction) * column_fraction,
            row_fraction * column_fraction,
        )
    )
    sample_rows = _immutable_int_array(np.column_stack((row0, row1)))
    sample_columns = _immutable_int_array(np.column_stack((col0, col1)))
    immutable_weights = immutable_float_array(weights)
    immutable_directions = immutable_float_array(unit)
    immutable_hemisphere = _immutable_int_array(hemisphere)
    ledger = DirectionalSamples(
        directions=immutable_directions,
        raw_values=immutable_float_array(np.zeros(len(unit))),
        hemisphere=immutable_hemisphere,
        source_rows=sample_rows,
        source_columns=sample_columns,
        weights=immutable_weights,
    )
    raw_values = interpolate_sample_ledger(field.north_grid, field.south_grid, ledger)

    equator = np.flatnonzero(np.abs(unit[:, 2]) <= _EQUATOR_TOLERANCE)
    if len(equator):
        south_hemisphere = np.array(hemisphere, copy=True)
        south_hemisphere[equator] = -1
        south_ledger = DirectionalSamples(
            directions=immutable_directions,
            raw_values=raw_values,
            hemisphere=_immutable_int_array(south_hemisphere),
            source_rows=sample_rows,
            source_columns=sample_columns,
            weights=immutable_weights,
        )
        south_values = interpolate_sample_ledger(field.north_grid, field.south_grid, south_ledger)
        scale = max(
            float(np.ptp(field.raw_values)),
            float(np.finfo(np.float64).eps),
        )
        residual = np.abs(raw_values[equator] - south_values[equator]) / scale
        if np.any(residual > field.seam.tolerance):
            raise ValueError("equator seam residual exceeds field tolerance")

    return DirectionalSamples(
        directions=immutable_directions,
        raw_values=raw_values,
        hemisphere=immutable_hemisphere,
        source_rows=sample_rows,
        source_columns=sample_columns,
        weights=immutable_weights,
    )

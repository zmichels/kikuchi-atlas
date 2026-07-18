"""Stereographic-master intensity fields for the separate Ice globe product."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.kinematical.contracts import KinematicalSimulation


STEREOGRAPHIC_SAMPLING_CONTRACT = "inverse-stereographic-disk/bilinear/upper-owns-equator/v1"


class _OwnedArray(np.ndarray):
    """Compatibility wrapper for NumPy 2's removed ndarray.ptp method."""

    def ptp(self, *args: object, **kwargs: object) -> np.generic:
        return np.ptp(np.asarray(self), *args, **kwargs)


def _frozen(value: object, *, dtype: np.dtype) -> np.ndarray:
    array = np.array(value, dtype=dtype, order="C", copy=True).view(_OwnedArray)
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class StereographicSeamDiagnostics:
    equator_owner: str
    boundary_count: int
    maximum_absolute_residual: float
    maximum_normalized_residual: float
    tolerance: float


@dataclass(frozen=True)
class IceIntensityField:
    """Owned source grids and their exact stereographic directional meaning."""

    field_id: str
    source_kind: str
    master_product_id: str
    master_array_sha256: str
    raw_values: np.ndarray
    upper_grid: np.ndarray
    lower_grid: np.ndarray
    seam: StereographicSeamDiagnostics


def build_ice_intensity_field(simulation: KinematicalSimulation) -> IceIntensityField:
    """Retain the Ice kinematical stereographic master without Lambert relabelling."""
    if not isinstance(simulation, KinematicalSimulation):
        raise TypeError("simulation must be a KinematicalSimulation")
    master = simulation.master_stereographic
    metadata = master.metadata
    if metadata.get("projection") != "stereographic" or metadata.get("hemisphere") != "both":
        raise ValueError("Ice intensity globe requires a both-hemisphere stereographic master")
    source = np.asarray(master.intensity, dtype=np.float64)
    if source.ndim != 3 or source.shape[0] != 2 or source.shape[1] != source.shape[2]:
        raise ValueError("stereographic master must have shape (2, N, N)")
    upper, lower = source
    boundary = np.zeros(upper.shape, dtype=bool)
    boundary[[0, -1], :] = True
    boundary[:, [0, -1]] = True
    canonical = np.concatenate((upper.ravel(), lower[~boundary]))
    residual = np.abs(upper[boundary] - lower[boundary])
    scale = max(float(np.ptp(canonical)), float(np.finfo(np.float64).eps))
    seam = StereographicSeamDiagnostics(
        equator_owner="upper",
        boundary_count=int(np.count_nonzero(boundary)),
        maximum_absolute_residual=float(residual.max(initial=0.0)),
        maximum_normalized_residual=float(residual.max(initial=0.0) / scale),
        tolerance=1e-6,
    )
    if seam.maximum_normalized_residual > seam.tolerance:
        raise ValueError("stereographic equator seam residual exceeds tolerance")
    identity = {
        "source_kind": "kinematical_stereographic_master",
        "master_product_id": master.product_id,
        "master_array_sha256": master.array_sha256,
        "source_array_shape": list(source.shape),
        "sampling_contract": STEREOGRAPHIC_SAMPLING_CONTRACT,
        "seam": asdict(seam),
    }
    return IceIntensityField(
        field_id=stable_id("ice-intensity-field", identity),
        source_kind="kinematical_stereographic_master",
        master_product_id=master.product_id,
        master_array_sha256=master.array_sha256,
        raw_values=_frozen(canonical, dtype=np.float64),
        upper_grid=_frozen(upper, dtype=np.float64),
        lower_grid=_frozen(lower, dtype=np.float64),
        seam=seam,
    )


def sample_stereographic_grid(field: IceIntensityField, directions: object, *, upper_grid: np.ndarray, lower_grid: np.ndarray) -> np.ndarray:
    """Bilinearly sample a mapped or raw stereographic master at unit directions."""
    if not isinstance(field, IceIntensityField):
        raise TypeError("field must be an IceIntensityField")
    vectors = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or np.any(norms <= 0.0):
        raise ValueError("directions must be finite nonzero vectors")
    if upper_grid.shape != lower_grid.shape or upper_grid.ndim != 2 or upper_grid.shape[0] != upper_grid.shape[1]:
        raise ValueError("stereographic grids must be aligned squares")
    unit = vectors / norms[:, None]
    # The public master uses a unit stereographic disk: q=(x,y) maps to
    # (2x,2y,+/- (1-|q|^2))/(1+|q|^2).  z==0 belongs to upper.
    q = unit[:, :2] / (1.0 + np.abs(unit[:, 2, None]))
    coordinates = np.clip((q + 1.0) * (upper_grid.shape[0] - 1) / 2.0, 0.0, upper_grid.shape[0] - 1)
    col, row = coordinates.T
    r0, c0 = np.floor(row).astype(int), np.floor(col).astype(int)
    r1, c1 = np.minimum(r0 + 1, upper_grid.shape[0] - 1), np.minimum(c0 + 1, upper_grid.shape[1] - 1)
    dr, dc = row - r0, col - c0
    # Selecting each corner individually keeps z==0 with the upper grid without
    # materialising a separate grid for every requested direction.
    upper_owner = unit[:, 2] >= 0.0
    def corner(rows: np.ndarray, columns: np.ndarray) -> np.ndarray:
        return np.where(upper_owner, upper_grid[rows, columns], lower_grid[rows, columns])
    values = (
        (1.0 - dr) * (1.0 - dc) * corner(r0, c0)
        + dr * (1.0 - dc) * corner(r1, c0)
        + (1.0 - dr) * dc * corner(r0, c1)
        + dr * dc * corner(r1, c1)
    )
    return _frozen(values, dtype=np.float64)


__all__ = ["IceIntensityField", "StereographicSeamDiagnostics", "STEREOGRAPHIC_SAMPLING_CONTRACT", "build_ice_intensity_field", "sample_stereographic_grid"]

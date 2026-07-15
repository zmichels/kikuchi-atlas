"""Exact axial Kikuchi-band overlap on an upper stereographic grid."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from orix.projections import InverseStereographicProjection


_DISK_EPSILON_MULTIPLIER = 32
_AXIAL_TOLERANCE = 1e-8


def _owned(array: object, dtype: np.dtype) -> np.ndarray:
    value = np.ascontiguousarray(np.asarray(array, dtype=dtype))
    owned = np.frombuffer(value.tobytes(order="C"), dtype=dtype).reshape(value.shape)
    return owned


@dataclass(frozen=True)
class AxialBandSet:
    """One representative for every signed `hkl`/`-h-k-l` pair."""

    hkl: np.ndarray
    normals: np.ndarray
    theta_radian: np.ndarray
    structure_factor_abs: np.ndarray

    def __post_init__(self) -> None:
        arrays = {
            "hkl": _owned(self.hkl, np.dtype("<i4")),
            "normals": _owned(self.normals, np.dtype("<f8")),
            "theta_radian": _owned(self.theta_radian, np.dtype("<f8")),
            "structure_factor_abs": _owned(
                self.structure_factor_abs, np.dtype("<f8")
            ),
        }
        count = arrays["hkl"].shape[0]
        if arrays["hkl"].shape != (count, 3) or arrays["normals"].shape != (count, 3):
            raise ValueError("axial hkl and normals must have shape (N, 3)")
        if arrays["theta_radian"].shape != (count,) or arrays[
            "structure_factor_abs"
        ].shape != (count,):
            raise ValueError("axial scalar channels must have shape (N,)")
        for name, value in arrays.items():
            if not np.isfinite(value).all():
                raise ValueError(f"axial {name} must be finite")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class OverlapField:
    """Additional multi-band overlap and its presentation normalization."""

    raw: np.ndarray
    normalized: np.ndarray
    valid_disk: np.ndarray
    normalization_value: float
    axial_band_count: int
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        raw = _owned(self.raw, np.dtype("<f4"))
        normalized = _owned(self.normalized, np.dtype("<f4"))
        valid = _owned(self.valid_disk, np.dtype("bool"))
        if raw.ndim != 2 or raw.shape != normalized.shape or raw.shape != valid.shape:
            raise ValueError("overlap channels must be equally shaped two-dimensional arrays")
        if not np.isfinite(raw).all() or not np.isfinite(normalized).all():
            raise ValueError("overlap channels must be finite")
        if not float(self.normalization_value) > 0:
            raise ValueError("overlap normalization value must be positive")
        if type(self.axial_band_count) is not int or self.axial_band_count <= 0:
            raise ValueError("overlap axial band count must be a positive integer")
        object.__setattr__(self, "raw", raw)
        object.__setattr__(self, "normalized", normalized)
        object.__setattr__(self, "valid_disk", valid)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def _canonical_hkl(hkl: np.ndarray) -> tuple[tuple[int, int, int], int]:
    rounded = np.rint(hkl).astype(np.int64)
    if not np.allclose(hkl, rounded, rtol=0, atol=_AXIAL_TOLERANCE):
        raise ValueError("reflector hkl values must be integer-valued")
    if not np.any(rounded):
        raise ValueError("zero reciprocal-lattice vector is not a reflector")
    first = int(rounded[np.flatnonzero(rounded)[0]])
    sign = 1 if first > 0 else -1
    canonical = tuple(int(value) for value in sign * rounded)
    return canonical, sign


def collapse_antipodal_reflectors(reflectors: object) -> AxialBandSet:
    """Collapse only exact signed Miller-index pairs, preserving harmonic orders."""
    hkl = np.asarray(getattr(reflectors, "hkl"), dtype=np.float64)
    normals = np.asarray(getattr(getattr(reflectors, "unit"), "data"), dtype=np.float64)
    theta = np.asarray(getattr(reflectors, "theta"), dtype=np.float64)
    strengths = np.abs(np.asarray(getattr(reflectors, "structure_factor")))
    count = hkl.shape[0]
    if hkl.shape != (count, 3) or normals.shape != (count, 3):
        raise ValueError("reflector hkl and unit normals must have shape (N, 3)")
    if theta.shape != (count,) or strengths.shape != (count,):
        raise ValueError("reflector theta and structure factor must have shape (N,)")
    if count == 0 or not all(
        np.isfinite(value).all() for value in (hkl, normals, theta, strengths)
    ):
        raise ValueError("reflectors must be finite and non-empty")

    groups: dict[tuple[int, int, int], list[tuple[np.ndarray, np.ndarray, float, float]]] = {}
    for indices, normal, angle, strength in zip(
        hkl, normals, theta, strengths, strict=True
    ):
        key, sign = _canonical_hkl(indices)
        groups.setdefault(key, []).append(
            (np.rint(indices).astype(np.int64), sign * normal, float(angle), float(strength))
        )

    output_hkl: list[tuple[int, int, int]] = []
    output_normals: list[np.ndarray] = []
    output_theta: list[float] = []
    output_strengths: list[float] = []
    for key in sorted(groups):
        pair = groups[key]
        signed_indices = {tuple(int(value) for value in item[0]) for item in pair}
        negative_key = tuple(-value for value in key)
        if signed_indices != {key, negative_key}:
            raise ValueError(f"axial reflector {key} does not include both signed indices")
        signed_counts = {
            indices: sum(tuple(int(value) for value in item[0]) == indices for item in pair)
            for indices in signed_indices
        }
        if signed_counts[key] != signed_counts[negative_key]:
            raise ValueError(f"axial reflector {key} has unbalanced signed duplicates")
        pair_normals = np.stack([item[1] for item in pair])
        pair_theta = np.array([item[2] for item in pair])
        pair_strength = np.array([item[3] for item in pair])
        if not np.allclose(pair_normals, pair_normals[0], rtol=0, atol=1e-9):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal normals")
        if not np.allclose(pair_theta, pair_theta[0], rtol=1e-9, atol=1e-11):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal angles")
        if not np.allclose(pair_strength, pair_strength[0], rtol=1e-9, atol=1e-10):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal strengths")
        normal = np.mean(pair_normals, axis=0)
        normal /= np.linalg.norm(normal)
        output_hkl.append(key)
        output_normals.append(normal)
        output_theta.append(float(np.mean(pair_theta)))
        output_strengths.append(float(np.mean(pair_strength)))

    return AxialBandSet(
        hkl=np.asarray(output_hkl, dtype=np.int32),
        normals=np.asarray(output_normals, dtype=np.float64),
        theta_radian=np.asarray(output_theta, dtype=np.float64),
        structure_factor_abs=np.asarray(output_strengths, dtype=np.float64),
    )


def accumulate_additional_overlap(
    *,
    directions: object,
    normals: object,
    half_width_sines: object,
    weights: object,
) -> np.ndarray:
    """Accumulate `sum(weight) - max(weight)` without a pixel-band cube."""
    xyz = np.asarray(directions, dtype=np.float64)
    plane_normals = np.asarray(normals, dtype=np.float64)
    widths = np.asarray(half_width_sines, dtype=np.float64)
    band_weights = np.asarray(weights, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1:] != (3,):
        raise ValueError("directions must have shape (N, 3)")
    if plane_normals.ndim != 2 or plane_normals.shape[1:] != (3,):
        raise ValueError("normals must have shape (M, 3)")
    count = plane_normals.shape[0]
    if widths.shape != (count,) or band_weights.shape != (count,):
        raise ValueError("band scalar channels must have shape (M,)")
    if not all(
        np.isfinite(value).all()
        for value in (xyz, plane_normals, widths, band_weights)
    ):
        raise ValueError("band-overlap inputs must be finite")
    if np.any(widths < 0) or np.any(widths > 1) or np.any(band_weights < 0):
        raise ValueError("band widths and weights are outside supported ranges")

    total = np.zeros(xyz.shape[0], dtype=np.float64)
    maximum = np.zeros(xyz.shape[0], dtype=np.float64)
    for normal, half_width_sine, weight in zip(
        plane_normals, widths, band_weights, strict=True
    ):
        inside = np.abs(xyz @ normal) <= half_width_sine
        total[inside] += weight
        maximum[inside] = np.maximum(maximum[inside], weight)
    return np.maximum(total - maximum, 0.0)


def compute_overlap_field(
    reflectors: object,
    *,
    size: int,
    relative_factor: float,
    weight_exponent: float,
    normalization_percentile: float,
) -> OverlapField:
    """Evaluate exact additional axial overlap on one upper stereographic grid."""
    if type(size) is not int or size < 3:
        raise ValueError("overlap grid size must be an integer of at least 3")
    if not 0 < relative_factor <= 1:
        raise ValueError("overlap relative factor must be in (0, 1]")
    if not weight_exponent > 0:
        raise ValueError("overlap weight exponent must be positive")
    if not 0 < normalization_percentile <= 100:
        raise ValueError("overlap normalization percentile must be in (0, 100]")

    strengths = np.abs(np.asarray(getattr(reflectors, "structure_factor")))
    if strengths.ndim != 1 or not strengths.size or not np.isfinite(strengths).all():
        raise ValueError("reflector strengths must be finite and non-empty")
    selected = reflectors[strengths >= relative_factor * float(strengths.max())]
    axial = collapse_antipodal_reflectors(selected)
    weights = (axial.structure_factor_abs / float(strengths.max())) ** weight_exponent

    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    tolerance = _DISK_EPSILON_MULTIPLIER * np.finfo(np.float64).eps
    valid = x_grid * x_grid + y_grid * y_grid <= 1.0 + tolerance
    directions = np.asarray(
        InverseStereographicProjection(pole=-1)
        .xy2vector(x_grid[valid], y_grid[valid])
        .data,
        dtype=np.float64,
    )
    raw_valid = accumulate_additional_overlap(
        directions=directions,
        normals=axial.normals,
        half_width_sines=np.sin(axial.theta_radian),
        weights=weights,
    )
    if not np.any(raw_valid > 0):
        raise ValueError("overlap field has no positive additional-overlap samples")
    normalization = float(np.percentile(raw_valid, normalization_percentile))
    if not np.isfinite(normalization) or normalization <= 0:
        raise ValueError("overlap normalization percentile has zero width")

    raw = np.zeros((size, size), dtype=np.float32)
    normalized = np.zeros((size, size), dtype=np.float32)
    raw[valid] = raw_valid.astype(np.float32)
    normalized[valid] = np.clip(raw_valid / normalization, 0.0, 1.0).astype(
        np.float32
    )
    metadata = {
        "schema_version": 1,
        "projection": "upper stereographic square grid",
        "grid_size": size,
        "grid_formula": "coordinate[k] = -1 + 2*k/(N-1)",
        "valid_domain": "X^2 + Y^2 <= 1 + 32*eps(float64)",
        "axial_collapse_rule": "collapse exact hkl/-h-k-l pairs; preserve orders",
        "membership_equation": "abs(dot(direction, normal)) <= sin(theta_B)",
        "weight_equation": "(abs(F_hkl)/max(abs(F)))^weight_exponent",
        "additional_overlap_equation": "max(sum_weight - max_weight, 0)",
        "relative_factor": float(relative_factor),
        "weight_exponent": float(weight_exponent),
        "normalization_percentile": float(normalization_percentile),
        "normalization_value": normalization,
        "signed_reflector_count": int(selected.size),
        "axial_band_count": int(axial.hkl.shape[0]),
    }
    return OverlapField(
        raw=raw,
        normalized=normalized,
        valid_disk=valid,
        normalization_value=normalization,
        axial_band_count=int(axial.hkl.shape[0]),
        metadata=metadata,
    )


def apply_optical_depth(
    base: object,
    overlap: object,
    *,
    gain: float,
    luminance_ceiling: float,
) -> np.ndarray:
    """Multiply remaining darkness pointwise, preserving exact zero-overlap pixels."""
    values = np.asarray(base, dtype=np.float64)
    depth = np.asarray(overlap, dtype=np.float64)
    if values.shape != depth.shape:
        raise ValueError("base luminance and overlap must have the same shape")
    if not np.isfinite(values).all() or not np.isfinite(depth).all():
        raise ValueError("optical-depth inputs must be finite")
    if not 0 < luminance_ceiling < 1 or not gain >= 0:
        raise ValueError("optical-depth parameters are outside supported ranges")
    if np.any(values < 0) or np.any(values >= luminance_ceiling):
        raise ValueError("base luminance exceeds luminance ceiling")
    if np.any(depth < 0) or np.any(depth > 1):
        raise ValueError("normalized overlap must be in [0, 1]")

    tau_base = -np.log1p(-values / luminance_ceiling)
    result = luminance_ceiling * (
        1.0 - np.exp(-(tau_base + float(gain) * depth))
    )
    result[depth == 0] = values[depth == 0]
    if not np.isfinite(result).all():
        raise ValueError("optical-depth output must be finite")
    return np.asarray(result, dtype=np.float32)


__all__ = [
    "AxialBandSet",
    "OverlapField",
    "accumulate_additional_overlap",
    "apply_optical_depth",
    "collapse_antipodal_reflectors",
    "compute_overlap_field",
]

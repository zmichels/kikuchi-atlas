"""Global intensity mapping, angular filtering, and radial relief geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from kikuchi_lab.globe_mesh import GlobeGeometrySpec, ReliefGeometry, build_radial_geometry

from .field import (
    SphericalScalarField,
    immutable_float_array,
    interpolate_sample_ledger,
    sample_spherical_field,
)
from .recipes import ReliefMappingSpec, SphericalFilterSpec
from .topology import IcosphereTopology

_UNIT_TOLERANCE = 2e-12


def _immutable_int_array(value: object, *, width: int | None = None) -> np.ndarray:
    converted = np.array(value, dtype=np.int64, order="C", copy=True)
    if width is not None:
        converted = converted.reshape(-1, width)
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.int64).reshape(converted.shape)


def _immutable_float_matrix(value: object, *, width: int) -> np.ndarray:
    return immutable_float_array(np.asarray(value, dtype=np.float64).reshape(-1, width))


def _positive_finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{field} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{field} must be a positive finite number")
    return number


@dataclass(frozen=True)
class MappedSphericalField:
    source: SphericalScalarField
    lower_percentile: float
    upper_percentile: float
    lower_value: float
    upper_value: float
    gamma: float
    north_grid: np.ndarray
    south_grid: np.ndarray


@dataclass(frozen=True)
class MappedDirectionalSamples:
    directions: np.ndarray
    raw_values: np.ndarray
    mapped_values: np.ndarray
    hemisphere: np.ndarray
    source_rows: np.ndarray
    source_columns: np.ndarray
    weights: np.ndarray


@dataclass(frozen=True)
class SphericalFilterDiagnostics:
    fwhm_mm: float
    fwhm_rad: float
    sigma_rad: float
    cutoff_sigma: float
    cutoff_chord: float
    minimum_neighbor_count: int
    maximum_neighbor_count: int
    constant_residual: float


def map_source_field(field: SphericalScalarField, spec: ReliefMappingSpec) -> MappedSphericalField:
    """Map one raw two-hemisphere field using a single global percentile range."""
    if not isinstance(field, SphericalScalarField):
        raise TypeError("field must be a SphericalScalarField")
    if not isinstance(spec, ReliefMappingSpec):
        raise TypeError("spec must be a ReliefMappingSpec")
    lower, upper = spec.percentiles
    if (
        isinstance(lower, bool)
        or isinstance(upper, bool)
        or not np.isfinite((lower, upper)).all()
        or not 0.0 <= lower < upper <= 100.0
    ):
        raise ValueError("percentile bounds must satisfy 0 <= lower < upper <= 100")
    gamma = _positive_finite_number(spec.gamma, field="gamma")
    if spec.direction != "bright_outward":
        raise ValueError("mapping direction must be bright_outward")

    lower_value, upper_value = np.percentile(field.raw_values, (lower, upper))
    if not np.isfinite((lower_value, upper_value)).all() or upper_value <= lower_value:
        raise ValueError("source percentile range must be finite and non-collapsed")

    def mapped(grid: np.ndarray) -> np.ndarray:
        unit = np.clip((grid - lower_value) / (upper_value - lower_value), 0.0, 1.0)
        return immutable_float_array(unit**gamma)

    return MappedSphericalField(
        source=field,
        lower_percentile=float(lower),
        upper_percentile=float(upper),
        lower_value=float(lower_value),
        upper_value=float(upper_value),
        gamma=gamma,
        north_grid=mapped(field.north_grid),
        south_grid=mapped(field.south_grid),
    )


def sample_mapped_field(
    mapped: MappedSphericalField, topology: IcosphereTopology
) -> MappedDirectionalSamples:
    """Sample raw and already-mapped grids through one exact interpolation ledger."""
    if not isinstance(mapped, MappedSphericalField):
        raise TypeError("mapped must be a MappedSphericalField")
    if not isinstance(topology, IcosphereTopology):
        raise TypeError("topology must be an IcosphereTopology")
    raw = sample_spherical_field(mapped.source, topology.directions)
    mapped_values = interpolate_sample_ledger(mapped.north_grid, mapped.south_grid, raw)
    return MappedDirectionalSamples(
        directions=raw.directions,
        raw_values=raw.raw_values,
        mapped_values=immutable_float_array(mapped_values),
        hemisphere=raw.hemisphere,
        source_rows=raw.source_rows,
        source_columns=raw.source_columns,
        weights=raw.weights,
    )


def _validated_unit_directions(directions: object) -> np.ndarray:
    try:
        vectors = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    except (TypeError, ValueError) as error:
        raise ValueError("filter directions must be finite unit vectors") from error
    norms = np.linalg.norm(vectors, axis=1)
    if (
        not np.isfinite(vectors).all()
        or not np.isfinite(norms).all()
        or np.any(np.abs(norms - 1.0) > _UNIT_TOLERANCE)
    ):
        raise ValueError("filter directions must be finite unit vectors")
    return np.array(vectors, dtype=np.float64, order="C", copy=True)


def _filter_from_neighborhoods(
    values: np.ndarray,
    unit: np.ndarray,
    neighborhoods: list[list[int]],
    sigma_rad: float,
) -> tuple[np.ndarray, np.ndarray]:
    filtered = np.empty_like(values)
    counts = np.empty(len(unit), dtype=np.int64)
    for index, neighbors in enumerate(neighborhoods):
        ordered = np.asarray(sorted(neighbors), dtype=np.int64)
        cosine = np.clip(unit[ordered] @ unit[index], -1.0, 1.0)
        angles = np.arccos(cosine)
        weights = np.exp(-0.5 * (angles / sigma_rad) ** 2)
        filtered[index] = np.dot(weights, values[ordered]) / weights.sum()
        counts[index] = len(ordered)
    return filtered, counts


def _constant_filter_residual(
    unit: np.ndarray,
    neighborhoods: list[list[int]],
    sigma_rad: float,
) -> float:
    probe = np.ones(len(unit), dtype=np.float64)
    filtered, _ = _filter_from_neighborhoods(probe, unit, neighborhoods, sigma_rad)
    return float(np.max(np.abs(filtered - probe), initial=0.0))


def filter_spherical_values(
    values: object,
    directions: object,
    base_radius_mm: float,
    spec: SphericalFilterSpec,
) -> tuple[np.ndarray, SphericalFilterDiagnostics]:
    """Apply a deterministic Gaussian kernel over angular cKDTree neighborhoods."""
    radius = _positive_finite_number(base_radius_mm, field="base radius")
    if not isinstance(spec, SphericalFilterSpec):
        raise TypeError("spec must be a SphericalFilterSpec")
    if spec.kind != "spherical_gaussian":
        raise ValueError("filter kind must be spherical_gaussian")
    try:
        fwhm_mm = _positive_finite_number(spec.fwhm_mm, field="filter FWHM")
        cutoff_sigma = _positive_finite_number(spec.cutoff_sigma, field="filter cutoff")
    except ValueError as error:
        raise ValueError(f"filter specification is invalid: {error}") from error
    try:
        value_array = np.asarray(values, dtype=np.float64).reshape(-1)
    except (TypeError, ValueError) as error:
        raise ValueError("filter values and directions must be finite and aligned") from error
    unit = _validated_unit_directions(directions)
    if len(value_array) != len(unit) or not np.isfinite(value_array).all() or not len(unit):
        raise ValueError("filter values and directions must be finite and aligned")

    fwhm_rad = fwhm_mm / radius
    sigma_rad = fwhm_rad / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    cutoff_angle = cutoff_sigma * sigma_rad
    if cutoff_angle > np.pi:
        raise ValueError("filter cutoff angle must not exceed pi radians")
    cutoff_chord = 2.0 * np.sin(cutoff_angle / 2.0)
    tree = cKDTree(unit)
    neighborhoods = tree.query_ball_point(unit, cutoff_chord, workers=1)
    filtered, counts = _filter_from_neighborhoods(value_array, unit, neighborhoods, sigma_rad)
    constant_residual = _constant_filter_residual(unit, neighborhoods, sigma_rad)
    if constant_residual > 1e-12 or not np.isfinite(filtered).all():
        raise ValueError("spherical filter failed its constant-field invariant")
    diagnostics = SphericalFilterDiagnostics(
        fwhm_mm=fwhm_mm,
        fwhm_rad=float(fwhm_rad),
        sigma_rad=float(sigma_rad),
        cutoff_sigma=cutoff_sigma,
        cutoff_chord=float(cutoff_chord),
        minimum_neighbor_count=int(counts.min()),
        maximum_neighbor_count=int(counts.max()),
        constant_residual=constant_residual,
    )
    return immutable_float_array(filtered), diagnostics


def build_relief_geometry(
    topology: IcosphereTopology,
    filtered_values: object,
    base_diameter_mm: float,
    maximum_relief_mm: float,
) -> ReliefGeometry:
    """Build only the legacy 80 mm / 1.2 mm relief geometry contract."""
    if not isinstance(topology, IcosphereTopology):
        raise TypeError("topology must be an IcosphereTopology")
    diameter = _positive_finite_number(base_diameter_mm, field="base diameter")
    relief = _positive_finite_number(maximum_relief_mm, field="maximum relief")
    if diameter != 80.0 or relief != 1.2:
        raise ValueError("canonical geometry must use an 80.0 mm diameter and 1.2 mm relief")
    if topology.subdivisions != 7:
        raise ValueError("canonical geometry must use the approved subdivision-7 topology")
    return build_radial_geometry(
        topology,
        filtered_values,
        GlobeGeometrySpec(diameter, relief, 7),
    )

"""Field-led presentation luminance evaluated at arbitrary crystal directions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from kikuchi_lab.kinematical.contracts import KinematicalRecipe
from kikuchi_lab.kinematical.render import asinh_tone_map
from kikuchi_lab.near_depth.contracts import NearDepthTreatmentRecipe
from kikuchi_lab.near_depth.overlap import (
    AxialBandSet,
    accumulate_additional_overlap,
    apply_optical_depth,
    collapse_antipodal_reflectors,
    compute_overlap_field,
)

from .reprojection import sample_stereographic_channel, stereographic_grid


def _owned(array: object, dtype: np.dtype) -> np.ndarray:
    value = np.ascontiguousarray(np.asarray(array, dtype=dtype))
    return np.frombuffer(value.tobytes(order="C"), dtype=dtype).reshape(value.shape)


@dataclass(frozen=True)
class PresentationSource:
    """Immutable field-led inputs for pointwise spherical presentation."""

    toned_master: np.ndarray
    axial_bands: AxialBandSet
    band_weights: np.ndarray
    overlap_normalization: float
    upper_directions: np.ndarray
    upper_valid: np.ndarray
    gain: float
    ceiling: float
    ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        toned = _owned(self.toned_master, np.dtype("<f4"))
        weights = _owned(self.band_weights, np.dtype("<f8"))
        directions = _owned(self.upper_directions, np.dtype("<f8"))
        valid = _owned(self.upper_valid, np.dtype("bool"))
        size = toned.shape[-1] if toned.ndim == 3 else 0
        band_count = self.axial_bands.normals.shape[0]
        if toned.shape != (2, size, size) or size < 3:
            raise ValueError("toned master must have shape (2, N, N) with N at least 3")
        if weights.shape != (band_count,):
            raise ValueError("presentation band weights must have shape (M,)")
        if valid.shape != (size, size):
            raise ValueError("upper validity mask must match the toned master grid")
        if directions.shape != (int(np.count_nonzero(valid)), 3):
            raise ValueError("upper directions must cover every valid upper-grid sample")
        if not all(np.isfinite(value).all() for value in (toned, weights, directions)):
            raise ValueError("presentation source arrays must be finite")
        if np.any(weights < 0):
            raise ValueError("presentation band weights must be non-negative")
        if not np.allclose(
            np.linalg.norm(directions, axis=1),
            1.0,
            rtol=0.0,
            atol=5e-13,
        ):
            raise ValueError("upper directions must be unit vectors within 5e-13")
        if not np.isfinite(self.overlap_normalization) or not (self.overlap_normalization > 0):
            raise ValueError("overlap normalization must be finite and positive")
        if not np.isfinite(self.gain) or self.gain < 0:
            raise ValueError("optical-depth gain must be finite and non-negative")
        if not np.isfinite(self.ceiling) or not 0 < self.ceiling < 1:
            raise ValueError("luminance ceiling must be finite and in (0, 1)")
        object.__setattr__(self, "toned_master", toned)
        object.__setattr__(self, "band_weights", weights)
        object.__setattr__(self, "upper_directions", directions)
        object.__setattr__(self, "upper_valid", valid)
        object.__setattr__(self, "overlap_normalization", float(self.overlap_normalization))
        object.__setattr__(self, "gain", float(self.gain))
        object.__setattr__(self, "ceiling", float(self.ceiling))
        object.__setattr__(self, "ledger", MappingProxyType(dict(self.ledger)))


def _validated_master(master: np.ndarray) -> np.ndarray:
    raw = np.asarray(master)
    size = raw.shape[-1] if raw.ndim == 3 else 0
    if raw.shape != (2, size, size) or size < 3:
        raise ValueError("scientific master must have shape (2, N, N) with N at least 3")
    if raw.dtype != np.dtype(np.float32):
        raise ValueError("scientific master must use float32")
    if not np.isfinite(raw).all():
        raise ValueError("scientific master must contain finite values")
    return raw


def build_presentation_source(
    master: np.ndarray,
    reflectors: object,
    base_recipe: KinematicalRecipe,
    treatment: NearDepthTreatmentRecipe,
) -> PresentationSource:
    """Prepare immutable field-led state without modifying scientific arrays."""
    if treatment.center.enabled or treatment.boundary.enabled:
        raise ValueError("oriented presentation vector overlays must be disabled")
    raw = _validated_master(master)
    toned = np.stack(
        [
            asinh_tone_map(
                raw[index],
                percentiles=base_recipe.tone_percentiles,
                scale=base_recipe.tone_asinh_scale,
            )
            for index in (0, 1)
        ]
    )
    strengths = np.abs(np.asarray(getattr(reflectors, "structure_factor")))
    if (
        strengths.ndim != 1
        or not strengths.size
        or not np.isfinite(strengths).all()
        or not float(strengths.max()) > 0
    ):
        raise ValueError("reflector strengths must be finite, non-empty, and positive")
    maximum_strength = float(strengths.max())
    selected = reflectors[strengths >= treatment.overlap_relative_factor * maximum_strength]
    axial = collapse_antipodal_reflectors(selected)
    weights = (axial.structure_factor_abs / maximum_strength) ** treatment.weight_exponent
    overlap = compute_overlap_field(
        reflectors,
        size=raw.shape[-1],
        relative_factor=treatment.overlap_relative_factor,
        weight_exponent=treatment.weight_exponent,
        normalization_percentile=treatment.normalization_percentile,
    )
    grid = stereographic_grid(raw.shape[-1], "upper")
    ledger = {
        "scientific_claim": "presentation_only",
        "base_tone": "pointwise_asinh",
        "spatial_filter": "none",
        "interpolation": "bilinear",
        "relative_factor": treatment.overlap_relative_factor,
        "weight_exponent": treatment.weight_exponent,
        "normalization_percentile": treatment.normalization_percentile,
        "normalization_value": overlap.normalization_value,
        "optical_gain": treatment.optical_depth_gain,
        "luminance_ceiling": treatment.luminance_ceiling,
        "center_overlay": False,
        "boundary_overlay": False,
    }
    return PresentationSource(
        toned_master=toned,
        axial_bands=axial,
        band_weights=weights,
        overlap_normalization=overlap.normalization_value,
        upper_directions=grid.directions[grid.valid],
        upper_valid=grid.valid,
        gain=treatment.optical_depth_gain,
        ceiling=treatment.luminance_ceiling,
        ledger=ledger,
    )


def evaluate_presentation(
    source: PresentationSource,
    crystal_directions: np.ndarray,
) -> np.ndarray:
    """Evaluate field-led luminance pointwise on arbitrary unit directions."""
    directions = np.asarray(crystal_directions, dtype=np.float64)
    base, _ = sample_stereographic_channel(source.toned_master, directions)
    raw_overlap = accumulate_additional_overlap(
        directions=directions,
        normals=source.axial_bands.normals,
        half_width_sines=np.sin(source.axial_bands.theta_radian),
        weights=source.band_weights,
    )
    normalized = np.clip(
        raw_overlap / source.overlap_normalization,
        0.0,
        1.0,
    )
    return apply_optical_depth(
        base,
        normalized,
        gain=source.gain,
        luminance_ceiling=source.ceiling,
    )


__all__ = [
    "PresentationSource",
    "build_presentation_source",
    "evaluate_presentation",
]

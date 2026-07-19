"""Stable grayscale animation frames from a retained dynamical master field."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from kikuchi_lab.relief.field import SphericalScalarField, sample_spherical_field


_BACKGROUND = np.array((14, 20, 23), dtype=np.uint8)
_BOUNDARY = (148, 158, 163)


@dataclass(frozen=True)
class DynamicalMasterRotationSpec:
    """One active sample-frame rotation sampled on a fixed upper hemisphere."""

    axis_sample: tuple[float, float, float]
    frame_count: int = 24
    frame_size_px: int = 512
    disk_radius_fraction: float = 0.94

    def __post_init__(self) -> None:
        axis = np.asarray(self.axis_sample, dtype=np.float64)
        if axis.shape != (3,) or not np.isfinite(axis).all() or np.linalg.norm(axis) <= 0:
            raise ValueError("axis_sample must be one finite nonzero 3-vector")
        if type(self.frame_count) is not int or self.frame_count < 2:
            raise ValueError("frame_count must be an integer of at least 2")
        if type(self.frame_size_px) is not int or self.frame_size_px < 128:
            raise ValueError("frame_size_px must be an integer of at least 128")
        if not 0.5 <= self.disk_radius_fraction < 1.0:
            raise ValueError("disk_radius_fraction must be in [0.5, 1.0)")

    @property
    def unit_axis_sample(self) -> np.ndarray:
        axis = np.asarray(self.axis_sample, dtype=np.float64)
        return axis / np.linalg.norm(axis)

    def angle_deg(self, frame_index: int) -> float:
        if type(frame_index) is not int or not 0 <= frame_index <= self.frame_count:
            raise ValueError("frame_index must be in [0, frame_count]")
        return 360.0 * frame_index / self.frame_count


@dataclass(frozen=True)
class DynamicalToneMap:
    """One fixed, source-field-derived mapping shared by every video frame."""

    black_percentile: float = 0.5
    white_percentile: float = 99.5
    gamma: float = 0.82

    def __post_init__(self) -> None:
        if not 0.0 <= self.black_percentile < self.white_percentile <= 100.0:
            raise ValueError("tone percentiles must satisfy 0 <= black < white <= 100")
        if not math.isfinite(self.gamma) or self.gamma <= 0.0:
            raise ValueError("tone gamma must be finite and positive")

    def limits(self, field: SphericalScalarField) -> tuple[float, float]:
        low, high = np.percentile(
            field.raw_values,
            (self.black_percentile, self.white_percentile),
        )
        if not math.isfinite(float(low)) or not math.isfinite(float(high)) or high <= low:
            raise ValueError("dynamical field must have a finite nonzero tone range")
        return float(low), float(high)


def axis_angle_matrix(axis: np.ndarray, angle_deg: float) -> np.ndarray:
    """Return a right-handed active Rodrigues rotation in sample coordinates."""
    unit_axis = np.asarray(axis, dtype=np.float64)
    unit_axis /= np.linalg.norm(unit_axis)
    x, y, z = unit_axis
    angle = math.radians(angle_deg % 360.0)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    skew = np.array(((0.0, -z, y), (z, 0.0, -x), (-y, x, 0.0)), dtype=np.float64)
    return cosine * np.eye(3) + sine * skew + (1.0 - cosine) * np.outer(unit_axis, unit_axis)


def _screen_directions(spec: DynamicalMasterRotationSpec) -> tuple[np.ndarray, np.ndarray]:
    """Return stereographic upper-hemisphere directions and a circular mask."""
    pixels = np.arange(spec.frame_size_px, dtype=np.float64)
    center = (spec.frame_size_px - 1) / 2.0
    radius = center * spec.disk_radius_fraction
    x, y = np.meshgrid((pixels - center) / radius, (center - pixels) / radius)
    radial_squared = x * x + y * y
    mask = radial_squared <= 1.0
    denominator = 1.0 + radial_squared[mask]
    directions = np.column_stack(
        (
            2.0 * x[mask] / denominator,
            2.0 * y[mask] / denominator,
            (1.0 - radial_squared[mask]) / denominator,
        )
    )
    return directions, mask


def render_dynamical_master_frame(
    field: SphericalScalarField,
    spec: DynamicalMasterRotationSpec,
    *,
    frame_index: int,
    tone_map: DynamicalToneMap | None = None,
) -> Image.Image:
    """Render one upper-hemisphere frame by actively rotating the stored field."""
    if not isinstance(field, SphericalScalarField):
        raise TypeError("field must be a SphericalScalarField")
    tone = DynamicalToneMap() if tone_map is None else tone_map
    screen_directions, mask = _screen_directions(spec)
    active_rotation = axis_angle_matrix(spec.unit_axis_sample, spec.angle_deg(frame_index))
    # The field stays crystal-fixed: evaluate each sample-frame direction in crystal coordinates.
    crystal_directions = screen_directions @ active_rotation
    values = sample_spherical_field(field, crystal_directions).raw_values
    black, white = tone.limits(field)
    grayscale = np.clip((values - black) / (white - black), 0.0, 1.0) ** tone.gamma
    intensity = np.rint(255.0 * grayscale).astype(np.uint8)

    canvas = np.empty((spec.frame_size_px, spec.frame_size_px, 3), dtype=np.uint8)
    canvas[...] = _BACKGROUND
    canvas[mask] = intensity[:, None]
    image = Image.fromarray(canvas, mode="RGB")
    center = (spec.frame_size_px - 1) / 2.0
    radius = center * spec.disk_radius_fraction
    ImageDraw.Draw(image).ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        outline=_BOUNDARY,
        width=max(1, round(spec.frame_size_px / 768.0)),
    )
    return image


__all__ = [
    "DynamicalMasterRotationSpec",
    "DynamicalToneMap",
    "axis_angle_matrix",
    "render_dynamical_master_frame",
]

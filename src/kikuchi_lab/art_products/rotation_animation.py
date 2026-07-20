"""Fast, deterministic animations of fixed direct-reflector compositions.

The selected reflector hierarchy is loaded once from an existing published
hemisphere bundle.  Each frame actively rotates those crystal normals in the
sample frame; it never rotates a flattened PNG and never reruns a diffraction
simulation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


_ARTBOARD_MM = 145.0
_OUTER_DIAMETER_MM = 132.0
_BOUNDARY_WIDTH_MM = 2.2
_CROP_RADIUS = 0.90
_NUMERIC_TOLERANCE = 1e-12
_DEPTH_BACKGROUND = (16, 21, 25)
_DEPTH_BAND_COLOR = (224, 231, 234)
_DEPTH_RIM_COLOR = (210, 220, 226)


@dataclass(frozen=True)
class DirectReflectorBand:
    """One fixed member of the reviewed direct-reflector composition."""

    member_id: str
    normal_crystal: tuple[float, float, float]
    width_mm: float

    def __post_init__(self) -> None:
        normal = np.asarray(self.normal_crystal, dtype=np.float64)
        if normal.shape != (3,) or not np.isfinite(normal).all():
            raise ValueError("normal_crystal must be one finite length-three vector")
        if not math.isclose(float(np.linalg.norm(normal)), 1.0, abs_tol=1e-12):
            raise ValueError("normal_crystal must have unit length")
        if not self.member_id or not math.isfinite(self.width_mm) or self.width_mm <= 0.0:
            raise ValueError("band requires an ID and positive finite width")


@dataclass(frozen=True)
class RotationAnimationSpec:
    """A seamless active sample-frame rotation and its raster presentation."""

    axis_sample: tuple[float, float, float]
    frame_count: int = 72
    frame_size_px: int = 1024
    supersampling: int = 2
    great_circle_samples: int = 721

    def __post_init__(self) -> None:
        axis = np.asarray(self.axis_sample, dtype=np.float64)
        if axis.shape != (3,) or not np.isfinite(axis).all() or np.linalg.norm(axis) <= 0.0:
            raise ValueError("axis_sample must be one nonzero finite length-three vector")
        if type(self.frame_count) is not int or self.frame_count < 2:
            raise ValueError("frame_count must be an integer of at least 2")
        if type(self.frame_size_px) is not int or self.frame_size_px < 128:
            raise ValueError("frame_size_px must be an integer of at least 128")
        if type(self.supersampling) is not int or self.supersampling < 1:
            raise ValueError("supersampling must be a positive integer")
        if type(self.great_circle_samples) is not int or self.great_circle_samples < 33:
            raise ValueError("great_circle_samples must be an integer of at least 33")

    @property
    def unit_axis_sample(self) -> np.ndarray:
        axis = np.asarray(self.axis_sample, dtype=np.float64)
        return axis / np.linalg.norm(axis)

    def angle_deg(self, frame_index: int) -> float:
        if type(frame_index) is not int or not 0 <= frame_index <= self.frame_count:
            raise ValueError("frame_index must be in [0, frame_count]")
        return 360.0 * frame_index / self.frame_count


def selected_bands_from_snapshots(
    catalog_snapshot: Mapping[str, object],
    selection_snapshot: Mapping[str, object],
) -> tuple[DirectReflectorBand, ...]:
    """Bind a published selection's ordered widths to its crystal normals."""
    catalog = catalog_snapshot.get("content")
    selected = selection_snapshot.get("selected_paths")
    if not isinstance(catalog, Mapping) or not isinstance(selected, Sequence):
        raise ValueError("catalog and selection snapshots have unexpected schema")
    members = catalog.get("members")
    if not isinstance(members, Sequence):
        raise ValueError("catalog snapshot is missing members")
    normals: dict[str, tuple[float, float, float]] = {}
    for member in members:
        if not isinstance(member, Mapping):
            raise ValueError("catalog member must be a mapping")
        member_id = member.get("member_id")
        normal = member.get("normal_crystal")
        if (
            not isinstance(member_id, str)
            or not isinstance(normal, Sequence)
            or len(normal) != 3
        ):
            raise ValueError("catalog member is missing its crystal normal")
        normals[member_id] = tuple(float(value) for value in normal)

    bands: list[DirectReflectorBand] = []
    for path in selected:
        if not isinstance(path, Mapping):
            raise ValueError("selection path must be a mapping")
        member_id = path.get("member_id")
        width = path.get("width_mm")
        if not isinstance(member_id, str) or not isinstance(width, (int, float)):
            raise ValueError("selection path is missing member_id or width_mm")
        if member_id not in normals:
            raise ValueError("selection member is absent from its catalog")
        bands.append(DirectReflectorBand(member_id, normals[member_id], float(width)))
    if not bands:
        raise ValueError("selection snapshot has no paths")
    return tuple(bands)


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


def _canonical_axial_normal(normal: np.ndarray) -> np.ndarray:
    result = np.array(normal, dtype=np.float64, copy=True)
    for component in result:
        if abs(float(component)) > 5e-15:
            if component < 0.0:
                result *= -1.0
            break
    return result


def _projected_upper_trace(normal_sample: np.ndarray, sample_count: int) -> np.ndarray:
    """Project the contiguous upper-hemisphere interval of one axial great circle."""
    normal = _canonical_axial_normal(normal_sample)
    specimen_z = np.array((0.0, 0.0, 1.0))
    equator_anchor = np.cross(specimen_z, normal)
    anchor_norm = float(np.linalg.norm(equator_anchor))
    if anchor_norm <= 5e-14:
        equator_anchor = np.array((1.0, 0.0, 0.0))
    else:
        equator_anchor /= anchor_norm
    upper_axis = np.cross(normal, equator_anchor)
    upper_axis /= np.linalg.norm(upper_axis)
    if upper_axis[2] < 0.0:
        upper_axis *= -1.0
    angles = np.linspace(0.0, 2.0 * np.pi, sample_count, endpoint=True)
    circle = (
        np.cos(angles)[:, None] * equator_anchor[None, :]
        + np.sin(angles)[:, None] * upper_axis[None, :]
    )
    upper_arc = circle if abs(float(upper_axis[2])) <= 5e-14 else circle[: sample_count // 2 + 1]
    return upper_arc[:, :2] / (1.0 + upper_arc[:, 2, None])


def _clip_trace(points: np.ndarray, radius: float) -> tuple[np.ndarray, ...]:
    """Clip a sampled trace to the circular display primitive."""
    fragments: list[np.ndarray] = []
    current: list[np.ndarray] = []
    radius_squared = radius * radius
    for start, stop in zip(points[:-1], points[1:], strict=True):
        direction = stop - start
        quadratic = float(np.dot(direction, direction))
        if quadratic <= _NUMERIC_TOLERANCE**2:
            continue
        linear = 2.0 * float(np.dot(start, direction))
        constant = float(np.dot(start, start) - radius_squared)
        discriminant = linear * linear - 4.0 * quadratic * constant
        if discriminant <= 0.0:
            if len(current) >= 2:
                fragments.append(np.asarray(current, dtype=np.float64))
            current = []
            continue
        root = math.sqrt(discriminant)
        first = (-linear - root) / (2.0 * quadratic)
        second = (-linear + root) / (2.0 * quadratic)
        lower, upper = max(0.0, min(first, second)), min(1.0, max(first, second))
        if upper - lower <= _NUMERIC_TOLERANCE:
            if len(current) >= 2:
                fragments.append(np.asarray(current, dtype=np.float64))
            current = []
            continue
        clipped_start, clipped_stop = start + lower * direction, start + upper * direction
        if current and float(np.linalg.norm(clipped_start - current[-1])) > _NUMERIC_TOLERANCE:
            if len(current) >= 2:
                fragments.append(np.asarray(current, dtype=np.float64))
            current = []
        current.extend((clipped_start, clipped_stop))
    if len(current) >= 2:
        fragments.append(np.asarray(current, dtype=np.float64))
    return tuple(fragments)


def render_direct_reflector_frame(
    bands: Sequence[DirectReflectorBand],
    base_orientation: Orientation,
    spec: RotationAnimationSpec,
    frame_index: int,
) -> Image.Image:
    """Render one frame after active rotation of the actual reflector normals."""
    pixel_size = spec.frame_size_px * spec.supersampling
    scale_px_per_mm = pixel_size / _ARTBOARD_MM
    center_mm = _ARTBOARD_MM / 2.0
    inner_radius_mm = _OUTER_DIAMETER_MM / 2.0 - _BOUNDARY_WIDTH_MM
    rotation = axis_angle_matrix(spec.unit_axis_sample, spec.angle_deg(frame_index))
    base_matrix = orientation_matrix(base_orientation)

    band_layer = Image.new("L", (pixel_size, pixel_size), 0)
    draw_bands = ImageDraw.Draw(band_layer)
    for band in bands:
        normal_sample = rotation @ base_matrix @ np.asarray(band.normal_crystal)
        trace = _projected_upper_trace(normal_sample, spec.great_circle_samples)
        for fragment in _clip_trace(trace, _CROP_RADIUS):
            points_mm = center_mm + (inner_radius_mm / _CROP_RADIUS) * fragment
            points_px = [tuple((point * scale_px_per_mm).tolist()) for point in points_mm]
            width_px = max(1, round(band.width_mm * scale_px_per_mm))
            draw_bands.line(points_px, fill=255, width=width_px, joint="curve")
            cap = width_px / 2.0
            for point in (points_px[0], points_px[-1]):
                draw_bands.ellipse(
                    (point[0] - cap, point[1] - cap, point[0] + cap, point[1] + cap),
                    fill=255,
                )

    mask = Image.new("L", (pixel_size, pixel_size), 0)
    center_px = center_mm * scale_px_per_mm
    inner_radius_px = inner_radius_mm * scale_px_per_mm
    ImageDraw.Draw(mask).ellipse(
        (center_px - inner_radius_px, center_px - inner_radius_px,
         center_px + inner_radius_px, center_px + inner_radius_px),
        fill=255,
    )
    image = Image.new("RGB", (pixel_size, pixel_size), "white")
    image.paste((0, 0, 0), mask=ImageChops.multiply(band_layer, mask))

    outer_radius_px = (_OUTER_DIAMETER_MM / 2.0) * scale_px_per_mm
    ImageDraw.Draw(image).ellipse(
        (center_px - outer_radius_px, center_px - outer_radius_px,
         center_px + outer_radius_px, center_px + outer_radius_px),
        outline="black",
        width=max(1, round(_BOUNDARY_WIDTH_MM * scale_px_per_mm)),
    )
    if spec.supersampling > 1:
        image = image.resize((spec.frame_size_px, spec.frame_size_px), Image.Resampling.LANCZOS)
    return image


def render_direct_reflector_depth_frame(
    bands: Sequence[DirectReflectorBand],
    base_orientation: Orientation,
    spec: RotationAnimationSpec,
    frame_index: int,
) -> Image.Image:
    """Render a dark additive-ribbon treatment of actively rotated reflectors.

    This is a deliberately idealized presentation layer: each exact projected
    reflector trace is composited as a translucent ribbon, so crossings become
    brighter while all geometric positions and widths remain catalog-derived.
    """
    pixel_size = spec.frame_size_px * spec.supersampling
    scale_px_per_mm = pixel_size / _ARTBOARD_MM
    center_mm = _ARTBOARD_MM / 2.0
    inner_radius_mm = _OUTER_DIAMETER_MM / 2.0 - _BOUNDARY_WIDTH_MM
    center_px = center_mm * scale_px_per_mm
    inner_radius_px = inner_radius_mm * scale_px_per_mm
    rotation = axis_angle_matrix(spec.unit_axis_sample, spec.angle_deg(frame_index))
    base_matrix = orientation_matrix(base_orientation)
    width_min = min(band.width_mm for band in bands)
    width_max = max(band.width_mm for band in bands)
    width_span = max(width_max - width_min, 1e-12)

    interior = Image.new("L", (pixel_size, pixel_size), 0)
    ImageDraw.Draw(interior).ellipse(
        (
            center_px - inner_radius_px,
            center_px - inner_radius_px,
            center_px + inner_radius_px,
            center_px + inner_radius_px,
        ),
        fill=255,
    )
    image = Image.new("RGBA", (pixel_size, pixel_size), (*_DEPTH_BACKGROUND, 255))
    for band in sorted(bands, key=lambda item: (item.width_mm, item.member_id)):
        normal_sample = rotation @ base_matrix @ np.asarray(band.normal_crystal)
        trace = _projected_upper_trace(normal_sample, spec.great_circle_samples)
        ribbon = Image.new("L", (pixel_size, pixel_size), 0)
        draw_ribbon = ImageDraw.Draw(ribbon)
        width_px = max(1, round(band.width_mm * scale_px_per_mm))
        for fragment in _clip_trace(trace, _CROP_RADIUS):
            points_mm = center_mm + (inner_radius_mm / _CROP_RADIUS) * fragment
            points_px = [tuple((point * scale_px_per_mm).tolist()) for point in points_mm]
            envelope_width = max(width_px, round(width_px * 1.35))
            draw_ribbon.line(points_px, fill=255, width=envelope_width, joint="curve")
            cap = envelope_width / 2.0
            for point in (points_px[0], points_px[-1]):
                draw_ribbon.ellipse(
                    (point[0] - cap, point[1] - cap, point[0] + cap, point[1] + cap),
                    fill=255,
                )
        normalized_width = (band.width_mm - width_min) / width_span
        envelope_alpha = int(round(255.0 * (0.025 + 0.055 * normalized_width)))
        envelope = ImageChops.multiply(ribbon, interior).point(
            lambda value: value * envelope_alpha // 255
        )
        colored_envelope = Image.new("RGBA", (pixel_size, pixel_size), _DEPTH_BAND_COLOR)
        colored_envelope.putalpha(envelope)
        image.alpha_composite(colored_envelope)

        core = Image.new("L", (pixel_size, pixel_size), 0)
        draw_core = ImageDraw.Draw(core)
        for fragment in _clip_trace(trace, _CROP_RADIUS):
            points_mm = center_mm + (inner_radius_mm / _CROP_RADIUS) * fragment
            points_px = [tuple((point * scale_px_per_mm).tolist()) for point in points_mm]
            draw_core.line(points_px, fill=255, width=width_px, joint="curve")
            cap = width_px / 2.0
            for point in (points_px[0], points_px[-1]):
                draw_core.ellipse(
                    (point[0] - cap, point[1] - cap, point[0] + cap, point[1] + cap),
                    fill=255,
                )
        core_alpha = int(round(255.0 * (0.10 + 0.34 * normalized_width**0.75)))
        core_mask = ImageChops.multiply(core, interior).point(
            lambda value: value * core_alpha // 255
        )
        colored_core = Image.new("RGBA", (pixel_size, pixel_size), _DEPTH_BAND_COLOR)
        colored_core.putalpha(core_mask)
        image.alpha_composite(colored_core)

    outer_radius_px = (_OUTER_DIAMETER_MM / 2.0) * scale_px_per_mm
    ImageDraw.Draw(image).ellipse(
        (
            center_px - outer_radius_px,
            center_px - outer_radius_px,
            center_px + outer_radius_px,
            center_px + outer_radius_px,
        ),
        outline=(*_DEPTH_RIM_COLOR, 255),
        width=max(1, round(_BOUNDARY_WIDTH_MM * scale_px_per_mm / 2.0)),
    )
    result = image.convert("RGB")
    if spec.supersampling > 1:
        result = result.resize((spec.frame_size_px, spec.frame_size_px), Image.Resampling.LANCZOS)
    return result


__all__ = [
    "DirectReflectorBand",
    "RotationAnimationSpec",
    "axis_angle_matrix",
    "render_direct_reflector_depth_frame",
    "render_direct_reflector_frame",
    "selected_bands_from_snapshots",
]

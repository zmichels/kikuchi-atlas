"""Physical tattoo geometry plus deterministic primary art renderers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from io import BytesIO
from types import MappingProxyType
from typing import Literal

import matplotlib
import numpy as np
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from PIL import Image, ImageChops, ImageDraw

from kikuchi_lab.art_products.contracts import (
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)
from kikuchi_lab.art_products.tattoo_selection import (
    HemisphereSelectionRecipe,
    TattooSelection,
)


_PATH_COUNT = 11
_PROJECTION = "upper_specimen_stereographic_center_trace"
_MIN_EDGE_GAP_MM = 1.5
_MIN_ENDPOINT_CLEARANCE_MM = 2.0
_NUMERIC_TOLERANCE = 1e-12
_ARRAY_DTYPE = np.dtype("<f8")
_POINTS_PER_INCH = 72.0
_MILLIMETERS_PER_INCH = 25.4
_PNG_DPI = 300
_PNG_SIZE_PX = 1713
_MOCKUP_BACKGROUND = "#d8b59a"
_STENCIL_BACKGROUND = "#ffffff"
_STROKE_CLIP_ID = "tattoo-band-layer-clip"

IntersectionKind = Literal["none", "crossing", "endpoint", "tangent"]
ClearanceKind = Literal["noncrossing_edge_gap", "unrelated_endpoint"]


class TattooClearanceError(ValueError):
    """Physical-clearance failure carrying the exact conflicting path pair."""

    def __init__(
        self,
        message: str,
        *,
        clearance_kind: ClearanceKind,
        member_ids: tuple[str, str],
    ) -> None:
        super().__init__(message)
        self.clearance_kind = clearance_kind
        self.member_ids = member_ids


def _cross_2d(first: np.ndarray, second: np.ndarray) -> float:
    return float(first[0] * second[1] - first[1] * second[0])


def _append_unique(points: list[np.ndarray], point: np.ndarray) -> None:
    if not points or float(np.linalg.norm(point - points[-1])) > _NUMERIC_TOLERANCE:
        points.append(np.array(point, dtype=_ARRAY_DTYPE, copy=True))


def _finish_fragment(
    fragments: list[np.ndarray],
    points: list[np.ndarray],
) -> None:
    if len(points) >= 2:
        fragment = np.asarray(points, dtype=_ARRAY_DTYPE)
        if np.any(np.linalg.norm(np.diff(fragment, axis=0), axis=1) > 0.0):
            fragments.append(fragment)
    points.clear()


def _clip_polyline_to_circle(
    points: np.ndarray,
    radius: float,
) -> tuple[np.ndarray, ...]:
    """Clip sampled segments analytically and return interior fragments."""
    source = np.asarray(points, dtype=_ARRAY_DTYPE)
    if source.ndim != 2 or source.shape[1:] != (2,) or source.shape[0] < 2:
        raise ValueError("points must have shape (N, 2) with N >= 2")
    if not np.isfinite(source).all():
        raise ValueError("points must contain finite numbers")
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError("radius must be positive and finite")

    radius_squared = np.float64(radius * radius)
    fragments: list[np.ndarray] = []
    current: list[np.ndarray] = []
    for start, stop in zip(source[:-1], source[1:], strict=True):
        direction = stop - start
        quadratic = float(np.dot(direction, direction))
        if quadratic <= _NUMERIC_TOLERANCE**2:
            continue
        linear = 2.0 * float(np.dot(start, direction))
        constant = float(np.dot(start, start) - radius_squared)
        discriminant = linear * linear - 4.0 * quadratic * constant
        discriminant_tolerance = (
            64.0
            * np.finfo(np.float64).eps
            * max(
                linear * linear,
                abs(4.0 * quadratic * constant),
                1.0,
            )
        )
        if discriminant <= discriminant_tolerance:
            _finish_fragment(fragments, current)
            continue

        root = math.sqrt(discriminant)
        first_root = (-linear - root) / (2.0 * quadratic)
        second_root = (-linear + root) / (2.0 * quadratic)
        lower = max(0.0, min(first_root, second_root))
        upper = min(1.0, max(first_root, second_root))
        if upper - lower <= _NUMERIC_TOLERANCE:
            _finish_fragment(fragments, current)
            continue

        clipped_start = start + lower * direction
        clipped_stop = start + upper * direction
        if current and float(np.linalg.norm(clipped_start - current[-1])) > (_NUMERIC_TOLERANCE):
            _finish_fragment(fragments, current)
        _append_unique(current, clipped_start)
        _append_unique(current, clipped_stop)

    _finish_fragment(fragments, current)
    return tuple(fragments)


def _segment_intersection_details(
    first_start: np.ndarray,
    first_stop: np.ndarray,
    second_start: np.ndarray,
    second_stop: np.ndarray,
) -> tuple[IntersectionKind, np.ndarray | None]:
    first_direction = first_stop - first_start
    second_direction = second_stop - second_start
    offset = second_start - first_start
    denominator = _cross_2d(first_direction, second_direction)
    scale = max(
        float(np.linalg.norm(first_direction) * np.linalg.norm(second_direction)),
        1.0,
    )
    tolerance = 64.0 * np.finfo(np.float64).eps * scale
    if abs(denominator) <= tolerance:
        if abs(_cross_2d(offset, first_direction)) > tolerance:
            return "none", None
        axis = int(np.argmax(np.abs(first_direction)))
        if abs(float(first_direction[axis])) <= _NUMERIC_TOLERANCE:
            return "endpoint", np.array(first_start, dtype=_ARRAY_DTYPE, copy=True)
        first_values = sorted((float(first_start[axis]), float(first_stop[axis])))
        second_values = sorted((float(second_start[axis]), float(second_stop[axis])))
        if min(first_values[1], second_values[1]) + _NUMERIC_TOLERANCE < max(
            first_values[0], second_values[0]
        ):
            return "none", None
        return "tangent", None

    first_parameter = _cross_2d(offset, second_direction) / denominator
    second_parameter = _cross_2d(offset, first_direction) / denominator
    if not (
        -_NUMERIC_TOLERANCE <= first_parameter <= 1.0 + _NUMERIC_TOLERANCE
        and -_NUMERIC_TOLERANCE <= second_parameter <= 1.0 + _NUMERIC_TOLERANCE
    ):
        return "none", None
    intersection = first_start + first_parameter * first_direction
    if (
        _NUMERIC_TOLERANCE < first_parameter < 1.0 - _NUMERIC_TOLERANCE
        and _NUMERIC_TOLERANCE < second_parameter < 1.0 - _NUMERIC_TOLERANCE
    ):
        return "crossing", intersection
    return "endpoint", intersection


def _segment_intersection_kind(
    first_start: np.ndarray,
    first_stop: np.ndarray,
    second_start: np.ndarray,
    second_stop: np.ndarray,
) -> IntersectionKind:
    """Classify a float64 segment contact for validation diagnostics."""
    kind, _ = _segment_intersection_details(
        np.asarray(first_start, dtype=_ARRAY_DTYPE),
        np.asarray(first_stop, dtype=_ARRAY_DTYPE),
        np.asarray(second_start, dtype=_ARRAY_DTYPE),
        np.asarray(second_stop, dtype=_ARRAY_DTYPE),
    )
    return kind


def _incident_directions(points: np.ndarray, intersection: np.ndarray) -> list[np.ndarray]:
    directions: list[np.ndarray] = []
    for start, stop in zip(points[:-1], points[1:], strict=True):
        if _point_segment_distance(intersection, start, stop) > _NUMERIC_TOLERANCE:
            continue
        for point in (start, stop):
            direction = point - intersection
            length = float(np.linalg.norm(direction))
            if length <= _NUMERIC_TOLERANCE:
                continue
            unit = direction / length
            if not any(
                abs(_cross_2d(unit, prior)) <= _NUMERIC_TOLERANCE
                and float(np.dot(unit, prior)) > 0.0
                for prior in directions
            ):
                directions.append(unit)
    return directions


def _directions_alternate(
    first: list[np.ndarray],
    second: list[np.ndarray],
) -> bool:
    if len(first) < 2 or len(second) < 2:
        return False
    for first_pair in (
        (first[i], first[j]) for i in range(len(first)) for j in range(i + 1, len(first))
    ):
        for second_pair in (
            (second[i], second[j]) for i in range(len(second)) for j in range(i + 1, len(second))
        ):
            labeled = [
                (math.atan2(float(vector[1]), float(vector[0])) % (2.0 * math.pi), label)
                for label, pair in (("first", first_pair), ("second", second_pair))
                for vector in pair
            ]
            labeled.sort()
            labels = [label for _, label in labeled]
            if all(labels[index] != labels[(index + 1) % 4] for index in range(4)):
                return True
    return False


def _paths_cross(first: np.ndarray, second: np.ndarray) -> bool:
    first_starts = first[:-1]
    first_directions = np.diff(first, axis=0)
    second_starts = second[:-1]
    second_directions = np.diff(second, axis=0)
    denominator = (
        first_directions[:, None, 0] * second_directions[None, :, 1]
        - first_directions[:, None, 1] * second_directions[None, :, 0]
    )
    scale = np.maximum(
        np.linalg.norm(first_directions, axis=1)[:, None]
        * np.linalg.norm(second_directions, axis=1)[None, :],
        1.0,
    )
    nonparallel = np.abs(denominator) > 64.0 * np.finfo(np.float64).eps * scale
    safe_denominator = np.where(nonparallel, denominator, 1.0)
    offset = second_starts[None, :, :] - first_starts[:, None, :]
    first_parameter = (
        offset[:, :, 0] * second_directions[None, :, 1]
        - offset[:, :, 1] * second_directions[None, :, 0]
    ) / safe_denominator
    second_parameter = (
        offset[:, :, 0] * first_directions[:, None, 1]
        - offset[:, :, 1] * first_directions[:, None, 0]
    ) / safe_denominator
    proper_crossing = (
        nonparallel
        & (first_parameter > _NUMERIC_TOLERANCE)
        & (first_parameter < 1.0 - _NUMERIC_TOLERANCE)
        & (second_parameter > _NUMERIC_TOLERANCE)
        & (second_parameter < 1.0 - _NUMERIC_TOLERANCE)
    )
    if bool(np.any(proper_crossing)):
        return True

    endpoint_contact = (
        nonparallel
        & (first_parameter >= -_NUMERIC_TOLERANCE)
        & (first_parameter <= 1.0 + _NUMERIC_TOLERANCE)
        & (second_parameter >= -_NUMERIC_TOLERANCE)
        & (second_parameter <= 1.0 + _NUMERIC_TOLERANCE)
    )
    if not bool(np.any(endpoint_contact)):
        return False

    endpoint_intersections: list[np.ndarray] = []
    for first_index, second_index in np.argwhere(endpoint_contact):
        kind, point = _segment_intersection_details(
            first[first_index],
            first[first_index + 1],
            second[second_index],
            second[second_index + 1],
        )
        if kind == "crossing":
            return True
        if (
            kind == "endpoint"
            and point is not None
            and not any(
                float(np.linalg.norm(point - prior)) <= _NUMERIC_TOLERANCE
                for prior in endpoint_intersections
            )
        ):
            endpoint_intersections.append(point)
    return any(
        _directions_alternate(
            _incident_directions(first, intersection),
            _incident_directions(second, intersection),
        )
        for intersection in endpoint_intersections
    )


def _point_segment_distance(
    point: np.ndarray,
    start: np.ndarray,
    stop: np.ndarray,
) -> float:
    direction = stop - start
    length_squared = float(np.dot(direction, direction))
    if length_squared <= _NUMERIC_TOLERANCE**2:
        return float(np.linalg.norm(point - start))
    parameter = float(np.dot(point - start, direction) / length_squared)
    parameter = min(max(parameter, 0.0), 1.0)
    return float(np.linalg.norm(point - (start + parameter * direction)))


def _segment_distance(
    first_start: np.ndarray,
    first_stop: np.ndarray,
    second_start: np.ndarray,
    second_stop: np.ndarray,
) -> float:
    kind, _ = _segment_intersection_details(
        first_start,
        first_stop,
        second_start,
        second_stop,
    )
    if kind != "none":
        return 0.0
    return min(
        _point_segment_distance(first_start, second_start, second_stop),
        _point_segment_distance(first_stop, second_start, second_stop),
        _point_segment_distance(second_start, first_start, first_stop),
        _point_segment_distance(second_stop, first_start, first_stop),
    )


def _polyline_distance(first: np.ndarray, second: np.ndarray) -> float:
    def point_distances(points: np.ndarray, polyline: np.ndarray) -> float:
        starts = polyline[:-1]
        directions = np.diff(polyline, axis=0)
        length_squared = np.sum(directions * directions, axis=1)
        offsets = points[:, None, :] - starts[None, :, :]
        parameters = np.sum(offsets * directions[None, :, :], axis=2) / (length_squared[None, :])
        parameters = np.clip(parameters, 0.0, 1.0)
        closest = starts[None, :, :] + parameters[:, :, None] * directions[None, :, :]
        squared = np.sum((points[:, None, :] - closest) ** 2, axis=2)
        return math.sqrt(float(np.min(squared)))

    return min(point_distances(first, second), point_distances(second, first))


def _endpoint_to_polyline_distance(endpoint: np.ndarray, points: np.ndarray) -> float:
    return min(
        _point_segment_distance(endpoint, start, stop)
        for start, stop in zip(points[:-1], points[1:], strict=True)
    )


def _stroke_clip_evidence(geometry: TattooGeometry) -> dict[str, object]:
    center = np.asarray(geometry.boundary.center_mm, dtype=_ARRAY_DTYPE)
    outer_radius_mm = geometry.boundary.outer_diameter_mm / 2.0
    clip_radius_mm = outer_radius_mm - geometry.boundary.width_mm
    if clip_radius_mm != 63.8:
        raise ValueError("primary tattoo stroke clip radius must be exactly 63.8 mm")

    raw_footprints = [
        float(np.max(np.linalg.norm(path.points_mm - center, axis=1)))
        + path.width_mm / 2.0
        for path in geometry.paths
    ]
    paths_requiring_clipping = [
        path.path_id
        for path, raw_radius in zip(geometry.paths, raw_footprints, strict=True)
        if raw_radius > clip_radius_mm + _NUMERIC_TOLERANCE
    ]
    max_post_clip_stroke_radius_mm = clip_radius_mm
    if max_post_clip_stroke_radius_mm > outer_radius_mm + _NUMERIC_TOLERANCE:
        raise ValueError("clipped stroke footprint escapes the projection boundary")
    return {
        "radius_mm": clip_radius_mm,
        "outer_boundary_radius_mm": outer_radius_mm,
        "raw_rounded_footprint_max_radius_mm": max(raw_footprints),
        "max_post_clip_stroke_radius_mm": max_post_clip_stroke_radius_mm,
        "paths_requiring_clipping": paths_requiring_clipping,
    }


def validate_tattoo_geometry(geometry: TattooGeometry) -> None:
    """Validate the primary open-path and physical-clearance contract."""
    if not isinstance(geometry, TattooGeometry):
        raise TypeError("geometry must be a TattooGeometry")
    if geometry.artboard_size_mm != 145.0:
        raise ValueError("primary tattoo artboard must be exactly 145 mm")
    if len(geometry.paths) != _PATH_COUNT:
        raise ValueError("primary tattoo geometry must contain exactly 11 open polylines")
    if not isinstance(geometry.boundary, TattooBoundary):
        raise ValueError("primary tattoo geometry requires one projection boundary")
    outer_radius = geometry.boundary.outer_diameter_mm / 2.0
    inner_radius = outer_radius - geometry.boundary.width_mm
    center = np.asarray(geometry.boundary.center_mm, dtype=_ARRAY_DTYPE)
    if outer_radius + center[0] != 138.5 or center[0] - outer_radius != 6.5:
        raise ValueError("projection boundary must retain an exact 6.5 mm page margin")
    for path in geometry.paths:
        radii = np.linalg.norm(path.points_mm - center, axis=1)
        if not np.all(radii <= inner_radius + 1e-8):
            raise ValueError("crystallographic path escapes the boundary inner edge")
        if not np.allclose(radii[[0, -1]], inner_radius, rtol=0.0, atol=1e-8):
            raise ValueError("crystallographic path endpoints must meet the inner limb")

    for path in geometry.paths:
        points = np.asarray(path.points_mm, dtype=_ARRAY_DTYPE)
        if float(np.linalg.norm(points[0] - points[-1])) <= _NUMERIC_TOLERANCE:
            raise ValueError(f"{path.member_id} path must be open")
        if np.any(np.linalg.norm(np.diff(points, axis=0), axis=1) <= _NUMERIC_TOLERANCE):
            raise ValueError(f"{path.member_id} has duplicate consecutive points")

    for first_index, first in enumerate(geometry.paths):
        for second in geometry.paths[first_index + 1 :]:
            if _paths_cross(first.points_mm, second.points_mm):
                continue
            centerline_distance = _polyline_distance(first.points_mm, second.points_mm)
            edge_gap = centerline_distance - 0.5 * first.width_mm - 0.5 * second.width_mm
            if edge_gap + _NUMERIC_TOLERANCE < _MIN_EDGE_GAP_MM:
                raise TattooClearanceError(
                    f"noncrossing edge gap {edge_gap:.6f} mm is below "
                    f"{_MIN_EDGE_GAP_MM:.6f} mm between {first.member_id} and "
                    f"{second.member_id}",
                    clearance_kind="noncrossing_edge_gap",
                    member_ids=(first.member_id, second.member_id),
                )

            endpoint_checks = (
                (
                    first.points_mm[0],
                    second.points_mm,
                    second.width_mm,
                    first.member_id,
                    second.member_id,
                ),
                (
                    first.points_mm[-1],
                    second.points_mm,
                    second.width_mm,
                    first.member_id,
                    second.member_id,
                ),
                (
                    second.points_mm[0],
                    first.points_mm,
                    first.width_mm,
                    second.member_id,
                    first.member_id,
                ),
                (
                    second.points_mm[-1],
                    first.points_mm,
                    first.width_mm,
                    second.member_id,
                    first.member_id,
                ),
            )
            for endpoint, unrelated, unrelated_width, owner_id, unrelated_id in endpoint_checks:
                clearance = (
                    _endpoint_to_polyline_distance(endpoint, unrelated) - 0.5 * unrelated_width
                )
                if clearance + _NUMERIC_TOLERANCE < _MIN_ENDPOINT_CLEARANCE_MM:
                    raise TattooClearanceError(
                        f"endpoint clearance {clearance:.6f} mm is below "
                        f"{_MIN_ENDPOINT_CLEARANCE_MM:.6f} mm from {owner_id} to "
                        f"unrelated path {unrelated_id}",
                        clearance_kind="unrelated_endpoint",
                        member_ids=(owner_id, unrelated_id),
                    )

    _stroke_clip_evidence(geometry)


def build_tattoo_geometry(
    selection: TattooSelection,
    recipe: HemisphereSelectionRecipe,
    *,
    width_scale: float = 1.0,
) -> TattooGeometry:
    """Clip selected traces, transform them to millimeters, and validate them."""
    if not isinstance(selection, TattooSelection):
        raise TypeError("selection must be a TattooSelection")
    if not isinstance(recipe, HemisphereSelectionRecipe):
        raise TypeError("recipe must satisfy HemisphereSelectionRecipe")
    if (
        isinstance(width_scale, bool)
        or not isinstance(width_scale, (int, float))
        or float(width_scale) not in (1.0, 1.15)
    ):
        raise ValueError("width_scale must be exactly 1.0 or 1.15")
    width_scale = float(width_scale)
    if selection.recipe_id != recipe.recipe_id:
        raise ValueError("selection recipe_id does not match the tattoo recipe")
    if selection.orientation_id != recipe.orientation.orientation_id:
        raise ValueError("selection orientation_id does not match the tattoo recipe")
    if len(selection.selected_paths) != _PATH_COUNT:
        raise ValueError("tattoo selection must contain exactly 11 paths")
    expected_assignments = tuple(
        assignment
        for tier, count in recipe.path_allocation.items()
        for assignment in zip(
            (tier,) * count,
            recipe.stroke_widths_mm[tier],
            strict=True,
        )
    )
    actual_assignments = tuple((path.tier, path.width_mm) for path in selection.selected_paths)
    if actual_assignments != expected_assignments:
        raise ValueError("ordered tier/width assignments must match the tattoo recipe")

    policy = recipe.projection_boundary
    boundary = TattooBoundary(
        schema_version=1,
        role=str(policy["role"]),
        scientific_claim=str(policy["scientific_claim"]),
        center_mm=(recipe.artboard_size_mm / 2.0,) * 2,
        outer_diameter_mm=float(policy["outer_diameter_mm"]),
        width_mm=float(policy["stroke_width_mm"]),
        ink=str(policy["ink"]),
    )
    inner_radius_mm = boundary.outer_diameter_mm / 2.0 - boundary.width_mm
    scale = inner_radius_mm / recipe.crop_radius
    center = np.asarray(boundary.center_mm, dtype=_ARRAY_DTYPE)
    paths: list[TattooPath] = []
    for selected in selection.selected_paths:
        fragments = _clip_polyline_to_circle(
            selected.center_trace,
            recipe.crop_radius,
        )
        if len(fragments) != 1:
            raise ValueError(
                f"selected path {selected.member_id} has {len(fragments)} interior "
                "crop fragments; exactly one is required"
            )
        points_mm = center + scale * fragments[0]
        points_mm[np.isclose(points_mm, 0.0, rtol=0.0, atol=_NUMERIC_TOLERANCE)] = 0.0
        points_mm[
            np.isclose(
                points_mm,
                recipe.artboard_size_mm,
                rtol=0.0,
                atol=_NUMERIC_TOLERANCE,
            )
        ] = recipe.artboard_size_mm
        paths.append(
            TattooPath(
                member_id=selected.member_id,
                tier=selected.tier,
                width_mm=selected.width_mm * width_scale,
                points_mm=points_mm,
                score_components=selected.score_components,
                selection_reason=selected.selection_reason,
            )
        )

    geometry = TattooGeometry(
        schema_version=1,
        catalog_id=selection.catalog_id,
        orientation_id=selection.orientation_id,
        artboard_size_mm=recipe.artboard_size_mm,
        boundary=boundary,
        paths=tuple(paths),
        projection=_PROJECTION,
    )
    validate_tattoo_geometry(geometry)
    return geometry


def primary_svg_bytes(geometry: TattooGeometry) -> bytes:
    """Serialize the validated primary line network as deterministic SVG bytes."""
    validate_tattoo_geometry(geometry)
    size = f"{geometry.artboard_size_mm:.6f}"
    lines = [
        f'<svg height="{size}mm" version="1.1" viewBox="0 0 {size} {size}" '
        f'width="{size}mm" xmlns="http://www.w3.org/2000/svg">'
    ]
    center_x, center_y = geometry.boundary.center_mm
    clip_radius_mm = (
        geometry.boundary.outer_diameter_mm / 2.0 - geometry.boundary.width_mm
    )
    lines.extend(
        (
            "  <defs>",
            f'    <clipPath clipPathUnits="userSpaceOnUse" id="{_STROKE_CLIP_ID}">',
            f'      <circle cx="{center_x:.6f}" cy="{center_y:.6f}" '
            f'r="{clip_radius_mm:.6f}"/>',
            "    </clipPath>",
            "  </defs>",
        )
    )
    for path in geometry.paths:
        coordinates = [f"{point[0]:.6f} {point[1]:.6f}" for point in path.points_mm]
        path_data = "M " + coordinates[0]
        if len(coordinates) > 1:
            path_data += " " + " ".join(f"L {value}" for value in coordinates[1:])
        lines.append(
            f'  <path clip-path="url(#{_STROKE_CLIP_ID})" d="{path_data}" '
            f'fill="none" id="{path.path_id}" '
            f'stroke="#000000" stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-width="{path.width_mm:.6f}"/>'
        )
    centerline_radius = (
        geometry.boundary.outer_diameter_mm - geometry.boundary.width_mm
    ) / 2.0
    lines.append(
        f'  <circle cx="{center_x:.6f}" cy="{center_y:.6f}" fill="none" '
        f'id="{geometry.boundary.boundary_id}" r="{centerline_radius:.6f}" '
        f'stroke="{geometry.boundary.ink}" '
        f'stroke-width="{geometry.boundary.width_mm:.6f}"/>'
    )
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _primary_pdf_bytes(geometry: TattooGeometry) -> bytes:
    size_inches = geometry.artboard_size_mm / _MILLIMETERS_PER_INCH
    figure = Figure(figsize=(size_inches, size_inches), frameon=False)
    canvas = FigureCanvasPdf(figure)
    axis = figure.add_axes((0.0, 0.0, 1.0, 1.0), frameon=False)
    axis.set_xlim(0.0, geometry.artboard_size_mm)
    axis.set_ylim(geometry.artboard_size_mm, 0.0)
    axis.set_aspect("equal", adjustable="box")
    axis.set_axis_off()
    clip_radius_mm = (
        geometry.boundary.outer_diameter_mm / 2.0 - geometry.boundary.width_mm
    )
    stroke_clip = Circle(
        geometry.boundary.center_mm,
        radius=clip_radius_mm,
        transform=axis.transData,
    )
    for path in geometry.paths:
        line = Line2D(
            path.points_mm[:, 0],
            path.points_mm[:, 1],
            color="#000000",
            linewidth=path.width_mm * _POINTS_PER_INCH / _MILLIMETERS_PER_INCH,
            solid_capstyle="round",
            solid_joinstyle="round",
        )
        line.set_clip_path(stroke_clip)
        axis.add_line(line)
    axis.add_patch(
        Circle(
            geometry.boundary.center_mm,
            radius=(
                geometry.boundary.outer_diameter_mm - geometry.boundary.width_mm
            )
            / 2.0,
            fill=False,
            edgecolor=geometry.boundary.ink,
            linewidth=(
                geometry.boundary.width_mm
                * _POINTS_PER_INCH
                / _MILLIMETERS_PER_INCH
            ),
            zorder=3,
        )
    )

    payload = BytesIO()
    with matplotlib.rc_context({"pdf.compression": 0}):
        canvas.print_pdf(
            payload,
            metadata={
                "Creator": "kikuchi-lab",
                "CreationDate": None,
                "ModDate": None,
            },
        )
    figure.clear()
    return payload.getvalue()


def _primary_png_bytes(geometry: TattooGeometry, *, background: str) -> bytes:
    image = Image.new("RGB", (_PNG_SIZE_PX, _PNG_SIZE_PX), background)
    band_layer = Image.new("L", (_PNG_SIZE_PX, _PNG_SIZE_PX), 0)
    draw_bands = ImageDraw.Draw(band_layer)
    scale = _PNG_SIZE_PX / geometry.artboard_size_mm
    for path in geometry.paths:
        points = [tuple(float(value) * scale for value in point) for point in path.points_mm]
        width_px = max(1, round(path.width_mm * scale))
        draw_bands.line(points, fill=255, width=width_px, joint="curve")
        radius = width_px / 2.0
        for point in points:
            draw_bands.ellipse(
                (
                    point[0] - radius,
                    point[1] - radius,
                    point[0] + radius,
                    point[1] + radius,
                ),
                fill=255,
            )
    center_x, center_y = geometry.boundary.center_mm
    clip_radius_mm = (
        geometry.boundary.outer_diameter_mm / 2.0 - geometry.boundary.width_mm
    )
    circular_mask = Image.new("L", (_PNG_SIZE_PX, _PNG_SIZE_PX), 0)
    ImageDraw.Draw(circular_mask).ellipse(
        (
            (center_x - clip_radius_mm) * scale,
            (center_y - clip_radius_mm) * scale,
            (center_x + clip_radius_mm) * scale,
            (center_y + clip_radius_mm) * scale,
        ),
        fill=255,
    )
    clipped_bands = ImageChops.multiply(band_layer, circular_mask)
    image.paste((0, 0, 0), mask=clipped_bands)

    outer_radius_mm = geometry.boundary.outer_diameter_mm / 2.0
    boundary_layer = Image.new("L", (_PNG_SIZE_PX, _PNG_SIZE_PX), 0)
    ImageDraw.Draw(boundary_layer).ellipse(
        (
            (center_x - outer_radius_mm) * scale,
            (center_y - outer_radius_mm) * scale,
            (center_x + outer_radius_mm) * scale,
            (center_y + outer_radius_mm) * scale,
        ),
        outline=255,
        width=round(geometry.boundary.width_mm * scale),
    )
    half_pixel_diagonal_mm = math.sqrt(2.0) / (2.0 * scale)
    pixel_centers_mm = (np.arange(_PNG_SIZE_PX, dtype=np.float64) + 0.5) / scale
    x_distance_squared = (pixel_centers_mm - center_x) ** 2
    y_distance_squared = (pixel_centers_mm - center_y) ** 2
    within_outer_disc = (
        y_distance_squared[:, None] + x_distance_squared[None, :]
        <= (outer_radius_mm + half_pixel_diagonal_mm) ** 2
    )
    bounded_boundary = Image.fromarray(
        np.where(within_outer_disc, np.asarray(boundary_layer), 0).astype(np.uint8)
    )
    image.paste((0, 0, 0), mask=bounded_boundary)

    payload = BytesIO()
    image.save(
        payload,
        format="PNG",
        compress_level=9,
        optimize=False,
        dpi=(_PNG_DPI, _PNG_DPI),
    )
    return payload.getvalue()


def render_primary_tattoo(geometry: TattooGeometry) -> Mapping[str, bytes]:
    """Render the canonical primary SVG plus deterministic PDF and PNG derivatives."""
    validate_tattoo_geometry(geometry)
    rendered = {
        "primary.svg": primary_svg_bytes(geometry),
        "primary.pdf": _primary_pdf_bytes(geometry),
        "mockup.png": _primary_png_bytes(geometry, background=_MOCKUP_BACKGROUND),
        "stencil.png": _primary_png_bytes(geometry, background=_STENCIL_BACKGROUND),
    }
    return MappingProxyType(rendered)


__all__ = [
    "TattooClearanceError",
    "build_tattoo_geometry",
    "primary_svg_bytes",
    "render_primary_tattoo",
    "validate_tattoo_geometry",
]

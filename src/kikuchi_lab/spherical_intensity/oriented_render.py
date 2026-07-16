"""Deterministic field-led hemisphere, sphere, and orientation figures."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from io import BytesIO
from types import MappingProxyType

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from PIL import Image

from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)

from .orientation import (
    OrientedProfile,
    OrientedSphericalRecipe,
    orientation_matrix,
)
from .presentation import PresentationSource, evaluate_presentation
from .reprojection import inverse_rotate_directions, stereographic_grid_rows


_DPI = 100
_FIGURES = {
    "identity-vs-oriented-upper.png",
    "oriented-upper.png",
    "oriented-lower.png",
    "oriented-sphere-front.png",
    "oriented-sphere-rear.png",
    "orientation-axes.png",
}
_PNG_METADATA = {
    "Software": "kikuchi-lab deterministic oriented-spherical renderer",
    "Creation Time": "1970-01-01T00:00:00Z",
}
_SPHERE_CAMERAS = (
    (20.0, -65.0),
    (-20.0, 115.0),
)
_AXIS_LABELS = (
    "RD",
    "TD",
    "ND",
    "G_cs[100]",
    "G_cs[010]",
    "G_cs[001]",
)


@dataclass(frozen=True)
class OrientedSphericalRender:
    """Project-owned canonical PNG payloads and their render ledger."""

    figures: Mapping[str, bytes]
    ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.figures, Mapping):
            raise TypeError("oriented render figures must be a mapping")
        figures = dict(self.figures)
        if set(figures) != _FIGURES:
            raise ValueError("oriented render figure inventory is not canonical")
        if any(not isinstance(payload, bytes) for payload in figures.values()):
            raise TypeError("oriented render figure payloads must be bytes")
        if not isinstance(self.ledger, Mapping):
            raise TypeError("oriented render ledger must be a mapping")
        object.__setattr__(self, "figures", MappingProxyType(figures))
        object.__setattr__(self, "ledger", MappingProxyType(dict(self.ledger)))


def _presentation_hemisphere(
    source: PresentationSource,
    orientation: Orientation,
    *,
    hemisphere: str,
    size: int,
    tile_rows: int,
    check_deadline: Callable[[], None],
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate one specimen hemisphere without retaining a full direction cube."""
    if not isinstance(source, PresentationSource):
        raise TypeError("source must be a PresentationSource")
    if not isinstance(orientation, Orientation):
        raise TypeError("orientation must be an Orientation")
    if hemisphere not in {"upper", "lower"}:
        raise ValueError("stereographic hemisphere must be upper or lower")
    if type(size) is not int or size < 2:
        raise ValueError("hemisphere size must be an integer of at least 2")
    if type(tile_rows) is not int or not 1 <= tile_rows <= size:
        raise ValueError("tile_rows must be an integer within the output grid")
    if not callable(check_deadline):
        raise TypeError("check_deadline must be callable")

    values = np.zeros((size, size), dtype=np.float32)
    valid = np.zeros((size, size), dtype=bool)
    identity_source_grid = (
        orientation.euler_bunge_deg == (0.0, 0.0, 0.0)
        and hemisphere == "upper"
        and source.toned_master.shape[-1] == size
    )
    source_offset = 0

    for row_start in range(0, size, tile_rows):
        check_deadline()
        row_stop = min(row_start + tile_rows, size)
        tile_values = values[row_start:row_stop]

        if identity_source_grid:
            tile_valid = source.upper_valid[row_start:row_stop]
            count = int(np.count_nonzero(tile_valid))
            crystal = source.upper_directions[source_offset : source_offset + count]
            source_offset += count
        else:
            grid = stereographic_grid_rows(
                size,
                hemisphere,
                row_start,
                row_stop,
            )
            tile_valid = grid.valid
            crystal = inverse_rotate_directions(grid.directions[tile_valid], orientation)

        valid[row_start:row_stop] = tile_valid
        tile_values[tile_valid] = evaluate_presentation(source, crystal)

    if identity_source_grid and source_offset != source.upper_directions.shape[0]:
        raise ValueError("identity source-grid traversal did not consume every direction")
    return values, valid


def _hemisphere_png(
    values: np.ndarray,
    valid: np.ndarray,
    *,
    size_px: int,
    background: str,
) -> bytes:
    """Render a nearest-neighbor stereographic field with only its circular rim."""
    field = np.asarray(values)
    mask = np.asarray(valid)
    if field.ndim != 2 or field.shape[0] != field.shape[1] or field.shape != mask.shape:
        raise ValueError("hemisphere values and validity must be equally sized square arrays")
    if mask.dtype != np.dtype(bool) or not np.isfinite(field).all():
        raise ValueError("hemisphere values must be finite and validity must be boolean")

    figure, axis = plt.subplots(
        figsize=(size_px / _DPI, size_px / _DPI),
        dpi=_DPI,
    )
    figure.patch.set_facecolor(background)
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_facecolor(background)
    axis.imshow(
        np.ma.array(field, mask=~mask),
        origin="lower",
        extent=(-1.0, 1.0, -1.0, 1.0),
        interpolation="nearest",
        cmap=colormaps["gray"].with_extremes(bad=background),
        vmin=0.0,
        vmax=1.0,
    )
    axis.add_patch(
        Circle(
            (0.0, 0.0),
            1.0,
            fill=False,
            edgecolor="#d7e0e5",
            linewidth=0.8,
        )
    )
    axis.set_xlim(-1.025, 1.025)
    axis.set_ylim(-1.025, 1.025)
    axis.set_aspect("equal")
    axis.set_axis_off()
    output = BytesIO()
    figure.savefig(
        output,
        format="png",
        dpi=_DPI,
        facecolor=background,
        metadata=_PNG_METADATA,
    )
    plt.close(figure)
    return output.getvalue()


def _save_figure_png(
    figure: Figure,
    *,
    size_px: int,
    background: str,
) -> bytes:
    figure.set_size_inches(size_px / _DPI, size_px / _DPI, forward=True)
    figure.patch.set_facecolor(background)
    output = BytesIO()
    figure.savefig(
        output,
        format="png",
        dpi=_DPI,
        facecolor=background,
        metadata=_PNG_METADATA,
    )
    plt.close(figure)
    return output.getvalue()


def _join_horizontal(left: bytes, right: bytes, background: str) -> bytes:
    with Image.open(BytesIO(left)) as left_source:
        left_image = left_source.convert("RGBA")
    with Image.open(BytesIO(right)) as right_source:
        right_image = right_source.convert("RGBA")
    if left_image.size != right_image.size:
        raise ValueError("comparison images must have identical sizes")
    canvas = Image.new(
        "RGBA",
        (2 * left_image.width, left_image.height),
        background,
    )
    canvas.paste(left_image, (0, 0))
    canvas.paste(right_image, (left_image.width, 0))
    output = BytesIO()
    canvas.save(output, format="PNG", compress_level=9)
    return output.getvalue()


def _sphere_png(
    source: PresentationSource,
    orientation: Orientation,
    profile: OrientedProfile,
    *,
    elev: float,
    azim: float,
    background: str,
) -> bytes:
    longitude = np.linspace(-np.pi, np.pi, profile.sphere_longitude_count)
    latitude = np.linspace(
        -np.pi / 2.0,
        np.pi / 2.0,
        profile.sphere_latitude_count,
    )
    lon, lat = np.meshgrid(longitude, latitude)
    specimen_x = np.cos(lat) * np.cos(lon)
    specimen_y = np.cos(lat) * np.sin(lon)
    specimen_z = np.sin(lat)
    specimen = np.stack([specimen_x, specimen_y, specimen_z], axis=-1)
    crystal = inverse_rotate_directions(specimen.reshape(-1, 3), orientation)
    luminance = evaluate_presentation(source, crystal).reshape(specimen_x.shape)
    gray_facecolors = colormaps["gray"](luminance)

    figure = plt.figure(
        figsize=(profile.figure_size_px / _DPI, profile.figure_size_px / _DPI),
        dpi=_DPI,
    )
    figure.patch.set_facecolor(background)
    axis = figure.add_subplot(111, projection="3d")
    axis.plot_surface(
        specimen_x,
        specimen_y,
        specimen_z,
        facecolors=gray_facecolors,
        rcount=profile.sphere_latitude_count,
        ccount=profile.sphere_longitude_count,
        shade=False,
        antialiased=False,
        linewidth=0.0,
    )
    axis.view_init(elev=elev, azim=azim)
    axis.set_proj_type("ortho")
    axis.set_xlim(-1.02, 1.02)
    axis.set_ylim(-1.02, 1.02)
    axis.set_zlim(-1.02, 1.02)
    axis.set_box_aspect((1.0, 1.0, 1.0))
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_axis_off()
    axis.set_facecolor(background)
    return _save_figure_png(
        figure,
        size_px=profile.figure_size_px,
        background=background,
    )


def _axis_endpoints(
    orientation: Orientation,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Return specimen basis and adapter-owned transformed crystal basis."""
    specimen_axes = {
        "RD": np.array([1.0, 0.0, 0.0]),
        "TD": np.array([0.0, 1.0, 0.0]),
        "ND": np.array([0.0, 0.0, 1.0]),
    }
    crystal_axes = {
        "G_cs[100]": transform_crystal_direction_to_sample(
            [1.0, 0.0, 0.0],
            orientation,
        ),
        "G_cs[010]": transform_crystal_direction_to_sample(
            [0.0, 1.0, 0.0],
            orientation,
        ),
        "G_cs[001]": transform_crystal_direction_to_sample(
            [0.0, 0.0, 1.0],
            orientation,
        ),
    }
    if not np.allclose(
        np.column_stack(tuple(crystal_axes.values())),
        orientation_matrix(orientation),
        rtol=0.0,
        atol=5e-13,
    ):
        raise ValueError("axis diagnostic disagrees with orientation matrix")
    return specimen_axes, crystal_axes


def _axis_png(
    orientation: Orientation,
    *,
    size_px: int,
    background: str,
) -> bytes:
    specimen_axes, crystal_axes = _axis_endpoints(orientation)
    figure = plt.figure(
        figsize=(size_px / _DPI, size_px / _DPI),
        dpi=_DPI,
    )
    figure.patch.set_facecolor(background)
    axis = figure.add_subplot(111, projection="3d")

    longitude = np.linspace(-np.pi, np.pi, 25)
    latitude = np.linspace(-np.pi / 2.0, np.pi / 2.0, 13)
    lon, lat = np.meshgrid(longitude, latitude)
    axis.plot_wireframe(
        np.cos(lat) * np.cos(lon),
        np.cos(lat) * np.sin(lon),
        np.sin(lat),
        rcount=latitude.size,
        ccount=longitude.size,
        color="#53626b",
        linewidth=0.35,
        alpha=0.36,
    )
    for label, endpoint in specimen_axes.items():
        axis.quiver(0, 0, 0, *endpoint, color="#e4edf2", linewidth=1.4)
        axis.text(*endpoint, label, color="#e4edf2")
    for label, endpoint in crystal_axes.items():
        axis.quiver(0, 0, 0, *endpoint, color="#8cc9ff", linewidth=1.2)
        axis.text(*endpoint, label, color="#8cc9ff")
    axis.view_init(elev=20.0, azim=-65.0)
    axis.set_proj_type("ortho")
    axis.set_xlim(-1.05, 1.05)
    axis.set_ylim(-1.05, 1.05)
    axis.set_zlim(-1.05, 1.05)
    axis.set_box_aspect((1.0, 1.0, 1.0))
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_axis_off()
    axis.set_facecolor(background)
    return _save_figure_png(figure, size_px=size_px, background=background)


def _validate_art_contract(source: PresentationSource) -> None:
    expected = {
        "spatial_filter": "none",
        "center_overlay": False,
        "boundary_overlay": False,
    }
    if any(source.ledger.get(name) != value for name, value in expected.items()):
        raise ValueError("presentation source art contract requires no filters or overlays")


def render_oriented_spherical(
    source: PresentationSource,
    recipe: OrientedSphericalRecipe,
    *,
    check_deadline: Callable[[], None] | None = None,
) -> OrientedSphericalRender:
    """Render all canonical specimen-frame derivatives from one presentation source."""
    if not isinstance(source, PresentationSource):
        raise TypeError("source must be a PresentationSource")
    if not isinstance(recipe, OrientedSphericalRecipe):
        raise TypeError("recipe must be an OrientedSphericalRecipe")
    if check_deadline is not None and not callable(check_deadline):
        raise TypeError("check_deadline must be callable")
    _validate_art_contract(source)

    check = check_deadline if check_deadline is not None else lambda: None
    profile = recipe.profile
    identity = Orientation((0.0, 0.0, 0.0))
    identity_upper, identity_valid = _presentation_hemisphere(
        source,
        identity,
        hemisphere="upper",
        size=profile.figure_size_px,
        tile_rows=profile.tile_rows,
        check_deadline=check,
    )
    oriented_upper, upper_valid = _presentation_hemisphere(
        source,
        recipe.orientation,
        hemisphere="upper",
        size=profile.figure_size_px,
        tile_rows=profile.tile_rows,
        check_deadline=check,
    )
    oriented_lower, lower_valid = _presentation_hemisphere(
        source,
        recipe.orientation,
        hemisphere="lower",
        size=profile.figure_size_px,
        tile_rows=profile.tile_rows,
        check_deadline=check,
    )

    check()
    identity_png = _hemisphere_png(
        identity_upper,
        identity_valid,
        size_px=profile.figure_size_px,
        background=recipe.background_color,
    )
    check()
    upper_png = _hemisphere_png(
        oriented_upper,
        upper_valid,
        size_px=profile.figure_size_px,
        background=recipe.background_color,
    )
    check()
    lower_png = _hemisphere_png(
        oriented_lower,
        lower_valid,
        size_px=profile.figure_size_px,
        background=recipe.background_color,
    )
    check()
    comparison_png = _join_horizontal(
        identity_png,
        upper_png,
        recipe.background_color,
    )
    check()
    front_png = _sphere_png(
        source,
        recipe.orientation,
        profile,
        elev=_SPHERE_CAMERAS[0][0],
        azim=_SPHERE_CAMERAS[0][1],
        background=recipe.background_color,
    )
    check()
    rear_png = _sphere_png(
        source,
        recipe.orientation,
        profile,
        elev=_SPHERE_CAMERAS[1][0],
        azim=_SPHERE_CAMERAS[1][1],
        background=recipe.background_color,
    )
    check()
    axis_png = _axis_png(
        recipe.orientation,
        size_px=profile.figure_size_px,
        background=recipe.background_color,
    )

    figures = {
        "identity-vs-oriented-upper.png": comparison_png,
        "oriented-upper.png": upper_png,
        "oriented-lower.png": lower_png,
        "oriented-sphere-front.png": front_png,
        "oriented-sphere-rear.png": rear_png,
        "orientation-axes.png": axis_png,
    }
    ledger = {
        "schema_version": 1,
        "orientation_id": recipe.orientation.orientation_id,
        "figure_size_px": profile.figure_size_px,
        "sphere_cameras": [
            {"elevation_deg": elevation, "azimuth_deg": azimuth}
            for elevation, azimuth in _SPHERE_CAMERAS
        ],
        "sphere_mesh": {
            "latitude_count": profile.sphere_latitude_count,
            "longitude_count": profile.sphere_longitude_count,
            "surface_rcount": profile.sphere_latitude_count,
            "surface_ccount": profile.sphere_longitude_count,
            "sampling": "full_grid_no_reduction",
        },
        "hemisphere_tile_rows": profile.tile_rows,
        "hemisphere_direction_tile_shape_upper_bound": [
            profile.tile_rows,
            profile.figure_size_px,
            3,
        ],
        "hemisphere_direction_cube_retained": False,
        "raster_interpolation": "nearest",
        "field_interpolation": "bilinear",
        "spatial_filter": "none",
        "image_rotation": False,
        "center_overlay": False,
        "boundary_overlay": False,
        "display_boundary": "circular_rim_only",
        "annotated_figures": ["orientation-axes.png"],
        "axis_labels": list(_AXIS_LABELS),
    }
    return OrientedSphericalRender(figures=figures, ledger=ledger)


__all__ = ["OrientedSphericalRender", "render_oriented_spherical"]

"""Deterministic crisp rendering of additional overlap and stepped vector relief."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import version
from io import BytesIO
from types import MappingProxyType

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from kikuchipy.simulations import KikuchiPatternSimulator
from matplotlib import colormaps
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from PIL import Image

from kikuchi_lab.kinematical.contracts import KinematicalRecipe, KinematicalSimulation
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _KikuchipyContext,
    _select_reflectors,
)
from kikuchi_lab.kinematical.render import asinh_tone_map

from .contracts import NearDepthTreatmentRecipe, StrokeStyle
from .overlap import OverlapField, apply_optical_depth


_DPI = 100
_PNG_METADATA = {
    "Software": "kikuchi-lab deterministic near-depth renderer",
    "Creation Time": "1970-01-01T00:00:00Z",
}
_CENTER_COLOR = (0.94, 0.97, 1.0)
_CENTER_CASING = (0.035, 0.047, 0.054)
_BOUNDARY_COLOR = (0.10, 0.12, 0.13)
_BOUNDARY_CASING = (0.015, 0.021, 0.024)


@dataclass(frozen=True)
class NearDepthRender:
    """Project-owned render payloads and their plain provenance ledger."""

    figures: Mapping[str, bytes]
    diagnostic_png: bytes
    ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        figures = dict(self.figures)
        expected = {
            "etched-master-near-depth-stepped.png",
            "quiet-vs-near-depth-stepped.png",
        }
        if set(figures) != expected or any(
            not isinstance(payload, bytes) for payload in figures.values()
        ):
            raise ValueError("near-depth render figure inventory is not canonical")
        if not isinstance(self.diagnostic_png, bytes):
            raise TypeError("near-depth diagnostic PNG must be bytes")
        object.__setattr__(self, "figures", MappingProxyType(figures))
        object.__setattr__(self, "ledger", MappingProxyType(dict(self.ledger)))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    return hashlib.sha256(value.tobytes(order="C")).hexdigest()


def _prepare_axis(*, size_px: int, background: str) -> tuple[Figure, Axes]:
    figure, axis = plt.subplots()
    figure.set_layout_engine("tight")
    figure.patch.set_facecolor(background)
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_xlim(-1.025, 1.025)
    axis.set_ylim(-1.025, 1.025)
    axis.set_aspect("equal")
    axis.set_facecolor(background)
    axis.set_axis_off()
    return figure, axis


def _save_png(figure: Figure, *, size_px: int, background: str) -> bytes:
    figure.set_size_inches(size_px / _DPI, size_px / _DPI, forward=True)
    figure.patch.set_facecolor(background)
    payload = BytesIO()
    figure.savefig(
        payload,
        format="png",
        dpi=_DPI,
        facecolor=background,
        metadata=_PNG_METADATA,
    )
    plt.close(figure)
    return payload.getvalue()


def _gray_cmap(background: str):
    return colormaps["gray"].with_extremes(bad=background)


def _insert_field(
    axis: Axes,
    field: np.ma.MaskedArray,
    *,
    background: str,
    rim: bool,
) -> None:
    axis.imshow(
        field,
        extent=(-1, 1, -1, 1),
        origin="lower",
        interpolation="nearest",
        cmap=_gray_cmap(background),
        vmin=0.0,
        vmax=1.0,
        zorder=-10,
    )
    if rim:
        axis.add_patch(
            Circle(
                (0.0, 0.0),
                1.0,
                fill=False,
                edgecolor=(0.84, 0.88, 0.90, 0.88),
                linewidth=1.0,
                zorder=20,
            )
        )


def _draw_paths(
    axis: Axes,
    simulator: KikuchiPatternSimulator,
    *,
    mode: str,
    style: StrokeStyle,
    color: tuple[float, float, float],
    casing_color: tuple[float, float, float],
    zorder: int,
) -> int:
    """Copy exact public kikuchipy path coordinates onto the final-size axis."""
    source_figure = simulator.plot(
        projection="stereographic",
        mode=mode,
        hemisphere="upper",
        scaling="linear",
        return_figure=True,
        backend="matplotlib",
        color=(*color, style.alpha),
        linewidth=style.width_pt,
    )
    source_lines = tuple(source_figure.axes[0].lines)
    for source in source_lines:
        (line,) = axis.plot(
            np.asarray(source.get_xdata(), dtype=np.float64),
            np.asarray(source.get_ydata(), dtype=np.float64),
            color=(*color, style.alpha),
            linewidth=style.width_pt,
            antialiased=True,
            solid_capstyle="round",
            zorder=zorder,
        )
        line.set_path_effects(
            [
                path_effects.Stroke(
                    linewidth=style.casing_width_pt,
                    foreground=(*casing_color, style.casing_alpha),
                ),
                path_effects.Normal(),
            ]
        )
    plt.close(source_figure)
    return len(source_lines)


def _comparison_png(
    quiet_payload: bytes,
    depth_payload: bytes,
    *,
    size_px: int,
    background: str,
) -> bytes:
    with Image.open(BytesIO(quiet_payload)) as quiet_source:
        quiet = quiet_source.convert("RGBA")
    with Image.open(BytesIO(depth_payload)) as depth_source:
        depth = depth_source.convert("RGBA")
    expected = (size_px, size_px)
    if quiet.size != expected or depth.size != expected:
        raise ValueError("quiet and near-depth figures must match the final canvas size")
    canvas = Image.new("RGBA", (2 * size_px, size_px), background)
    canvas.paste(quiet, (0, 0))
    canvas.paste(depth, (size_px, 0))
    payload = BytesIO()
    canvas.save(payload, format="PNG", compress_level=9)
    return payload.getvalue()


def _masked(array: np.ndarray, valid: np.ndarray) -> np.ma.MaskedArray:
    return np.ma.array(array, mask=~valid)


def render_near_depth(
    context: _KikuchipyContext,
    simulation: KinematicalSimulation,
    base_recipe: KinematicalRecipe,
    treatment: NearDepthTreatmentRecipe,
    overlap: OverlapField,
    quiet_payload: bytes,
    *,
    figure_size_px: int | None = None,
) -> NearDepthRender:
    """Render one exact, presentation-only near-depth derivative."""
    effective_size = treatment.figure_size_px if figure_size_px is None else figure_size_px
    if type(effective_size) is not int or effective_size <= 0:
        raise ValueError("near-depth figure size must be a positive integer")
    master = np.asarray(simulation.master_stereographic.intensity)
    if master.ndim != 3 or master.shape[0] < 1 or master.shape[-2:] != overlap.raw.shape:
        raise ValueError("near-depth overlap grid must match the stereographic master")
    base = asinh_tone_map(
        master[0],
        percentiles=base_recipe.tone_percentiles,
        scale=base_recipe.tone_asinh_scale,
    )
    depth = apply_optical_depth(
        base,
        overlap.normalized,
        gain=treatment.optical_depth_gain,
        luminance_ceiling=treatment.luminance_ceiling,
    )

    all_reflectors = context.master_simulator.reflectors
    boundary_reflectors = _select_reflectors(
        all_reflectors,
        treatment.boundary.relative_factor,
        base_recipe.energy_kev,
    )
    center_reflectors = _select_reflectors(
        all_reflectors,
        treatment.center.relative_factor,
        base_recipe.energy_kev,
    )
    figure, axis = _prepare_axis(
        size_px=effective_size,
        background=treatment.background_color,
    )
    _insert_field(
        axis,
        _masked(depth, overlap.valid_disk),
        background=treatment.background_color,
        rim=False,
    )
    boundary_path_count = _draw_paths(
        axis,
        KikuchiPatternSimulator(boundary_reflectors),
        mode="bands",
        style=treatment.boundary,
        color=_BOUNDARY_COLOR,
        casing_color=_BOUNDARY_CASING,
        zorder=5,
    )
    center_path_count = _draw_paths(
        axis,
        KikuchiPatternSimulator(center_reflectors),
        mode="lines",
        style=treatment.center,
        color=_CENTER_COLOR,
        casing_color=_CENTER_CASING,
        zorder=10,
    )
    axis.add_patch(
        Circle(
            (0.0, 0.0),
            1.0,
            fill=False,
            edgecolor=(0.84, 0.88, 0.90, 0.88),
            linewidth=1.0,
            zorder=20,
        )
    )
    depth_payload = _save_png(
        figure,
        size_px=effective_size,
        background=treatment.background_color,
    )

    diagnostic_figure, diagnostic_axis = _prepare_axis(
        size_px=effective_size,
        background=treatment.background_color,
    )
    _insert_field(
        diagnostic_axis,
        _masked(overlap.normalized, overlap.valid_disk),
        background=treatment.background_color,
        rim=True,
    )
    diagnostic_payload = _save_png(
        diagnostic_figure,
        size_px=effective_size,
        background=treatment.background_color,
    )
    figures = {
        "etched-master-near-depth-stepped.png": depth_payload,
        "quiet-vs-near-depth-stepped.png": _comparison_png(
            quiet_payload,
            depth_payload,
            size_px=effective_size,
            background=treatment.background_color,
        ),
    }
    ledger = {
        "schema_version": 1,
        "scientific_claim": "presentation_only",
        "source_id": simulation.master_stereographic.metadata["source_id"],
        "source_sha256": simulation.master_stereographic.metadata["source_sha256"],
        "base_recipe_id": base_recipe.recipe_id,
        "base_stereographic_product_id": simulation.master_stereographic.product_id,
        "base_stereographic_array_sha256": (
            simulation.master_stereographic.array_sha256
        ),
        "base_quiet_png_sha256": _sha256_bytes(quiet_payload),
        "treatment_recipe_id": treatment.recipe_id,
        "projection": "upper stereographic square grid",
        "frame": simulation.projection_ledger["frames"]["crystal"],
        "spatial_filter": "none",
        "interpolation": "nearest",
        "overlap": {
            **dict(overlap.metadata),
            "raw_array_sha256": _sha256_array(overlap.raw),
            "normalized_array_sha256": _sha256_array(overlap.normalized),
        },
        "optical_depth": {
            "equation": (
                "L_max * (1 - exp(-(-log(1 - B/L_max) + gain * "
                "overlap_normalized)))"
            ),
            "gain": treatment.optical_depth_gain,
            "luminance_ceiling": treatment.luminance_ceiling,
            "zero_overlap_rule": "output luminance equals base luminance exactly",
        },
        "vector_layers": {
            "boundary": {
                "mode": "bands",
                **treatment.boundary.to_dict(),
                "signed_reflector_count": int(boundary_reflectors.size),
                "path_count": boundary_path_count,
                "geometry_owner": "kikuchipy.KikuchiPatternSimulator.plot",
                "path_displacement": "none",
            },
            "center": {
                "mode": "lines",
                **treatment.center.to_dict(),
                "signed_reflector_count": int(center_reflectors.size),
                "path_count": center_path_count,
                "geometry_owner": "kikuchipy.KikuchiPatternSimulator.plot",
                "path_displacement": "none",
            },
        },
        "figure_size_px": effective_size,
        "renderer_versions": {
            package: version(package)
            for package in ("kikuchipy", "matplotlib", "numpy", "pillow")
        },
        "output_sha256": {
            **{name: _sha256_bytes(payload) for name, payload in figures.items()},
            "overlap-additional-depth.png": _sha256_bytes(diagnostic_payload),
        },
    }
    return NearDepthRender(
        figures=figures,
        diagnostic_png=diagnostic_payload,
        ledger=ledger,
    )


def render_quiet_control(
    context: _KikuchipyContext,
    simulation: KinematicalSimulation,
    base_recipe: KinematicalRecipe,
    *,
    figure_size_px: int,
) -> bytes:
    """Render only the existing promoted quiet control with its original code path."""
    from kikuchi_lab.kinematical.render import (
        _etched_figure,
        _save_png as _save_kinematical_png,
        circular_stereographic_field,
    )

    if type(figure_size_px) is not int or figure_size_px <= 0:
        raise ValueError("quiet control figure size must be a positive integer")
    try:
        style = next(item for item in base_recipe.styles if item.name == "quiet")
    except StopIteration:
        raise ValueError("base kinematical recipe does not define the quiet style") from None
    upper = simulation.master_stereographic.intensity[0]
    toned = asinh_tone_map(
        upper,
        percentiles=base_recipe.tone_percentiles,
        scale=base_recipe.tone_asinh_scale,
    )
    field = circular_stereographic_field(toned)
    return _save_kinematical_png(
        _etched_figure(context, style, field),
        size_px=figure_size_px,
    )


__all__ = ["NearDepthRender", "render_near_depth", "render_quiet_control"]

"""Deterministic, no-blur rendering for kinematical reference products."""

from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from PIL import Image

from .contracts import EtchedMasterStyle, KinematicalRecipe, KinematicalSimulation
from .kikuchipy_adapter import _KikuchipyContext, _SPHERICAL_CAMERA_DEG


_DPI = 100
_BACKGROUND = "#101519"
_TRACE_COLOR = (0.94, 0.97, 1.0)
_PNG_METADATA = {
    "Software": "kikuchi-lab deterministic matplotlib renderer",
    "Creation Time": "1970-01-01T00:00:00Z",
}


def asinh_tone_map(
    image: np.ndarray, *, percentiles: tuple[float, float], scale: float
) -> np.ndarray:
    """Apply a monotonic pointwise asinh curve without spatial operations."""
    values = np.asarray(image, dtype=np.float64)
    low, high = (float(value) for value in np.percentile(values, percentiles))
    if not high > low:
        raise ValueError("tone percentile window must have positive width")
    normalized = np.clip((values - low) / (high - low), 0.0, 1.0)
    mapped = np.arcsinh(scale * normalized) / np.arcsinh(scale)
    return np.asarray(0.035 + 0.90 * mapped, dtype=np.float32)


def circular_stereographic_field(image: np.ndarray) -> np.ma.MaskedArray:
    """Mask only samples outside the unit stereographic disk."""
    coordinates = np.linspace(-1.0, 1.0, image.shape[0])
    yy, xx = np.meshgrid(coordinates, coordinates, indexing="ij")
    return np.ma.array(image, mask=(xx * xx + yy * yy) > 1.0)


def _fix_canvas(figure: Figure, size_px: int) -> None:
    figure.set_size_inches(size_px / _DPI, size_px / _DPI, forward=True)
    figure.patch.set_facecolor(_BACKGROUND)


def _save_png(figure: Figure, *, size_px: int) -> bytes:
    _fix_canvas(figure, size_px)
    payload = BytesIO()
    figure.savefig(
        payload,
        format="png",
        dpi=_DPI,
        facecolor=figure.get_facecolor(),
        metadata=_PNG_METADATA,
    )
    plt.close(figure)
    return payload.getvalue()


def _save_svg(figure: Figure, *, size_px: int, recipe_id: str) -> bytes:
    _fix_canvas(figure, size_px)
    payload = BytesIO()
    with matplotlib.rc_context({"svg.hashsalt": recipe_id}):
        figure.savefig(
            payload,
            format="svg",
            facecolor=figure.get_facecolor(),
            metadata={"Date": None},
        )
    plt.close(figure)
    return payload.getvalue()


def _tone(image: np.ndarray, recipe: KinematicalRecipe) -> np.ndarray:
    return asinh_tone_map(
        image,
        percentiles=recipe.tone_percentiles,
        scale=recipe.tone_asinh_scale,
    )


def _gray_cmap():
    return colormaps["gray"].with_extremes(bad=_BACKGROUND)


def _prepare_stereographic_axis(figure: Figure):
    axis = figure.axes[0]
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_xlim(-1.025, 1.025)
    axis.set_ylim(-1.025, 1.025)
    axis.set_aspect("equal")
    axis.set_facecolor(_BACKGROUND)
    axis.set_axis_off()
    return axis


def _insert_etched_master(
    figure: Figure,
    master_field: np.ma.MaskedArray,
) -> Figure:
    axis = _prepare_stereographic_axis(figure)
    axis.imshow(
        master_field,
        extent=(-1, 1, -1, 1),
        origin="lower",
        interpolation="nearest",
        cmap=_gray_cmap(),
        vmin=0.0,
        vmax=1.0,
        zorder=-10,
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
    return figure


def _etched_figure(
    context: _KikuchipyContext,
    style: EtchedMasterStyle,
    master_field: np.ma.MaskedArray,
) -> Figure:
    figure = context.overlay_simulators[style.name].plot(
        projection="stereographic",
        mode="lines",
        hemisphere="upper",
        scaling="linear",
        return_figure=True,
        backend="matplotlib",
        color=(0.94, 0.97, 1.0, style.line_alpha),
        linewidth=style.line_width_pt,
    )
    return _insert_etched_master(figure, master_field)


def _master_threshold_figure(
    context: _KikuchipyContext,
    master_field: np.ma.MaskedArray,
) -> Figure:
    figure = context.master_simulator.plot(
        projection="stereographic",
        mode="lines",
        hemisphere="upper",
        scaling="linear",
        return_figure=True,
        backend="matplotlib",
        color=(*_TRACE_COLOR, 0.46),
        linewidth=0.32,
    )
    return _insert_etched_master(figure, master_field)


def _stereographic_bands(context: _KikuchipyContext, recipe: KinematicalRecipe) -> bytes:
    figure = context.master_simulator.plot(
        projection="stereographic",
        mode="bands",
        hemisphere="upper",
        scaling="square",
        return_figure=True,
        backend="matplotlib",
        color=_TRACE_COLOR,
    )
    _prepare_stereographic_axis(figure)
    return _save_svg(figure, size_px=recipe.figure_size_px, recipe_id=recipe.recipe_id)


def _spherical_bands(context: _KikuchipyContext, recipe: KinematicalRecipe) -> bytes:
    figure = context.master_simulator.plot(
        projection="spherical",
        mode="bands",
        scaling="square",
        return_figure=True,
        backend="matplotlib",
        color=_TRACE_COLOR,
    )
    axis = figure.axes[0]
    axis.view_init(
        elev=_SPHERICAL_CAMERA_DEG["elevation"],
        azim=_SPHERICAL_CAMERA_DEG["azimuth"],
        roll=_SPHERICAL_CAMERA_DEG["roll"],
    )
    axis.set_proj_type("ortho")
    axis.set_xlim(-1.02, 1.02)
    axis.set_ylim(-1.02, 1.02)
    axis.set_zlim(-1.02, 1.02)
    axis.set_box_aspect((1.0, 1.0, 1.0))
    axis.set_position((0.0, 0.0, 1.0, 1.0))
    axis.set_facecolor(_BACKGROUND)
    axis.set_axis_off()
    return _save_png(figure, size_px=recipe.figure_size_px)


def _detector_figure(
    context: _KikuchipyContext,
    simulation: KinematicalSimulation,
    recipe: KinematicalRecipe,
) -> Figure:
    detector_field = _tone(simulation.detector.intensity, recipe)
    figure = context.detector_geometry.plot(
        pattern=detector_field,
        lines=True,
        zone_axes=False,
        zone_axes_labels=False,
        pc=True,
        pattern_kwargs={
            "cmap": _gray_cmap(),
            "interpolation": "nearest",
            "vmin": 0.0,
            "vmax": 1.0,
        },
        lines_kwargs={"colors": (*_TRACE_COLOR, 0.64), "linewidths": 0.62},
        pc_kwargs={"c": ["#f3b35b"], "s": 16.0},
        return_figure=True,
    )
    axis = figure.axes[0]
    axis.set_facecolor(_BACKGROUND)
    figure.patch.set_facecolor(_BACKGROUND)
    return figure


def _detector_overlay(
    context: _KikuchipyContext,
    simulation: KinematicalSimulation,
    recipe: KinematicalRecipe,
) -> bytes:
    figure = _detector_figure(context, simulation, recipe)
    return _save_png(figure, size_px=recipe.figure_size_px)


def _png_array(payload: bytes) -> np.ndarray:
    with Image.open(BytesIO(payload)) as image:
        return np.asarray(image.convert("RGBA"), dtype=np.uint8)


def _selection_panel(
    context: _KikuchipyContext,
    simulation: KinematicalSimulation,
    recipe: KinematicalRecipe,
    etched_payloads: Mapping[str, bytes],
    master_field: np.ma.MaskedArray,
) -> bytes:
    thumbnail_size = max(96, recipe.figure_size_px // 2)
    master_payload = _save_png(
        _master_threshold_figure(context, master_field), size_px=thumbnail_size
    )
    top_payloads = [
        master_payload,
        etched_payloads["etched-master-balanced.png"],
        etched_payloads["etched-master-quiet.png"],
    ]

    detector_field = _tone(simulation.detector.intensity, recipe)
    detector_payloads: list[bytes] = []
    selection_simulators = [
        context.master_simulator,
        context.overlay_simulators["balanced"],
        context.overlay_simulators["quiet"],
    ]
    for simulator in selection_simulators:
        geometry = simulator.on_detector(
            context.detector_geometry.detector,
            context.detector_geometry.rotations,
        )
        figure = geometry.plot(
            pattern=detector_field,
            lines=True,
            zone_axes=False,
            zone_axes_labels=False,
            pc=False,
            pattern_kwargs={
                "cmap": _gray_cmap(),
                "interpolation": "nearest",
                "vmin": 0.0,
                "vmax": 1.0,
            },
            lines_kwargs={"colors": (*_TRACE_COLOR, 0.68), "linewidths": 0.56},
            return_figure=True,
        )
        detector_payloads.append(_save_png(figure, size_px=thumbnail_size))

    figure, axes = plt.subplots(2, 3)
    figure.patch.set_facecolor(_BACKGROUND)
    catalog = simulation.reflector_catalog
    thresholds = [
        catalog["master"],
        catalog["overlays"]["balanced"],
        catalog["overlays"]["quiet"],
    ]
    names = ["master", "balanced", "quiet"]
    for column, (name, selection) in enumerate(zip(names, thresholds, strict=True)):
        for row, payload in enumerate((top_payloads[column], detector_payloads[column])):
            axis = axes[row, column]
            axis.imshow(_png_array(payload), interpolation="nearest")
            axis.set_axis_off()
            axis.set_facecolor(_BACKGROUND)
        axes[0, column].set_title(
            (
                f"{name}\n"
                f"|F| >= {selection['relative_factor']:.2f} max; "
                f"n={selection['retained_count']}"
            ),
            color="#e8edf0",
            fontsize=7.0,
            pad=5.0,
        )
    figure.text(
        0.012,
        0.70,
        "upper stereographic\nmaster + exact traces",
        color="#aeb9bf",
        fontsize=6.0,
        rotation=90,
        va="center",
    )
    figure.text(
        0.012,
        0.25,
        "detector consequences\nexact projected traces",
        color="#aeb9bf",
        fontsize=6.0,
        rotation=90,
        va="center",
    )
    figure.subplots_adjust(left=0.10, right=0.99, bottom=0.03, top=0.87, wspace=0.03, hspace=0.08)
    return _save_png(figure, size_px=recipe.figure_size_px)


def render_kinematical_figures(
    context: _KikuchipyContext,
    simulation: KinematicalSimulation,
    recipe: KinematicalRecipe,
) -> Mapping[str, bytes]:
    """Render six deterministic figures without altering scientific arrays."""
    upper_master = simulation.master_stereographic.intensity[0]
    master_field = circular_stereographic_field(_tone(upper_master, recipe))
    etched = {
        f"etched-master-{style.name}.png": _save_png(
            _etched_figure(context, style, master_field), size_px=recipe.figure_size_px
        )
        for style in recipe.styles
    }
    figures = {
        "kinematical-stereographic-bands.svg": _stereographic_bands(context, recipe),
        "kinematical-spherical-bands.png": _spherical_bands(context, recipe),
        "kinematical-detector-overlay.png": _detector_overlay(context, simulation, recipe),
        **etched,
    }
    figures["reflector-selection.png"] = _selection_panel(
        context,
        simulation,
        recipe,
        etched,
        master_field,
    )
    return figures

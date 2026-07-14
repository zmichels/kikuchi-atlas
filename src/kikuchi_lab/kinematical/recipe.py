"""Strict loading for version-controlled kinematical recipes."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from kikuchi_lab.model.recipes import DetectorRecipe, Orientation

from .contracts import EtchedMasterStyle, KinematicalRecipe

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "source_record",
    "energy_kev",
    "orientation",
    "detector",
    "reflections",
    "master",
    "tone",
    "figure_size_px",
    "promoted_style",
    "styles",
}
_ORIENTATION_FIELDS = {"euler_bunge_deg", "frame", "zone_axis_uvw"}
_DETECTOR_FIELDS = {
    "shape",
    "pcx",
    "pcy",
    "pcz",
    "pc_convention",
    "sample_tilt_deg",
    "detector_tilt_deg",
    "detector_azimuth_deg",
    "detector_twist_deg",
    "pixel_size_um",
    "binning",
    "supersampling",
}
_REFLECTION_FIELDS = {
    "min_dspacing_angstrom",
    "scattering_params",
    "master_relative_factor",
}
_MASTER_FIELDS = {"half_size", "hemisphere", "scaling"}
_TONE_FIELDS = {"percentiles", "asinh_scale"}
_STYLE_FIELDS = {"name", "overlay_relative_factor", "line_alpha", "line_width_pt"}


def _mapping(value: Any, field: str, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"kinematical recipe {field} fields differ from the supported schema")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"kinematical recipe {field} must be non-empty text")
    return value


def _real(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"kinematical recipe {field} must be a number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        qualifier = "positive and finite" if positive else "finite"
        raise ValueError(f"kinematical recipe {field} must be {qualifier}")
    return result


def _positive_integer(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"kinematical recipe {field} must be a positive integer")
    return value


def _integer_triplet(value: Any, field: str) -> tuple[int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(type(component) is not int for component in value)
        or value == [0, 0, 0]
    ):
        raise ValueError(f"kinematical recipe {field} must contain three nonzero integer indices")
    return value[0], value[1], value[2]


def _styles(value: Any) -> tuple[EtchedMasterStyle, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("kinematical recipe styles must be a non-empty ordered list")
    styles: list[EtchedMasterStyle] = []
    names: set[str] = set()
    for index, item in enumerate(value):
        raw = _mapping(item, f"styles[{index}]", _STYLE_FIELDS)
        name = _text(raw["name"], f"styles[{index}].name")
        if name in names:
            raise ValueError("kinematical recipe style names must be unique")
        names.add(name)
        line_alpha = _real(raw["line_alpha"], f"styles[{index}].line_alpha")
        if not 0 <= line_alpha <= 1:
            raise ValueError("kinematical recipe style line_alpha must be in [0, 1]")
        styles.append(
            EtchedMasterStyle(
                name=name,
                overlay_relative_factor=_real(
                    raw["overlay_relative_factor"],
                    f"styles[{index}].overlay_relative_factor",
                    positive=True,
                ),
                line_alpha=line_alpha,
                line_width_pt=_real(
                    raw["line_width_pt"], f"styles[{index}].line_width_pt", positive=True
                ),
            )
        )
    return tuple(styles)


def load_kinematical_recipe(path: str | Path) -> KinematicalRecipe:
    """Load and validate a version-1 project-owned kinematical recipe."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("kinematical recipe YAML is invalid") from None
    root = _mapping(payload, "top-level", _TOP_LEVEL_FIELDS)
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise ValueError("kinematical recipe schema_version must be integer 1")

    orientation_raw = _mapping(root["orientation"], "orientation", _ORIENTATION_FIELDS)
    eulers = orientation_raw["euler_bunge_deg"]
    if not isinstance(eulers, list) or len(eulers) != 3:
        raise ValueError("kinematical recipe orientation Euler angles must contain three values")
    orientation = Orientation(
        tuple(_real(value, "orientation Euler angle") for value in eulers),
        frame=_text(orientation_raw["frame"], "orientation.frame"),
    )
    zone_axis = _integer_triplet(orientation_raw["zone_axis_uvw"], "orientation.zone_axis_uvw")

    detector_raw = _mapping(root["detector"], "detector", _DETECTOR_FIELDS)
    shape = detector_raw["shape"]
    if (
        not isinstance(shape, list)
        or len(shape) != 2
        or any(type(dimension) is not int or dimension <= 0 for dimension in shape)
    ):
        raise ValueError("kinematical recipe detector.shape must contain two positive integers")
    detector = DetectorRecipe(
        shape=(shape[0], shape[1]),
        pcx=_real(detector_raw["pcx"], "detector.pcx"),
        pcy=_real(detector_raw["pcy"], "detector.pcy"),
        pcz=_real(detector_raw["pcz"], "detector.pcz"),
        pc_convention=_text(detector_raw["pc_convention"], "detector.pc_convention"),
        sample_tilt_deg=_real(detector_raw["sample_tilt_deg"], "detector.sample_tilt_deg"),
        detector_tilt_deg=_real(
            detector_raw["detector_tilt_deg"], "detector.detector_tilt_deg"
        ),
        detector_azimuth_deg=_real(
            detector_raw["detector_azimuth_deg"], "detector.detector_azimuth_deg"
        ),
        detector_twist_deg=_real(
            detector_raw["detector_twist_deg"], "detector.detector_twist_deg"
        ),
        pixel_size_um=_real(detector_raw["pixel_size_um"], "detector.pixel_size_um"),
        binning=_positive_integer(detector_raw["binning"], "detector.binning"),
        supersampling=_positive_integer(
            detector_raw["supersampling"], "detector.supersampling"
        ),
    )

    reflections = _mapping(root["reflections"], "reflections", _REFLECTION_FIELDS)
    master = _mapping(root["master"], "master", _MASTER_FIELDS)
    hemisphere = master["hemisphere"]
    if hemisphere not in {"upper", "lower", "both"}:
        raise ValueError("kinematical recipe hemisphere must be upper, lower, or both")
    if master["scaling"] != "square":
        raise ValueError("kinematical recipe master scaling must be square")

    tone = _mapping(root["tone"], "tone", _TONE_FIELDS)
    percentiles = tone["percentiles"]
    if not isinstance(percentiles, list) or len(percentiles) != 2:
        raise ValueError("kinematical recipe tone.percentiles must contain two values")
    tone_percentiles = tuple(_real(value, "tone percentile") for value in percentiles)
    if not 0 <= tone_percentiles[0] < tone_percentiles[1] <= 100:
        raise ValueError("kinematical recipe tone percentiles must increase within [0, 100]")

    styles = _styles(root["styles"])
    promoted_style = _text(root["promoted_style"], "promoted_style")
    if sum(style.name == promoted_style for style in styles) != 1:
        raise ValueError("kinematical recipe promoted_style must name exactly one style")

    return KinematicalRecipe(
        schema_version=1,
        name=_text(root["name"], "name"),
        source_record=_text(root["source_record"], "source_record"),
        energy_kev=_real(root["energy_kev"], "energy_kev", positive=True),
        orientation=orientation,
        zone_axis_uvw=zone_axis,
        detector=detector,
        min_dspacing_angstrom=_real(
            reflections["min_dspacing_angstrom"],
            "reflections.min_dspacing_angstrom",
            positive=True,
        ),
        scattering_params=_text(
            reflections["scattering_params"], "reflections.scattering_params"
        ),
        master_relative_factor=_real(
            reflections["master_relative_factor"],
            "reflections.master_relative_factor",
            positive=True,
        ),
        half_size=_positive_integer(master["half_size"], "master.half_size"),
        hemisphere=hemisphere,
        master_scaling="square",
        tone_percentiles=(tone_percentiles[0], tone_percentiles[1]),
        tone_asinh_scale=_real(tone["asinh_scale"], "tone.asinh_scale", positive=True),
        figure_size_px=_positive_integer(root["figure_size_px"], "figure_size_px"),
        promoted_style=promoted_style,
        styles=styles,
    )

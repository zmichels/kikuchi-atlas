"""Strict loading for profiled spherical-intensity recipes."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, cast

import yaml

from .contracts import (
    DensityWeightRecipe,
    ProfileName,
    SphericalIntensityRecipe,
    SphericalProfile,
    SphericalToleranceRecipe,
)


_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "source_kinematical_recipe",
    "profiles",
    "density",
    "tolerances",
    "rng_seed",
    "rng_generator",
    "csv_float_format",
    "display_resolution_deg",
    "emit_axial",
    "expected_mtex_version",
}
_PROFILE_NAMES = {"smoke", "acceptance"}
_PROFILE_FIELDS = {
    "half_size",
    "point_count",
    "sampling_resolution_deg",
    "timeout_seconds",
}
_DENSITY_FIELDS = {"name", "low_percentile", "high_percentile", "exponent"}
_TOLERANCE_FIELDS = {
    "disk_epsilon_multiplier",
    "unit_norm_max",
    "stereo_round_trip_rad_max",
    "equator_normalized_max",
    "axial_normalized_rms_max",
    "axial_normalized_max",
    "mtex_node_normalized_max",
}
_PROFILE_HALF_SIZES = {"smoke": 32, "acceptance": 128}


def _mapping(value: Any, field: str, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"spherical intensity recipe {field} fields differ from the schema")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"spherical intensity recipe {field} must be non-empty text")
    return value


def _real(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"spherical intensity recipe {field} must be a number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        qualifier = "positive and finite" if positive else "finite"
        raise ValueError(f"spherical intensity recipe {field} must be {qualifier}")
    return result


def _positive_integer(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"spherical intensity recipe {field} must be a positive integer")
    return value


def _relative_path(value: Any, field: str) -> str:
    result = _text(value, field)
    if Path(result).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", result):
        raise ValueError(f"spherical intensity recipe {field} must be a relative path")
    return result


def load_spherical_intensity_recipe(
    path: str | Path, *, profile: ProfileName
) -> SphericalIntensityRecipe:
    """Load one bounded profile from a version-1 spherical-intensity recipe."""
    if profile not in _PROFILE_NAMES:
        raise ValueError("spherical intensity profile must be smoke or acceptance")
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("spherical intensity recipe YAML is invalid") from None
    root = _mapping(payload, "top-level", _TOP_LEVEL_FIELDS)
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise ValueError("spherical intensity recipe schema_version must be integer 1")

    profiles = _mapping(root["profiles"], "profiles", _PROFILE_NAMES)
    parsed_profiles: dict[str, SphericalProfile] = {}
    for name in ("smoke", "acceptance"):
        values = _mapping(profiles[name], f"profiles.{name}", _PROFILE_FIELDS)
        half_size = _positive_integer(values["half_size"], f"profiles.{name}.half_size")
        if half_size != _PROFILE_HALF_SIZES[name]:
            raise ValueError(
                f"spherical intensity recipe {name} half_size must be "
                f"{_PROFILE_HALF_SIZES[name]}"
            )
        parsed_profiles[name] = SphericalProfile(
            name=cast(ProfileName, name),
            half_size=half_size,
            point_count=_positive_integer(
                values["point_count"], f"profiles.{name}.point_count"
            ),
            sampling_resolution_deg=_real(
                values["sampling_resolution_deg"],
                f"profiles.{name}.sampling_resolution_deg",
                positive=True,
            ),
            timeout_seconds=_positive_integer(
                values["timeout_seconds"], f"profiles.{name}.timeout_seconds"
            ),
        )

    density = _mapping(root["density"], "density", _DENSITY_FIELDS)
    tolerances = _mapping(root["tolerances"], "tolerances", _TOLERANCE_FIELDS)
    if not isinstance(root["emit_axial"], bool):
        raise ValueError("spherical intensity recipe emit_axial must be boolean")

    return SphericalIntensityRecipe(
        schema_version=1,
        name=_text(root["name"], "name"),
        source_kinematical_recipe=_relative_path(
            root["source_kinematical_recipe"], "source_kinematical_recipe"
        ),
        profile=parsed_profiles[profile],
        density=DensityWeightRecipe(
            name=_text(density["name"], "density.name"),
            low_percentile=_real(density["low_percentile"], "density.low_percentile"),
            high_percentile=_real(density["high_percentile"], "density.high_percentile"),
            exponent=_real(density["exponent"], "density.exponent", positive=True),
        ),
        tolerances=SphericalToleranceRecipe(
            disk_epsilon_multiplier=_positive_integer(
                tolerances["disk_epsilon_multiplier"],
                "tolerances.disk_epsilon_multiplier",
            ),
            unit_norm_max=_real(
                tolerances["unit_norm_max"], "tolerances.unit_norm_max", positive=True
            ),
            stereo_round_trip_rad_max=_real(
                tolerances["stereo_round_trip_rad_max"],
                "tolerances.stereo_round_trip_rad_max",
                positive=True,
            ),
            equator_normalized_max=_real(
                tolerances["equator_normalized_max"],
                "tolerances.equator_normalized_max",
                positive=True,
            ),
            axial_normalized_rms_max=_real(
                tolerances["axial_normalized_rms_max"],
                "tolerances.axial_normalized_rms_max",
                positive=True,
            ),
            axial_normalized_max=_real(
                tolerances["axial_normalized_max"],
                "tolerances.axial_normalized_max",
                positive=True,
            ),
            mtex_node_normalized_max=_real(
                tolerances["mtex_node_normalized_max"],
                "tolerances.mtex_node_normalized_max",
                positive=True,
            ),
        ),
        rng_seed=_positive_integer(root["rng_seed"], "rng_seed"),
        rng_generator=_text(root["rng_generator"], "rng_generator"),
        csv_float_format=_text(root["csv_float_format"], "csv_float_format"),
        display_resolution_deg=_real(
            root["display_resolution_deg"], "display_resolution_deg", positive=True
        ),
        emit_axial=root["emit_axial"],
        expected_mtex_version=_text(root["expected_mtex_version"], "expected_mtex_version"),
    )

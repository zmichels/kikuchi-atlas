"""Strict oriented-proof recipes and crystal-to-sample frame ledgers."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal, cast

import numpy as np
import yaml
from orix.quaternion import Rotation as OrixRotation

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)


OrientedProfileName = Literal["smoke", "review"]

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "source_spherical_recipe",
    "presentation_recipe",
    "orientation",
    "profiles",
    "interpolation",
    "spatial_filter",
    "background_color",
}
_PROFILE_NAMES = {"smoke", "review"}
_PROFILE_FIELDS = {
    "source_half_size",
    "figure_size_px",
    "sphere_longitude_count",
    "sphere_latitude_count",
    "tile_rows",
    "timeout_seconds",
}
_ORIENTATION_FIELDS = {"euler_bunge_deg", "frame"}
_APPROVED_BOUNDS = {
    "smoke": (32, 480, 180),
    "review": (512, 2400, 600),
}


def _mapping(
    value: object, field: str, expected: set[str]
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"oriented recipe {field} fields differ from the schema")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"oriented recipe {field} must be non-empty text")
    return value


def _relative_path(value: object, field: str) -> str:
    result = _text(value, field)
    if Path(result).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", result):
        raise ValueError(f"oriented recipe {field} must be a relative path")
    return result


def _euler_bunge_deg(value: object) -> tuple[float, float, float]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 3
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        raise ValueError("oriented recipe Euler angles must be three finite numbers")
    return cast(tuple[float, float, float], tuple(float(item) for item in value))


@dataclass(frozen=True)
class OrientedProfile:
    """One bounded execution profile for the oriented proof."""

    name: OrientedProfileName
    source_half_size: int
    figure_size_px: int
    sphere_longitude_count: int
    sphere_latitude_count: int
    tile_rows: int
    timeout_seconds: int

    def __post_init__(self) -> None:
        for name in (
            "source_half_size",
            "figure_size_px",
            "sphere_longitude_count",
            "sphere_latitude_count",
            "tile_rows",
            "timeout_seconds",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"oriented profile {name} must be a positive integer")
        if self.sphere_longitude_count % 2 == 0 or self.sphere_latitude_count % 2 == 0:
            raise ValueError("oriented sphere grid counts must be odd")
        if self.tile_rows > self.figure_size_px:
            raise ValueError("oriented tile_rows cannot exceed figure_size_px")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OrientedSphericalRecipe:
    """Immutable version-1 contract for one oriented spherical proof."""

    schema_version: int
    name: str
    source_spherical_recipe: str
    presentation_recipe: str
    orientation: Orientation
    profile: OrientedProfile
    interpolation: str
    spatial_filter: str
    background_color: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("oriented recipe schema_version must be integer 1")
        if self.interpolation != "bilinear":
            raise ValueError("oriented recipe interpolation must be bilinear")
        if self.spatial_filter != "none":
            raise ValueError("oriented recipe spatial_filter must be none")
        if self.background_color.lower() != "#101519":
            raise ValueError("oriented recipe background_color must be #101519")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_spherical_recipe": self.source_spherical_recipe,
            "presentation_recipe": self.presentation_recipe,
            "orientation": self.orientation.to_dict(),
            "profile": self.profile.to_dict(),
            "interpolation": self.interpolation,
            "spatial_filter": self.spatial_filter,
            "background_color": self.background_color,
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())


def orientation_matrix(orientation: Orientation) -> np.ndarray:
    """Return the active crystal-to-sample matrix in RD-TD-ND coordinates."""
    basis = np.eye(3, dtype=np.float64)
    matrix = np.column_stack(
        [transform_crystal_direction_to_sample(axis, orientation) for axis in basis]
    )
    if not np.allclose(matrix.T @ matrix, np.eye(3), rtol=0.0, atol=5e-13):
        raise ValueError("orientation matrix must be orthonormal")
    if not math.isclose(float(np.linalg.det(matrix)), 1.0, rel_tol=0.0, abs_tol=5e-13):
        raise ValueError("orientation matrix must be right-handed")
    return matrix


def load_oriented_spherical_recipe(
    path: str | Path, *, profile: OrientedProfileName
) -> OrientedSphericalRecipe:
    """Load one bounded profile from a strict version-1 oriented recipe."""
    if profile not in _PROFILE_NAMES:
        raise ValueError("oriented profile must be smoke or review")
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("oriented recipe YAML is invalid") from None

    root = _mapping(payload, "top-level", _TOP_LEVEL_FIELDS)
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise ValueError("oriented recipe schema_version must be integer 1")

    profiles = _mapping(root["profiles"], "profiles", _PROFILE_NAMES)
    parsed_profiles: dict[str, OrientedProfile] = {}
    for name in ("smoke", "review"):
        profile_data = _mapping(profiles[name], f"profiles.{name}", _PROFILE_FIELDS)
        parsed_profile = OrientedProfile(
            name=cast(OrientedProfileName, name),
            source_half_size=cast(int, profile_data["source_half_size"]),
            figure_size_px=cast(int, profile_data["figure_size_px"]),
            sphere_longitude_count=cast(int, profile_data["sphere_longitude_count"]),
            sphere_latitude_count=cast(int, profile_data["sphere_latitude_count"]),
            tile_rows=cast(int, profile_data["tile_rows"]),
            timeout_seconds=cast(int, profile_data["timeout_seconds"]),
        )
        observed_bounds = (
            parsed_profile.source_half_size,
            parsed_profile.figure_size_px,
            parsed_profile.timeout_seconds,
        )
        if observed_bounds != _APPROVED_BOUNDS[name]:
            raise ValueError(
                f"oriented {name} size/time bounds differ from the approved proof"
            )
        parsed_profiles[name] = parsed_profile

    orientation_data = _mapping(root["orientation"], "orientation", _ORIENTATION_FIELDS)
    orientation = Orientation(
        _euler_bunge_deg(orientation_data["euler_bunge_deg"]),
        frame=_text(orientation_data["frame"], "orientation.frame"),
    )
    return OrientedSphericalRecipe(
        schema_version=root["schema_version"],
        name=_text(root["name"], "name"),
        source_spherical_recipe=_relative_path(
            root["source_spherical_recipe"], "source_spherical_recipe"
        ),
        presentation_recipe=_relative_path(
            root["presentation_recipe"], "presentation_recipe"
        ),
        orientation=orientation,
        profile=parsed_profiles[profile],
        interpolation=str(root["interpolation"]),
        spatial_filter=str(root["spatial_filter"]),
        background_color=str(root["background_color"]),
    )


def orientation_ledger(orientation: Orientation) -> dict[str, object]:
    """Serialize the active frame contract and its implementation provenance."""
    matrix = orientation_matrix(orientation)
    rotation = OrixRotation.from_euler(
        orientation.euler_bunge_deg,
        degrees=True,
        direction="crystal2lab",
    )
    return {
        "schema_version": 1,
        "orientation_id": orientation.orientation_id,
        "euler_bunge_deg": list(orientation.euler_bunge_deg),
        "angle_units": "degree",
        "euler_convention": "Bunge ZXZ",
        "direction": "active crystal_to_sample",
        "equation_forward": "s = G_cs c",
        "equation_pullback": "I_sample(s) = I_crystal(G_cs^-1 s)",
        "input_frame": "crystal",
        "output_frame": "EDAX-TSL:RD-TD-ND",
        "output_axis_order": ["RD", "TD", "ND"],
        "matrix_G_cs": matrix.tolist(),
        "matrix_G_cs_inverse": matrix.T.tolist(),
        "quaternion_abcd": np.asarray(rotation.data[0], dtype=np.float64).tolist(),
        "quaternion_component_order": ["a", "b", "c", "d"],
        "determinant": float(np.linalg.det(matrix)),
        "orthonormal_max_error": float(
            np.max(np.abs(matrix.T @ matrix - np.eye(3)))
        ),
        "implementation_owner": "kikuchi_lab.projection.kikuchipy_adapter",
        "implementation_versions": {
            "kikuchi-lab": version("kikuchi-lab"),
            "orix": version("orix"),
        },
    }

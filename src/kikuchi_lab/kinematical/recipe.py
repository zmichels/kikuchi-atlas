"""Strict loading for bounded kinematical source recipes."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from kikuchi_lab.model.recipes import Orientation

from .contracts import KinematicalRecipe


_ROOT = {
    "schema_version",
    "name",
    "source_record",
    "reflector_recipe",
    "energy_kev",
    "orientation",
    "master",
}
_ORIENTATION = {"euler_bunge_deg", "frame", "zone_axis_uvw"}
_MASTER = {"half_size", "hemisphere", "scaling"}


def _mapping(value: Any, name: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"kinematical recipe {name} fields differ from the supported schema")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"kinematical recipe {name} must be non-empty text")
    return value


def _number(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"kinematical recipe {name} must be finite")
    return float(value)


def load_kinematical_recipe(path: str | Path) -> KinematicalRecipe:
    """Load the closed source-master recipe without path-dependent identity."""
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError("kinematical recipe YAML is invalid") from error
    root = _mapping(raw, "top-level", _ROOT)
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise ValueError("kinematical recipe schema_version must be integer 1")
    orientation_raw = _mapping(root["orientation"], "orientation", _ORIENTATION)
    eulers = orientation_raw["euler_bunge_deg"]
    axis = orientation_raw["zone_axis_uvw"]
    if not isinstance(eulers, list) or len(eulers) != 3:
        raise ValueError("kinematical recipe orientation Euler angles must contain three values")
    if (
        not isinstance(axis, list)
        or len(axis) != 3
        or any(type(item) is not int for item in axis)
        or axis == [0, 0, 0]
    ):
        raise ValueError("kinematical recipe zone_axis_uvw must be three non-zero integer indices")
    master = _mapping(root["master"], "master", _MASTER)
    if type(master["half_size"]) is not int or master["half_size"] <= 0:
        raise ValueError("kinematical recipe master.half_size must be a positive integer")
    if master["hemisphere"] != "both":
        raise ValueError("bounded Ice source master requires both hemispheres")
    if master["scaling"] != "square":
        raise ValueError("bounded Ice source master requires square scaling")
    energy = _number(root["energy_kev"], "energy_kev")
    if energy <= 0:
        raise ValueError("kinematical recipe energy_kev must be positive")
    return KinematicalRecipe(
        schema_version=1,
        name=_text(root["name"], "name"),
        source_record=_text(root["source_record"], "source_record"),
        reflector_recipe=_text(root["reflector_recipe"], "reflector_recipe"),
        energy_kev=energy,
        orientation=Orientation(
            tuple(_number(value, "orientation Euler angle") for value in eulers),
            frame=_text(orientation_raw["frame"], "orientation.frame"),
        ),
        zone_axis_uvw=(axis[0], axis[1], axis[2]),
        half_size=master["half_size"],
        hemisphere="both",
        scaling="square",
    )

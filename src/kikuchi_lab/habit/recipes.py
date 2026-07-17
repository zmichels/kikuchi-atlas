"""Immutable, content-identified crystal habit recipes."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import yaml

from kikuchi_lab.model.identity import stable_id

_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_PROVENANCE_FIELDS = ("uri", "license", "citation")
_ROOT_FIELDS = ("schema", "phase", "habit", "geometry", "exports", "fdm_context")
_PHASE_FIELDS = (
    "name",
    "formula",
    "space_group_number",
    "cif",
    "sha256",
    "provenance",
)
_HABIT_FIELDS = ("index_convention", "faces")
_FACE_FIELDS = ("family", "relative_distance", "label")
_GEOMETRY_FIELDS = ("maximum_dimension_mm", "orientation_matrix")
_FDM_FIELDS = ("nozzle_width_mm", "layer_height_mm")


@dataclass(frozen=True)
class HabitFace:
    family: tuple[int, ...]
    relative_distance: float
    label: str


@dataclass(frozen=True)
class PhaseSource:
    name: str
    formula: str
    space_group_number: int
    cif_path: Path
    cif_sha256: str
    provenance: Mapping[str, str]


@dataclass(frozen=True)
class FDMContext:
    nozzle_width_mm: float
    layer_height_mm: float


@dataclass(frozen=True)
class HabitRecipe:
    schema: str
    phase: PhaseSource
    index_convention: str
    faces: tuple[HabitFace, ...]
    maximum_dimension_mm: float
    orientation_matrix: tuple[tuple[float, float, float], ...]
    exports: tuple[str, ...]
    fdm_context: FDMContext | None

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "phase": {
                "name": self.phase.name,
                "formula": self.phase.formula,
                "space_group_number": self.phase.space_group_number,
                "cif_sha256": self.phase.cif_sha256,
                "provenance": dict(self.phase.provenance),
            },
            "habit": {
                "index_convention": self.index_convention,
                "faces": [asdict(face) for face in self.faces],
            },
            "geometry": {
                "maximum_dimension_mm": self.maximum_dimension_mm,
                "orientation_matrix": [list(row) for row in self.orientation_matrix],
            },
            "exports": list(self.exports),
            "fdm_context": None if self.fdm_context is None else asdict(self.fdm_context),
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("habit-recipe", self.identity_dict())


def _required_mapping(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _check_mapping_keys(
    mapping: Mapping[str, Any],
    name: str,
    *,
    allowed: tuple[str, ...],
    required: tuple[str, ...],
) -> None:
    unknown = set(mapping) - set(allowed)
    if unknown:
        rendered = ", ".join(sorted((repr(key) for key in unknown)))
        raise ValueError(f"{name} has unknown keys: {rendered}")
    missing = set(required) - set(mapping)
    if missing:
        rendered = ", ".join(sorted(missing))
        raise ValueError(f"{name} has missing keys: {rendered}")


def _required_text(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value


def _positive_float(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{key} must be a positive finite number")
    return result


def _parse_face(value: Any, convention: str) -> HabitFace:
    if not isinstance(value, dict):
        raise ValueError("habit face must be a mapping")
    _check_mapping_keys(
        value,
        "habit face",
        allowed=_FACE_FIELDS,
        required=_FACE_FIELDS,
    )
    family = value.get("family")
    expected_length = 3 if convention == "hkl" else 4
    if not isinstance(family, list) or len(family) != expected_length:
        raise ValueError(f"{convention} family must contain {expected_length} indices")
    if any(isinstance(index, bool) or not isinstance(index, int) for index in family):
        raise ValueError("family indices must be integers")
    if not any(family):
        raise ValueError("family must not be all zero")
    if convention == "hkil" and sum(family[:3]) != 0:
        raise ValueError("h  k  i closure requires h + k + i = 0")
    label = _required_text(value, "label")
    if not _LABEL.fullmatch(label):
        raise ValueError("habit face label must be safe non-empty text")
    return HabitFace(
        family=tuple(family),
        relative_distance=_positive_float(value, "relative_distance"),
        label=label,
    )


def _parse_phase(value: Mapping[str, Any], cif_path: Path, observed_hash: str) -> PhaseSource:
    space_group_number = value.get("space_group_number")
    if (
        isinstance(space_group_number, bool)
        or not isinstance(space_group_number, int)
        or not 1 <= space_group_number <= 230
    ):
        raise ValueError("space_group_number must be an integer from 1 to 230")
    provenance_raw = _required_mapping(value, "provenance")
    provenance = {field: _required_text(provenance_raw, field) for field in _PROVENANCE_FIELDS}
    return PhaseSource(
        name=_required_text(value, "name"),
        formula=_required_text(value, "formula"),
        space_group_number=space_group_number,
        cif_path=cif_path,
        cif_sha256=observed_hash,
        provenance=MappingProxyType(provenance),
    )


def _parse_exports(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or value != ["stl"]:
        raise ValueError("exports must contain exactly stl")
    return ("stl",)


def _parse_fdm_context(value: Any) -> FDMContext | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("fdm_context must be a mapping or null")
    _check_mapping_keys(
        value,
        "fdm_context",
        allowed=_FDM_FIELDS,
        required=_FDM_FIELDS,
    )
    return FDMContext(
        nozzle_width_mm=_positive_float(value, "nozzle_width_mm"),
        layer_height_mm=_positive_float(value, "layer_height_mm"),
    )


def _parse_orientation(value: Any) -> tuple[tuple[float, float, float], ...]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(not isinstance(row, list) or len(row) != 3 for row in value)
        or any(
            isinstance(item, bool) or not isinstance(item, (int, float))
            for row in value
            for item in row
        )
    ):
        raise ValueError("orientation_matrix must be a finite 3 by 3 matrix")
    orientation = np.asarray(value, dtype=float)
    if not np.isfinite(orientation).all():
        raise ValueError("orientation_matrix must be a finite 3 by 3 matrix")
    if not np.allclose(
        orientation.T @ orientation, np.eye(3), atol=1e-12, rtol=0.0
    ) or not np.isclose(np.linalg.det(orientation), 1.0, atol=1e-12, rtol=0.0):
        raise ValueError("orientation_matrix must be a proper orthogonal rotation")
    return tuple(tuple(float(item) for item in row) for row in orientation)


def load_habit_recipe(path: str | Path) -> HabitRecipe:
    recipe_path = Path(path).resolve()
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "kikuchi.habit-recipe/v1":
        raise ValueError("unsupported habit recipe schema")
    _check_mapping_keys(
        raw,
        "root",
        allowed=_ROOT_FIELDS,
        required=tuple(field for field in _ROOT_FIELDS if field != "fdm_context"),
    )
    phase_raw = _required_mapping(raw, "phase")
    habit_raw = _required_mapping(raw, "habit")
    geometry_raw = _required_mapping(raw, "geometry")
    _check_mapping_keys(
        phase_raw,
        "phase",
        allowed=_PHASE_FIELDS,
        required=_PHASE_FIELDS,
    )
    provenance_raw = _required_mapping(phase_raw, "provenance")
    _check_mapping_keys(
        provenance_raw,
        "phase provenance",
        allowed=_PROVENANCE_FIELDS,
        required=_PROVENANCE_FIELDS,
    )
    _check_mapping_keys(
        habit_raw,
        "habit",
        allowed=_HABIT_FIELDS,
        required=_HABIT_FIELDS,
    )
    _check_mapping_keys(
        geometry_raw,
        "geometry",
        allowed=_GEOMETRY_FIELDS,
        required=("maximum_dimension_mm",),
    )
    convention = _required_text(habit_raw, "index_convention")
    if convention not in {"hkl", "hkil"}:
        raise ValueError("index_convention must be hkl or hkil")
    cif_locator = Path(_required_text(phase_raw, "cif"))
    cif_path = cif_locator if cif_locator.is_absolute() else recipe_path.parent / cif_locator
    cif_path = cif_path.resolve()
    observed_hash = hashlib.sha256(cif_path.read_bytes()).hexdigest()
    if observed_hash != _required_text(phase_raw, "sha256"):
        raise ValueError("habit CIF checksum mismatch")
    raw_faces = habit_raw.get("faces")
    if not isinstance(raw_faces, list) or not raw_faces:
        raise ValueError("habit faces must be a non-empty list")
    faces = tuple(_parse_face(item, convention) for item in raw_faces)
    if len({face.label for face in faces}) != len(faces):
        raise ValueError("habit face labels must be unique")
    return HabitRecipe(
        schema="kikuchi.habit-recipe/v1",
        phase=_parse_phase(phase_raw, cif_path, observed_hash),
        index_convention=convention,
        faces=faces,
        maximum_dimension_mm=_positive_float(geometry_raw, "maximum_dimension_mm"),
        orientation_matrix=_parse_orientation(
            geometry_raw["orientation_matrix"]
            if "orientation_matrix" in geometry_raw
            else [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        ),
        exports=_parse_exports(raw.get("exports")),
        fdm_context=_parse_fdm_context(raw.get("fdm_context")),
    )

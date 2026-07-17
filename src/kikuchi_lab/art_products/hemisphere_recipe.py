"""Strict phase-general recipes for the five-phase hemisphere art series."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import yaml

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.recipes import Orientation

from .tattoo_recipe import (
    _ALLOCATION,
    _SCORE_WEIGHTS,
    _TIER_ORDER,
    _exact_boolean,
    _exact_boundary_policy,
    _exact_integer,
    _exact_number,
    _exact_numeric_mapping,
    _exact_palette,
    _exact_width_mapping,
    _mapping,
)


_PHASE_ORDER = ("ice-ih", "forsterite", "quartz", "zircon", "titanite")
_REFLECTOR_RECIPES = {
    "ice-ih": "../reflectors/ice-ih-art-bands.yml",
    "forsterite": "../reflectors/forsterite-art-bands.yml",
    "quartz": "../reflectors/quartz-art-bands.yml",
    "zircon": "../reflectors/zircon-art-bands.yml",
    "titanite": "../reflectors/titanite-art-bands.yml",
}
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "phase_order",
    "reflector_recipes",
    "reviewed_standard_reference",
    "orientation",
    "path_allocation",
    "stroke_widths_mm",
    "great_circle_samples",
    "crop_radius",
    "redundancy_threshold_deg",
    "score_weights",
    "coverage_sectors",
    "zone_interior_margin_deg",
    "projection_boundary",
    "artboard_size_mm",
    "include_nodes",
    "spatial_filter",
    "primary_palette",
    "treatments",
}
_ORIENTATION_FIELDS = {"euler_bunge_deg", "frame"}
_TREATMENT_FIELDS = {"arc_width_scale"}
_TREATMENT_SCALES = {"standard": 1.0, "wide": 1.15}
_PHASE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _orientation(value: object) -> Orientation:
    payload = _mapping(value, _ORIENTATION_FIELDS, "orientation")
    orientation = Orientation(
        euler_bunge_deg=payload["euler_bunge_deg"],
        frame=payload["frame"],
    )
    if orientation.frame != "crystal_to_sample":
        raise ValueError("hemisphere recipe orientation must be crystal_to_sample")
    return orientation


def _phase_slug(value: object) -> str:
    if not isinstance(value, str) or _PHASE_SLUG.fullmatch(value) is None:
        raise ValueError("hemisphere recipe phase_slug is invalid")
    return value


def _shared_policy(instance: object) -> dict[str, object]:
    allocation = _exact_numeric_mapping(
        getattr(instance, "path_allocation"),
        _ALLOCATION,
        "path_allocation",
    )
    widths = _exact_width_mapping(getattr(instance, "stroke_widths_mm"))
    weights = _exact_numeric_mapping(
        getattr(instance, "score_weights"),
        _SCORE_WEIGHTS,
        "score_weights",
    )
    return {
        "artboard_size_mm": _exact_number(
            getattr(instance, "artboard_size_mm"), 145.0, "artboard_size_mm"
        ),
        "path_allocation": allocation,
        "stroke_widths_mm": widths,
        "great_circle_samples": _exact_integer(
            getattr(instance, "great_circle_samples"), 721, "great_circle_samples"
        ),
        "crop_radius": _exact_number(
            getattr(instance, "crop_radius"), 0.90, "crop_radius"
        ),
        "redundancy_threshold_deg": _exact_number(
            getattr(instance, "redundancy_threshold_deg"),
            4.0,
            "redundancy_threshold_deg",
        ),
        "score_weights": weights,
        "coverage_sectors": _exact_integer(
            getattr(instance, "coverage_sectors"), 6, "coverage_sectors"
        ),
        "zone_interior_margin_deg": _exact_number(
            getattr(instance, "zone_interior_margin_deg"),
            6.0,
            "zone_interior_margin_deg",
        ),
        "projection_boundary": _exact_boundary_policy(
            getattr(instance, "projection_boundary")
        ),
        "include_nodes": _exact_boolean(
            getattr(instance, "include_nodes"), False, "include_nodes"
        ),
        "primary_palette": _exact_palette(getattr(instance, "primary_palette")),
    }


def _set_shared_policy(instance: object) -> None:
    for field, value in _shared_policy(instance).items():
        object.__setattr__(instance, field, value)
    if getattr(instance, "spatial_filter") != "none":
        raise ValueError("hemisphere recipe spatial_filter must be none")


def _shared_dict(instance: object) -> dict[str, object]:
    return {
        "orientation": getattr(instance, "orientation").to_dict(),
        "path_allocation": dict(getattr(instance, "path_allocation")),
        "stroke_widths_mm": {
            tier: list(getattr(instance, "stroke_widths_mm")[tier])
            for tier in _TIER_ORDER
        },
        "great_circle_samples": getattr(instance, "great_circle_samples"),
        "crop_radius": getattr(instance, "crop_radius"),
        "redundancy_threshold_deg": getattr(instance, "redundancy_threshold_deg"),
        "score_weights": dict(getattr(instance, "score_weights")),
        "coverage_sectors": getattr(instance, "coverage_sectors"),
        "zone_interior_margin_deg": getattr(instance, "zone_interior_margin_deg"),
        "projection_boundary": dict(getattr(instance, "projection_boundary")),
        "artboard_size_mm": getattr(instance, "artboard_size_mm"),
        "include_nodes": getattr(instance, "include_nodes"),
        "spatial_filter": getattr(instance, "spatial_filter"),
        "primary_palette": dict(getattr(instance, "primary_palette")),
    }


@dataclass(frozen=True)
class HemisphereTreatment:
    """One width-only treatment that leaves selected centerlines unchanged."""

    name: Literal["standard", "wide"]
    arc_width_scale: float

    def __post_init__(self) -> None:
        if self.name not in _TREATMENT_SCALES:
            raise ValueError("hemisphere treatment must be standard or wide")
        object.__setattr__(
            self,
            "arc_width_scale",
            _exact_number(
                self.arc_width_scale,
                _TREATMENT_SCALES[self.name],
                "arc_width_scale",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "arc_width_scale": self.arc_width_scale}

    @property
    def treatment_id(self) -> str:
        return stable_id("hemisphere-treatment", self.to_dict())


@dataclass(frozen=True)
class HemisphereCompositionRecipe:
    """One phase's orientation and shared selection/projection policy."""

    phase_slug: str
    orientation: Orientation
    artboard_size_mm: float
    path_allocation: Mapping[str, int]
    stroke_widths_mm: Mapping[str, tuple[float, ...]]
    great_circle_samples: int
    crop_radius: float
    redundancy_threshold_deg: float
    score_weights: Mapping[str, float]
    coverage_sectors: int
    zone_interior_margin_deg: float
    projection_boundary: Mapping[str, object]
    include_nodes: bool
    spatial_filter: str
    primary_palette: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase_slug", _phase_slug(self.phase_slug))
        if not isinstance(self.orientation, Orientation) or (
            self.orientation.frame != "crystal_to_sample"
        ):
            raise ValueError(
                "hemisphere composition orientation must be crystal_to_sample"
            )
        _set_shared_policy(self)

    def to_dict(self) -> dict[str, object]:
        return {"phase_slug": self.phase_slug, **_shared_dict(self)}

    @property
    def recipe_id(self) -> str:
        return stable_id("hemisphere-composition", self.to_dict())


@dataclass(frozen=True)
class HemisphereSeriesRecipe:
    """Immutable shared policy and phase catalog references for one art series."""

    schema_version: int
    name: str
    phase_order: tuple[str, ...]
    reflector_recipes: Mapping[str, str]
    reviewed_standard_reference: str
    orientation: Orientation
    artboard_size_mm: float
    path_allocation: Mapping[str, int]
    stroke_widths_mm: Mapping[str, tuple[float, ...]]
    great_circle_samples: int
    crop_radius: float
    redundancy_threshold_deg: float
    score_weights: Mapping[str, float]
    coverage_sectors: int
    zone_interior_margin_deg: float
    projection_boundary: Mapping[str, object]
    include_nodes: bool
    spatial_filter: str
    primary_palette: Mapping[str, str]
    treatments: Mapping[str, HemisphereTreatment]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "schema_version",
            _exact_integer(self.schema_version, 1, "schema_version"),
        )
        if self.name != "five-phase-hemisphere-series":
            raise ValueError(
                "hemisphere recipe name must be five-phase-hemisphere-series"
            )
        phases = tuple(_phase_slug(slug) for slug in self.phase_order)
        if phases != _PHASE_ORDER or len(set(phases)) != len(phases):
            raise ValueError("hemisphere recipe phase_order differs from approved order")
        object.__setattr__(self, "phase_order", phases)
        if dict(self.reflector_recipes) != _REFLECTOR_RECIPES:
            raise ValueError("hemisphere recipe reflector_recipes differ from policy")
        object.__setattr__(
            self,
            "reflector_recipes",
            MappingProxyType(dict(_REFLECTOR_RECIPES)),
        )
        if self.reviewed_standard_reference != "ice-ih":
            raise ValueError("hemisphere reviewed standard reference must be ice-ih")
        if not isinstance(self.orientation, Orientation) or (
            self.orientation.frame != "crystal_to_sample"
        ):
            raise ValueError("hemisphere recipe orientation must be crystal_to_sample")
        _set_shared_policy(self)

        treatments = dict(self.treatments)
        if tuple(treatments) != ("standard", "wide") or any(
            not isinstance(value, HemisphereTreatment)
            or value.name != name
            for name, value in treatments.items()
        ):
            raise ValueError("hemisphere treatments must be ordered standard then wide")
        object.__setattr__(self, "treatments", MappingProxyType(treatments))

    def composition_for(self, phase_slug: str) -> HemisphereCompositionRecipe:
        phase = _phase_slug(phase_slug)
        if phase not in self.phase_order:
            raise KeyError(f"phase {phase!r} is not in the hemisphere series")
        return HemisphereCompositionRecipe(
            phase_slug=phase,
            orientation=self.orientation,
            artboard_size_mm=self.artboard_size_mm,
            path_allocation=self.path_allocation,
            stroke_widths_mm=self.stroke_widths_mm,
            great_circle_samples=self.great_circle_samples,
            crop_radius=self.crop_radius,
            redundancy_threshold_deg=self.redundancy_threshold_deg,
            score_weights=self.score_weights,
            coverage_sectors=self.coverage_sectors,
            zone_interior_margin_deg=self.zone_interior_margin_deg,
            projection_boundary=self.projection_boundary,
            include_nodes=self.include_nodes,
            spatial_filter=self.spatial_filter,
            primary_palette=self.primary_palette,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "phase_order": list(self.phase_order),
            "reflector_recipes": dict(self.reflector_recipes),
            "reviewed_standard_reference": self.reviewed_standard_reference,
            **_shared_dict(self),
            "treatments": {
                name: {"arc_width_scale": treatment.arc_width_scale}
                for name, treatment in self.treatments.items()
            },
        }

    @property
    def series_id(self) -> str:
        return stable_id("hemisphere-series", self.to_dict())


def load_hemisphere_series_recipe(path: str | Path) -> HemisphereSeriesRecipe:
    """Load and strictly validate the version-1 five-phase series recipe."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("hemisphere recipe YAML is invalid") from None
    root = _mapping(payload, _TOP_LEVEL_FIELDS, "top-level")
    treatment_payload = _mapping(root["treatments"], set(_TREATMENT_SCALES), "treatments")
    treatments: dict[str, HemisphereTreatment] = {}
    for name, expected in _TREATMENT_SCALES.items():
        item = _mapping(treatment_payload[name], _TREATMENT_FIELDS, f"treatments.{name}")
        treatments[name] = HemisphereTreatment(
            name=name,  # type: ignore[arg-type]
            arc_width_scale=_exact_number(
                item["arc_width_scale"], expected, "arc_width_scale"
            ),
        )
    return HemisphereSeriesRecipe(
        schema_version=root["schema_version"],
        name=root["name"],
        phase_order=tuple(root["phase_order"]),
        reflector_recipes=root["reflector_recipes"],
        reviewed_standard_reference=root["reviewed_standard_reference"],
        orientation=_orientation(root["orientation"]),
        artboard_size_mm=root["artboard_size_mm"],
        path_allocation=root["path_allocation"],
        stroke_widths_mm=root["stroke_widths_mm"],
        great_circle_samples=root["great_circle_samples"],
        crop_radius=root["crop_radius"],
        redundancy_threshold_deg=root["redundancy_threshold_deg"],
        score_weights=root["score_weights"],
        coverage_sectors=root["coverage_sectors"],
        zone_interior_margin_deg=root["zone_interior_margin_deg"],
        projection_boundary=root["projection_boundary"],
        include_nodes=root["include_nodes"],
        spatial_filter=root["spatial_filter"],
        primary_palette=root["primary_palette"],
        treatments=treatments,
    )


__all__ = [
    "HemisphereCompositionRecipe",
    "HemisphereSeriesRecipe",
    "HemisphereTreatment",
    "load_hemisphere_series_recipe",
]

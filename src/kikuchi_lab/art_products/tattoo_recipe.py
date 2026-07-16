"""Strict immutable recipe for the primary rotated Ice Ih tattoo selection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.recipes import Orientation


_TIER_ORDER = ("dominant", "secondary", "fine")
_SCORE_ORDER = (
    "strength",
    "angular_width",
    "nonredundancy",
    "coverage",
    "zone_relationship",
)
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "orientation",
    "artboard_size_mm",
    "path_allocation",
    "stroke_widths_mm",
    "great_circle_samples",
    "crop_radius",
    "redundancy_threshold_deg",
    "score_weights",
    "coverage_sectors",
    "zone_interior_margin_deg",
    "include_rim",
    "include_nodes",
    "spatial_filter",
    "primary_palette",
}
_ORIENTATION_FIELDS = {"euler_bunge_deg", "frame"}
_ALLOCATION = {"dominant": 4, "secondary": 4, "fine": 3}
_WIDTHS = {
    "dominant": (4.8, 4.2, 3.6, 3.1),
    "secondary": (2.5, 2.2, 1.9, 1.6),
    "fine": (1.2, 1.0, 0.8),
}
_SCORE_WEIGHTS = {
    "strength": 0.40,
    "angular_width": 0.15,
    "nonredundancy": 0.20,
    "coverage": 0.15,
    "zone_relationship": 0.10,
}
_PALETTE = {"ink": "#000000", "substrate": "skin"}


def _mapping(value: object, expected: set[str], field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"tattoo recipe {field} fields differ from the schema")
    return value


def _exact_number(value: object, expected: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"tattoo recipe {field} must be {expected}")
    converted = float(value)
    if converted != expected:
        raise ValueError(f"tattoo recipe {field} must be {expected}")
    return converted


def _exact_integer(value: object, expected: int, field: str) -> int:
    if type(value) is not int or value != expected:
        raise ValueError(f"tattoo recipe {field} must be integer {expected}")
    return value


def _exact_boolean(value: object, expected: bool, field: str) -> bool:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"tattoo recipe {field} must be {str(expected).lower()}")
    return value


def _exact_numeric_mapping(
    value: object,
    expected: Mapping[str, int | float],
    field: str,
) -> MappingProxyType[str, int | float]:
    source = _mapping(value, set(expected), field)
    converted: dict[str, int | float] = {}
    for name, required in expected.items():
        if isinstance(required, int):
            converted[name] = _exact_integer(source[name], required, field)
        else:
            converted[name] = _exact_number(source[name], required, field)
    return MappingProxyType(converted)


def _exact_width_mapping(
    value: object,
) -> MappingProxyType[str, tuple[float, ...]]:
    source = _mapping(value, set(_WIDTHS), "stroke_widths_mm")
    converted: dict[str, tuple[float, ...]] = {}
    for tier in _TIER_ORDER:
        widths = source[tier]
        if not isinstance(widths, Sequence) or isinstance(widths, (str, bytes, bytearray)):
            raise ValueError("tattoo recipe stroke_widths_mm must match approved widths")
        required = _WIDTHS[tier]
        if len(widths) != len(required):
            raise ValueError("tattoo recipe stroke_widths_mm must match approved widths")
        converted[tier] = tuple(
            _exact_number(width, expected, "stroke_widths_mm")
            for width, expected in zip(widths, required, strict=True)
        )
    return MappingProxyType(converted)


def _exact_palette(value: object) -> MappingProxyType[str, str]:
    source = _mapping(value, set(_PALETTE), "primary_palette")
    if dict(source) != _PALETTE:
        raise ValueError("tattoo recipe primary_palette must be black on skin")
    return MappingProxyType(dict(_PALETTE))


@dataclass(frozen=True)
class TattooRecipe:
    """Exact version-1 selection and art policy for the primary composition."""

    schema_version: int
    name: str
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
    include_rim: bool
    include_nodes: bool
    spatial_filter: str
    primary_palette: Mapping[str, str]

    def __post_init__(self) -> None:
        schema_version = _exact_integer(self.schema_version, 1, "schema_version")
        if self.name != "ice-ih-tattoo":
            raise ValueError("tattoo recipe name must be ice-ih-tattoo")
        if not isinstance(self.orientation, Orientation) or (
            self.orientation.euler_bunge_deg != (17.0, 31.0, 43.0)
            or self.orientation.frame != "crystal_to_sample"
        ):
            raise ValueError(
                "tattoo recipe orientation must be active crystal-to-sample "
                "Bunge (17, 31, 43) degrees"
            )
        allocation = _exact_numeric_mapping(
            self.path_allocation,
            _ALLOCATION,
            "path_allocation",
        )
        widths = _exact_width_mapping(self.stroke_widths_mm)
        score_weights = _exact_numeric_mapping(
            self.score_weights,
            _SCORE_WEIGHTS,
            "score_weights",
        )
        palette = _exact_palette(self.primary_palette)

        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(
            self,
            "artboard_size_mm",
            _exact_number(self.artboard_size_mm, 145.0, "artboard_size_mm"),
        )
        object.__setattr__(self, "path_allocation", allocation)
        object.__setattr__(self, "stroke_widths_mm", widths)
        object.__setattr__(
            self,
            "great_circle_samples",
            _exact_integer(self.great_circle_samples, 721, "great_circle_samples"),
        )
        object.__setattr__(
            self,
            "crop_radius",
            _exact_number(self.crop_radius, 0.90, "crop_radius"),
        )
        object.__setattr__(
            self,
            "redundancy_threshold_deg",
            _exact_number(
                self.redundancy_threshold_deg,
                4.0,
                "redundancy_threshold_deg",
            ),
        )
        object.__setattr__(self, "score_weights", score_weights)
        object.__setattr__(
            self,
            "coverage_sectors",
            _exact_integer(self.coverage_sectors, 6, "coverage_sectors"),
        )
        object.__setattr__(
            self,
            "zone_interior_margin_deg",
            _exact_number(
                self.zone_interior_margin_deg,
                6.0,
                "zone_interior_margin_deg",
            ),
        )
        object.__setattr__(
            self,
            "include_rim",
            _exact_boolean(self.include_rim, False, "include_rim"),
        )
        object.__setattr__(
            self,
            "include_nodes",
            _exact_boolean(self.include_nodes, False, "include_nodes"),
        )
        if self.spatial_filter != "none":
            raise ValueError("tattoo recipe spatial_filter must be none")
        object.__setattr__(self, "primary_palette", palette)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "orientation": self.orientation.to_dict(),
            "artboard_size_mm": self.artboard_size_mm,
            "path_allocation": dict(self.path_allocation),
            "stroke_widths_mm": {
                tier: list(self.stroke_widths_mm[tier]) for tier in _TIER_ORDER
            },
            "great_circle_samples": self.great_circle_samples,
            "crop_radius": self.crop_radius,
            "redundancy_threshold_deg": self.redundancy_threshold_deg,
            "score_weights": dict(self.score_weights),
            "coverage_sectors": self.coverage_sectors,
            "zone_interior_margin_deg": self.zone_interior_margin_deg,
            "include_rim": self.include_rim,
            "include_nodes": self.include_nodes,
            "spatial_filter": self.spatial_filter,
            "primary_palette": dict(self.primary_palette),
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("tattoo-recipe", self.to_dict())


def load_tattoo_recipe(path: str | Path) -> TattooRecipe:
    """Load and fully validate one strict primary tattoo recipe."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("tattoo recipe YAML is invalid") from None
    root = _mapping(payload, _TOP_LEVEL_FIELDS, "top-level")
    orientation_payload = _mapping(
        root["orientation"],
        _ORIENTATION_FIELDS,
        "orientation",
    )
    orientation = Orientation(
        euler_bunge_deg=orientation_payload["euler_bunge_deg"],
        frame=orientation_payload["frame"],
    )
    return TattooRecipe(
        schema_version=root["schema_version"],
        name=root["name"],
        orientation=orientation,
        artboard_size_mm=root["artboard_size_mm"],
        path_allocation=root["path_allocation"],
        stroke_widths_mm=root["stroke_widths_mm"],
        great_circle_samples=root["great_circle_samples"],
        crop_radius=root["crop_radius"],
        redundancy_threshold_deg=root["redundancy_threshold_deg"],
        score_weights=root["score_weights"],
        coverage_sectors=root["coverage_sectors"],
        zone_interior_margin_deg=root["zone_interior_margin_deg"],
        include_rim=root["include_rim"],
        include_nodes=root["include_nodes"],
        spatial_filter=root["spatial_filter"],
        primary_palette=root["primary_palette"],
    )


__all__ = ["TattooRecipe", "load_tattoo_recipe"]

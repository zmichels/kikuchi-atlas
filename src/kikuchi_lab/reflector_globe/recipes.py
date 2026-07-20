"""Closed, physical recipes for analytic outward reflector ridges."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import yaml

from kikuchi_lab.model.identity import stable_id


_SCHEMA = "kikuchi.reflector-ridge-recipe/v1"
_TIE_POLICY = "keep_equal_weights_together"


class _DuplicateKeyError(ValueError):
    """Raised when a recipe repeats a YAML key."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe loader retaining YAML's unique-key contract."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateKeyError(f"duplicate key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _positive(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{field} must be a positive finite number")
    return number


def _keys(value: Any, *, allowed: set[str], required: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise ValueError(f"{field} has unknown keys: {unknown}")
    if missing:
        raise ValueError(f"{field} is missing keys: {missing}")
    return value


@dataclass(frozen=True)
class ReflectorRidgeGeometry:
    """Physical globe dimensions and directionality for one ridge field."""

    base_diameter_mm: float
    maximum_relief_mm: float
    topology: str
    subdivisions: int
    direction: Literal["raised_outward"]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "base_diameter_mm", _positive(self.base_diameter_mm, field="base_diameter_mm")
        )
        object.__setattr__(
            self, "maximum_relief_mm", _positive(self.maximum_relief_mm, field="maximum_relief_mm")
        )
        if not isinstance(self.topology, str) or not self.topology.strip():
            raise ValueError("topology must be non-empty text")
        if (
            isinstance(self.subdivisions, bool)
            or not isinstance(self.subdivisions, int)
            or not 0 <= self.subdivisions <= 7
        ):
            raise ValueError("subdivisions must be an integer in [0, 7]")
        if self.direction != "raised_outward":
            raise ValueError("direction must equal raised_outward")


@dataclass(frozen=True)
class ReflectorRidgeSelection:
    """Catalog compatibility policy retained in the ridge recipe."""

    source_structure_id: str
    energy_kev: float
    eligibility_min_weight: float
    tie_policy: Literal["keep_equal_weights_together"]
    cohort_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.source_structure_id, str) or not self.source_structure_id.strip():
            raise ValueError("source_structure_id must be non-empty text")
        object.__setattr__(self, "energy_kev", _positive(self.energy_kev, field="energy_kev"))
        threshold = _positive(self.eligibility_min_weight, field="eligibility_min_weight")
        if threshold > 1.0:
            raise ValueError("eligibility_min_weight must be in (0, 1]")
        object.__setattr__(self, "eligibility_min_weight", threshold)
        if self.tie_policy != _TIE_POLICY:
            raise ValueError(f"tie_policy must equal {_TIE_POLICY}")
        if type(self.cohort_count) is not int or not 2 <= self.cohort_count <= 4:
            raise ValueError("cohort_count must be an integer between 2 and 4")


@dataclass(frozen=True)
class RidgeTier:
    """One cohort's outward ridge height and physical corridor controls."""

    height_mm: float
    width_multiplier: float
    minimum_width_mm: float
    edge_fillet_fraction: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "height_mm", _positive(self.height_mm, field="height_mm"))
        object.__setattr__(
            self, "width_multiplier", _positive(self.width_multiplier, field="width_multiplier")
        )
        object.__setattr__(
            self, "minimum_width_mm", _positive(self.minimum_width_mm, field="minimum_width_mm")
        )
        value = self.edge_fillet_fraction
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0.0 < float(value) <= 1.0
        ):
            raise ValueError("edge_fillet_fraction must be in (0, 1]")
        object.__setattr__(self, "edge_fillet_fraction", float(value))


@dataclass(frozen=True)
class ReflectorRidgeRecipe:
    """Plain-data recipe for a bounded-union, raised reflector field."""

    schema: str
    geometry: ReflectorRidgeGeometry
    selection: ReflectorRidgeSelection
    tiers: Mapping[int, RidgeTier]
    fdm_context: str | None = None
    recipe_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema != _SCHEMA:
            raise ValueError(f"schema must equal {_SCHEMA}")
        if not isinstance(self.geometry, ReflectorRidgeGeometry):
            raise ValueError("geometry must be a ReflectorRidgeGeometry")
        if not isinstance(self.selection, ReflectorRidgeSelection):
            raise ValueError("selection must be a ReflectorRidgeSelection")
        tiers = dict(self.tiers)
        expected_cohorts = set(range(1, self.selection.cohort_count + 1))
        if set(tiers) != expected_cohorts or not all(
            isinstance(tier, RidgeTier) for tier in tiers.values()
        ):
            raise ValueError("tiers must contain RidgeTier records for every selected cohort")
        if any(tier.height_mm > self.geometry.maximum_relief_mm for tier in tiers.values()):
            raise ValueError("tier height_mm must not exceed geometry maximum_relief_mm")
        if tiers[self.selection.cohort_count].height_mm != self.geometry.maximum_relief_mm:
            raise ValueError("strongest cohort height_mm must equal geometry maximum_relief_mm")
        if self.fdm_context is not None and self.fdm_context != "filament_fdm":
            raise ValueError("fdm_context must equal filament_fdm when provided")
        frozen_tiers = MappingProxyType({cohort: tiers[cohort] for cohort in sorted(tiers)})
        object.__setattr__(self, "tiers", frozen_tiers)
        object.__setattr__(
            self,
            "recipe_id",
            stable_id("reflector-ridge-recipe", self.identity_dict()),
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "geometry": asdict(self.geometry),
            "selection": asdict(self.selection),
            "tiers": {str(cohort): asdict(tier) for cohort, tier in self.tiers.items()},
            "fdm_context": self.fdm_context,
        }


def load_reflector_ridge_recipe(path: str | Path) -> ReflectorRidgeRecipe:
    """Load a closed, physical analytic-ridge recipe."""
    raw = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_UniqueKeySafeLoader)
    root = _keys(
        raw,
        allowed={"schema", "geometry", "selection", "tiers", "fdm_context"},
        required={"schema", "geometry", "selection", "tiers"},
        field="root",
    )
    geometry = _keys(
        root["geometry"],
        allowed={"base_diameter_mm", "maximum_relief_mm", "topology", "subdivisions", "direction"},
        required={"base_diameter_mm", "maximum_relief_mm", "topology", "subdivisions", "direction"},
        field="geometry",
    )
    selection = _keys(
        root["selection"],
        allowed={
            "source_structure_id",
            "energy_kev",
            "eligibility_min_weight",
            "tie_policy",
            "cohort_count",
        },
        required={
            "source_structure_id",
            "energy_kev",
            "eligibility_min_weight",
            "tie_policy",
            "cohort_count",
        },
        field="selection",
    )
    raw_tiers = root["tiers"]
    if not isinstance(raw_tiers, dict):
        raise ValueError("tiers must be a mapping")
    tiers: dict[int, RidgeTier] = {}
    for cohort, value in raw_tiers.items():
        if type(cohort) is not int or cohort not in {1, 2, 3, 4}:
            raise ValueError("tiers must use integer cohort keys 1 through 4")
        tier = _keys(
            value,
            allowed={"height_mm", "width_multiplier", "minimum_width_mm", "edge_fillet_fraction"},
            required={"height_mm", "width_multiplier", "minimum_width_mm", "edge_fillet_fraction"},
            field=f"tiers.{cohort}",
        )
        tiers[cohort] = RidgeTier(**tier)
    loaded_geometry = ReflectorRidgeGeometry(**geometry)
    if loaded_geometry.topology != "icosphere":
        raise ValueError("topology must equal icosphere")
    if loaded_geometry.base_diameter_mm != 80.0:
        raise ValueError("base_diameter_mm must equal 80.0")
    if loaded_geometry.maximum_relief_mm != 3.0:
        raise ValueError("maximum_relief_mm must equal 3.0")
    if loaded_geometry.subdivisions != 7:
        raise ValueError("subdivisions must equal 7")
    return ReflectorRidgeRecipe(
        schema=root["schema"],
        geometry=loaded_geometry,
        selection=ReflectorRidgeSelection(**selection),
        tiers=tiers,
        fdm_context=root.get("fdm_context"),
    )


__all__ = [
    "ReflectorRidgeGeometry",
    "ReflectorRidgeRecipe",
    "ReflectorRidgeSelection",
    "RidgeTier",
    "load_reflector_ridge_recipe",
]

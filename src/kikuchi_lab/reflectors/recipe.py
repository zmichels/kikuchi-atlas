"""Strict reflector-catalog recipe loading."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

from kikuchi_lab.model.identity import stable_id

_ALLOWED_KEYS = {
    "schema_version",
    "source_record",
    "energy_kev",
    "min_dspacing_angstrom",
    "scattering_params",
    "source_master_relative_factor",
    "selection_relative_factor",
    "weight_exponent",
    "eligibility_min_weight",
    "tie_policy",
    "cohort_count",
}
_TIE_POLICY = "keep_equal_weights_together"


class _DuplicateKeyError(ValueError):
    """Raised when a recipe mapping repeats a YAML key."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that preserves YAML's mapping-key uniqueness contract."""


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


def _positive(name: str, value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return number


def _fraction(name: str, value: object) -> float:
    number = _positive(name, value)
    if number > 1.0:
        raise ValueError(f"{name} must be in (0, 1]")
    return number


def _relative_source_record(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("source_record must be non-empty relative text")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("source_record must be a relative project path")
    return path.as_posix()


@dataclass(frozen=True)
class ReflectorRecipe:
    schema_version: int
    source_record: str
    energy_kev: float
    min_dspacing_angstrom: float
    scattering_params: str
    source_master_relative_factor: float
    selection_relative_factor: float
    weight_exponent: float
    eligibility_min_weight: float
    tie_policy: Literal["keep_equal_weights_together"]
    cohort_count: int
    recipe_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("schema_version must equal 1")
        object.__setattr__(self, "schema_version", 1)
        object.__setattr__(self, "source_record", _relative_source_record(self.source_record))
        object.__setattr__(self, "energy_kev", _positive("energy_kev", self.energy_kev))
        object.__setattr__(
            self,
            "min_dspacing_angstrom",
            _positive("min_dspacing_angstrom", self.min_dspacing_angstrom),
        )
        if not isinstance(self.scattering_params, str) or not self.scattering_params.strip():
            raise ValueError("scattering_params must be non-empty text")
        object.__setattr__(
            self,
            "source_master_relative_factor",
            _positive("source_master_relative_factor", self.source_master_relative_factor),
        )
        object.__setattr__(
            self,
            "selection_relative_factor",
            _fraction("selection_relative_factor", self.selection_relative_factor),
        )
        object.__setattr__(
            self,
            "weight_exponent",
            _positive("weight_exponent", self.weight_exponent),
        )
        object.__setattr__(
            self,
            "eligibility_min_weight",
            _fraction("eligibility_min_weight", self.eligibility_min_weight),
        )
        if self.tie_policy != _TIE_POLICY:
            raise ValueError(f"tie_policy must equal {_TIE_POLICY}")
        if type(self.cohort_count) is not int or self.cohort_count < 1:
            raise ValueError("cohort_count must be a positive integer")
        object.__setattr__(
            self,
            "recipe_id",
            stable_id(
                "reflector-recipe",
                {
                    "schema_version": self.schema_version,
                    "source_record": self.source_record,
                    "energy_kev": self.energy_kev,
                    "min_dspacing_angstrom": self.min_dspacing_angstrom,
                    "scattering_params": self.scattering_params,
                    "source_master_relative_factor": self.source_master_relative_factor,
                    "selection_relative_factor": self.selection_relative_factor,
                    "weight_exponent": self.weight_exponent,
                    "eligibility_min_weight": self.eligibility_min_weight,
                    "tie_policy": self.tie_policy,
                    "cohort_count": self.cohort_count,
                },
            ),
        )


def load_reflector_recipe(path: str | Path) -> ReflectorRecipe:
    """Load a closed-schema catalog recipe without incorporating *path* into identity."""
    raw = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_UniqueKeySafeLoader)
    if not isinstance(raw, dict):
        raise ValueError("reflector recipe root must be a mapping")
    unknown = sorted(set(raw) - _ALLOWED_KEYS)
    missing = sorted(_ALLOWED_KEYS - set(raw))
    if unknown:
        raise ValueError(f"reflector recipe has unknown keys: {unknown}")
    if missing:
        raise ValueError(f"reflector recipe is missing keys: {missing}")
    return ReflectorRecipe(**raw)

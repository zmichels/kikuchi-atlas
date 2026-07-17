"""Immutable, content-identified spherical intensity-relief recipes."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from kikuchi_lab.model.identity import plain_data, stable_id

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MASTER_PRODUCT_ID = re.compile(r"^master-[0-9a-f]{16}$")


@dataclass(frozen=True)
class ReliefSourceExpectation:
    product_id: str
    array_sha256: str
    file_sha256: str


@dataclass(frozen=True)
class ReliefGeometrySpec:
    base_diameter_mm: float
    maximum_relief_mm: float
    topology: str
    subdivisions: int


@dataclass(frozen=True)
class ReliefMappingSpec:
    percentiles: tuple[float, float]
    gamma: float
    direction: str


@dataclass(frozen=True)
class SphericalFilterSpec:
    kind: str
    fwhm_mm: float
    cutoff_sigma: float


@dataclass(frozen=True)
class ReliefFDMContext:
    process: str


@dataclass(frozen=True)
class ReliefGlobeRecipe:
    schema: str
    source: ReliefSourceExpectation
    geometry: ReliefGeometrySpec
    mapping: ReliefMappingSpec
    filter: SphericalFilterSpec
    exports: tuple[str, ...]
    fdm_context: ReliefFDMContext | None
    recipe_id: str

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source": asdict(self.source),
            "geometry": asdict(self.geometry),
            "mapping": asdict(self.mapping),
            "filter": asdict(self.filter),
            "export": {"formats": list(self.exports)},
            "fdm_context": (
                asdict(self.fdm_context) if self.fdm_context is not None else None
            ),
        }


def _keys(mapping: Any, *, allowed: set[str], required: set[str], field: str) -> None:
    if not isinstance(mapping, dict):
        raise ValueError(f"{field} must be a mapping")
    unknown = sorted(set(mapping) - allowed)
    missing = sorted(required - set(mapping))
    if unknown:
        raise ValueError(f"{field} has unknown keys: {unknown}")
    if missing:
        raise ValueError(f"{field} is missing keys: {missing}")


def _positive_number(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{key} must be a positive finite number")
    return number


def _finite_number(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{key} must be a finite number")
    return number


def _exact_text(mapping: dict[str, Any], key: str, expected: str) -> str:
    value = mapping.get(key)
    if value != expected:
        raise ValueError(f"{key} must equal {expected}")
    return expected


def _text(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value


def _source_expectation(mapping: dict[str, Any]) -> ReliefSourceExpectation:
    product_id = mapping.get("product_id")
    if not isinstance(product_id, str) or not _MASTER_PRODUCT_ID.fullmatch(product_id):
        raise ValueError("product_id must match master-[0-9a-f]{16}")
    checksums: dict[str, str] = {}
    for field in ("array_sha256", "file_sha256"):
        value = mapping.get(field)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise ValueError(f"{field} must be a lowercase SHA-256 string")
        checksums[field] = value
    return ReliefSourceExpectation(product_id=product_id, **checksums)


def _fdm_context(value: Any) -> ReliefFDMContext | None:
    if value is None:
        return None
    _keys(value, allowed={"process"}, required={"process"}, field="fdm_context")
    return ReliefFDMContext(process=_exact_text(value, "process", "filament_fdm"))


def load_relief_globe_recipe(path: str | Path) -> ReliefGlobeRecipe:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    _keys(
        raw,
        allowed={"schema", "source", "geometry", "mapping", "filter", "export", "fdm_context"},
        required={"schema", "source", "geometry", "mapping", "filter", "export"},
        field="root",
    )
    if raw.get("schema") != "kikuchi.relief-globe-recipe/v1":
        raise ValueError("unsupported relief globe recipe schema")

    source = raw["source"]
    geometry = raw["geometry"]
    mapping = raw["mapping"]
    percentiles = mapping.get("percentiles") if isinstance(mapping, dict) else None
    filtering = raw["filter"]
    export = raw["export"]
    _keys(
        source,
        allowed={"product_id", "array_sha256", "file_sha256"},
        required={"product_id", "array_sha256", "file_sha256"},
        field="source",
    )
    _keys(
        geometry,
        allowed={"base_diameter_mm", "maximum_relief_mm", "topology", "subdivisions"},
        required={"base_diameter_mm", "maximum_relief_mm", "topology", "subdivisions"},
        field="geometry",
    )
    _keys(
        mapping,
        allowed={"percentiles", "gamma", "direction"},
        required={"percentiles", "gamma", "direction"},
        field="mapping",
    )
    _keys(
        percentiles,
        allowed={"lower", "upper"},
        required={"lower", "upper"},
        field="percentiles",
    )
    _keys(
        filtering,
        allowed={"kind", "fwhm_mm", "cutoff_sigma"},
        required={"kind", "fwhm_mm", "cutoff_sigma"},
        field="filter",
    )
    _keys(export, allowed={"formats"}, required={"formats"}, field="export")

    subdivisions = geometry.get("subdivisions")
    if (
        isinstance(subdivisions, bool)
        or not isinstance(subdivisions, int)
        or not 0 <= subdivisions <= 7
    ):
        raise ValueError("subdivisions must be an integer in [0, 7]")
    lower = _finite_number(percentiles, "lower")
    upper = _finite_number(percentiles, "upper")
    if not 0.0 <= lower < upper <= 100.0:
        raise ValueError("percentile bounds must satisfy 0 <= lower < upper <= 100")
    formats = export.get("formats")
    if (
        not isinstance(formats, list)
        or not formats
        or any(not isinstance(item, str) or not item.strip() for item in formats)
        or len(set(formats)) != len(formats)
    ):
        raise ValueError("formats must be a non-empty list of unique text values")

    recipe_without_id = ReliefGlobeRecipe(
        schema="kikuchi.relief-globe-recipe/v1",
        source=_source_expectation(source),
        geometry=ReliefGeometrySpec(
            base_diameter_mm=_positive_number(geometry, "base_diameter_mm"),
            maximum_relief_mm=_positive_number(geometry, "maximum_relief_mm"),
            topology=_text(geometry, "topology"),
            subdivisions=subdivisions,
        ),
        mapping=ReliefMappingSpec(
            percentiles=(lower, upper),
            gamma=_positive_number(mapping, "gamma"),
            direction=_text(mapping, "direction"),
        ),
        filter=SphericalFilterSpec(
            kind=_text(filtering, "kind"),
            fwhm_mm=_positive_number(filtering, "fwhm_mm"),
            cutoff_sigma=_positive_number(filtering, "cutoff_sigma"),
        ),
        exports=tuple(formats),
        fdm_context=_fdm_context(raw.get("fdm_context")),
        recipe_id="",
    )
    identity = plain_data(recipe_without_id.identity_dict())
    return replace(
        recipe_without_id,
        recipe_id=stable_id("relief-globe-recipe", identity),
    )

"""Strict immutable recipe for the standard-width five-phase orientation gallery."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.recipes import Orientation

from .hemisphere_recipe import (
    HemisphereSeriesRecipe,
    HemisphereTreatment,
    load_hemisphere_series_recipe,
)


_PHASE_COUNT = 5
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "source_series_recipe",
    "treatment",
    "variants",
}
_VARIANT_FIELDS = {"slug", "orientation"}
_ORIENTATION_FIELDS = {"euler_bunge_deg", "frame"}
_SOURCE_SERIES_RECIPE = "five-phase-hemisphere-series.yml"
_TREATMENT = "standard"
_VARIANT_SLUGS = ("azimuthal-60", "tilt-plus-20", "oblique-high")
_VARIANT_ORIENTATIONS = (
    (77.0, 31.0, 43.0),
    (17.0, 51.0, 43.0),
    (97.0, 71.0, 83.0),
)
_VARIANT_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _mapping(value: object, expected: set[str], field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"orientation gallery recipe {field} fields differ from the schema")
    return value


def _exact_integer(value: object, expected: int, field: str) -> int:
    if type(value) is not int or value != expected:
        raise ValueError(f"orientation gallery recipe {field} must be integer {expected}")
    return value


def _orientation(value: object) -> Orientation:
    payload = _mapping(value, _ORIENTATION_FIELDS, "variant orientation")
    if payload["frame"] != "crystal_to_sample":
        raise ValueError(
            "orientation gallery recipe variant orientation frame must be crystal_to_sample"
        )
    try:
        orientation = Orientation(
            euler_bunge_deg=payload["euler_bunge_deg"],
            frame=payload["frame"],
        )
    except (TypeError, ValueError):
        raise ValueError("orientation gallery recipe variant orientation is invalid") from None
    if orientation.frame != "crystal_to_sample":
        raise ValueError(
            "orientation gallery recipe variant orientation frame must be crystal_to_sample"
        )
    return orientation


@dataclass(frozen=True)
class OrientationGalleryVariant:
    """One named active crystal-to-sample Bunge orientation."""

    slug: str
    orientation: Orientation

    def __post_init__(self) -> None:
        if not isinstance(self.slug, str) or _VARIANT_SLUG.fullmatch(self.slug) is None:
            raise ValueError("orientation gallery recipe variant slug is invalid")
        if not isinstance(self.orientation, Orientation) or (
            self.orientation.frame != "crystal_to_sample"
        ):
            raise ValueError(
                "orientation gallery recipe variant orientation must be crystal_to_sample"
            )

    def to_dict(self) -> dict[str, object]:
        return {"slug": self.slug, "orientation": self.orientation.to_dict()}

    @property
    def variant_id(self) -> str:
        return stable_id("orientation-gallery-variant", self.to_dict())


@dataclass(frozen=True)
class OrientationGalleryRecipe:
    """Versioned gallery policy reusing one immutable five-phase source series."""

    schema_version: int
    name: str
    source_series_recipe: str
    source_series: HemisphereSeriesRecipe
    treatment: HemisphereTreatment
    variants: tuple[OrientationGalleryVariant, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "schema_version",
            _exact_integer(self.schema_version, 1, "schema_version"),
        )
        if self.name != "five-phase-standard-orientation-gallery":
            raise ValueError(
                "orientation gallery recipe name must be five-phase-standard-orientation-gallery"
            )
        if self.source_series_recipe != _SOURCE_SERIES_RECIPE:
            raise ValueError(
                "orientation gallery recipe source_series_recipe must be "
                "five-phase-hemisphere-series.yml"
            )
        if not isinstance(self.source_series, HemisphereSeriesRecipe):
            raise ValueError("orientation gallery recipe source series is invalid")
        if len(self.source_series.phase_order) != _PHASE_COUNT:
            raise ValueError(
                "orientation gallery recipe source series must contain the approved "
                "five-phase inventory"
            )
        if not isinstance(self.treatment, HemisphereTreatment) or (
            self.treatment.name != _TREATMENT or self.treatment.arc_width_scale != 1.0
        ):
            raise ValueError("orientation gallery recipe treatment must be the standard width")

        variants = tuple(self.variants)
        if len(variants) != 3:
            raise ValueError("orientation gallery recipe must contain exactly three variants")
        if any(not isinstance(variant, OrientationGalleryVariant) for variant in variants):
            raise ValueError("orientation gallery recipe variants are invalid")
        slugs = tuple(variant.slug for variant in variants)
        if len(set(slugs)) != len(slugs):
            raise ValueError("orientation gallery recipe variant slugs must be unique")
        if slugs != _VARIANT_SLUGS:
            raise ValueError("orientation gallery recipe variant slugs differ from policy")
        orientations = tuple(variant.orientation for variant in variants)
        if any(orientation == self.source_series.orientation for orientation in orientations):
            raise ValueError("orientation gallery recipe variants must be non-identity")
        if len(set(orientations)) != len(orientations):
            raise ValueError("orientation gallery recipe variant orientations must be distinct")
        if (
            tuple(orientation.euler_bunge_deg for orientation in orientations)
            != _VARIANT_ORIENTATIONS
        ):
            raise ValueError("orientation gallery recipe variant orientations differ from policy")
        object.__setattr__(self, "variants", variants)

    @property
    def phase_order(self) -> tuple[str, ...]:
        """Ordered phase inventory inherited from the immutable source series."""
        return self.source_series.phase_order

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_series_recipe": self.source_series_recipe,
            "source_series_id": self.source_series.series_id,
            "treatment": self.treatment.to_dict(),
            "variants": [variant.to_dict() for variant in self.variants],
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("orientation-gallery-recipe", self.to_dict())


def _variants(value: object) -> tuple[OrientationGalleryVariant, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("orientation gallery recipe variants must be a sequence")
    variants: list[OrientationGalleryVariant] = []
    for index, item in enumerate(value):
        payload = _mapping(item, _VARIANT_FIELDS, f"variants[{index}]")
        variants.append(
            OrientationGalleryVariant(
                slug=payload["slug"],  # type: ignore[arg-type]
                orientation=_orientation(payload["orientation"]),
            )
        )
    return tuple(variants)


def load_orientation_gallery_recipe(path: str | Path) -> OrientationGalleryRecipe:
    """Load the strict version-1 standard-width orientation-gallery policy."""
    recipe_path = Path(path)
    try:
        payload = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("orientation gallery recipe YAML is invalid") from None
    root = _mapping(payload, _TOP_LEVEL_FIELDS, "top-level")
    schema_version = _exact_integer(root["schema_version"], 1, "schema_version")
    name = root["name"]
    if name != "five-phase-standard-orientation-gallery":
        raise ValueError(
            "orientation gallery recipe name must be five-phase-standard-orientation-gallery"
        )
    source_series_recipe = root["source_series_recipe"]
    if source_series_recipe != _SOURCE_SERIES_RECIPE:
        raise ValueError(
            "orientation gallery recipe source_series_recipe must be "
            "five-phase-hemisphere-series.yml"
        )
    treatment_name = root["treatment"]
    if treatment_name != _TREATMENT:
        raise ValueError("orientation gallery recipe treatment must be standard")
    variants = _variants(root["variants"])
    try:
        source_series = load_hemisphere_series_recipe(recipe_path.parent / source_series_recipe)
    except OSError:
        raise ValueError("orientation gallery recipe source series is invalid") from None
    return OrientationGalleryRecipe(
        schema_version=schema_version,
        name=name,
        source_series_recipe=source_series_recipe,
        source_series=source_series,
        treatment=source_series.treatments[_TREATMENT],
        variants=variants,
    )


__all__ = [
    "OrientationGalleryRecipe",
    "OrientationGalleryVariant",
    "load_orientation_gallery_recipe",
]

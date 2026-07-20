"""Immutable, content-identified contracts shared by Ice Ih art products."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

import numpy as np

from kikuchi_lab.model.identity import stable_id


AcceptanceState = Literal["unreviewed", "accepted", "rejected"]
TattooTier = Literal["dominant", "secondary", "fine"]

_ACCEPTANCE_STATES = {"unreviewed", "accepted", "rejected"}
_TATTOO_TIERS = {"dominant", "secondary", "fine"}
_PROJECTION = "upper_specimen_stereographic_center_trace"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    return value


def _require_schema_1(value: object) -> int:
    if type(value) is not int or value != 1:
        raise ValueError("schema_version must be integer 1")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be boolean")
    return value


def _require_positive_finite(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be positive and finite")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0:
        raise ValueError(f"{field_name} must be positive and finite")
    return converted


def _require_unit_weight(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be in (0, 1]")
    converted = float(value)
    if not math.isfinite(converted) or not 0 < converted <= 1:
        raise ValueError(f"{field_name} must be in (0, 1]")
    return converted


def _owned_f8(value: object, *, field_name: str, shape: tuple[int, ...]) -> np.ndarray:
    try:
        converted = np.array(value, dtype=np.dtype("<f8"), order="C", copy=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain finite numbers") from exc
    if converted.shape != shape:
        raise ValueError(f"{field_name} must have shape {shape}")
    if not np.isfinite(converted).all():
        raise ValueError(f"{field_name} must contain finite numbers")
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.dtype("<f8")).reshape(
        converted.shape
    )


def _owned_points(value: object) -> np.ndarray:
    try:
        converted = np.array(value, dtype=np.dtype("<f8"), order="C", copy=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("points_mm must have shape (N, 2)") from exc
    if converted.ndim != 2 or converted.shape[1:] != (2,):
        raise ValueError("points_mm must have shape (N, 2)")
    if converted.shape[0] < 2:
        raise ValueError("points_mm must have shape (N, 2) with N >= 2")
    if not np.isfinite(converted).all():
        raise ValueError("points_mm must contain finite numbers")
    return np.frombuffer(converted.tobytes(order="C"), dtype=np.dtype("<f8")).reshape(
        converted.shape
    )


def _score_mapping(value: object) -> Mapping[str, float]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError("score_components must be a non-empty mapping")
    scores: dict[str, float] = {}
    for name, score in value.items():
        _require_text(name, "score component name")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("score component values must be finite numbers")
        converted = float(score)
        if not math.isfinite(converted):
            raise ValueError("score component values must be finite numbers")
        scores[name] = converted
    return MappingProxyType(scores)


@dataclass(frozen=True, eq=False)
class ArtBandMember:
    """One intrinsically identified band plus mutable-by-rebuild art policy."""

    hkl: tuple[int, int, int]
    normal_crystal: np.ndarray
    bragg_half_width_rad: float
    structure_factor_magnitude: float
    normalized_weight: float
    globe_cohort: int | None
    globe_eligible: bool
    tattoo_eligible: bool
    acceptance_state: AcceptanceState
    acceptance_reason: str
    member_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.hkl, Sequence)
            or isinstance(self.hkl, (str, bytes, bytearray))
            or len(self.hkl) != 3
            or any(type(index) is not int for index in self.hkl)
            or not any(self.hkl)
        ):
            raise ValueError("hkl must contain three integers and must be nonzero")
        hkl = tuple(self.hkl)
        normal = _owned_f8(
            self.normal_crystal,
            field_name="normal_crystal",
            shape=(3,),
        )
        if abs(float(np.linalg.norm(normal)) - 1.0) > 5e-13:
            raise ValueError("normal_crystal must be unit length within 5e-13")
        half_width = _require_positive_finite(
            self.bragg_half_width_rad,
            "bragg_half_width_rad",
        )
        strength = _require_positive_finite(
            self.structure_factor_magnitude,
            "structure_factor_magnitude",
        )
        weight = _require_unit_weight(self.normalized_weight, "normalized_weight")
        if self.globe_cohort is not None and (
            type(self.globe_cohort) is not int or self.globe_cohort not in {1, 2, 3, 4}
        ):
            raise ValueError("globe_cohort must be 1, 2, 3, 4, or None")
        _require_boolean(self.globe_eligible, "globe_eligible")
        _require_boolean(self.tattoo_eligible, "tattoo_eligible")
        if self.acceptance_state not in _ACCEPTANCE_STATES:
            raise ValueError(
                "acceptance_state must be unreviewed, accepted, or rejected"
            )
        _require_text(self.acceptance_reason, "acceptance_reason")

        object.__setattr__(self, "hkl", hkl)
        object.__setattr__(self, "normal_crystal", normal)
        object.__setattr__(self, "bragg_half_width_rad", half_width)
        object.__setattr__(self, "structure_factor_magnitude", strength)
        object.__setattr__(self, "normalized_weight", weight)
        object.__setattr__(
            self,
            "member_id",
            stable_id("art-band-member", self.intrinsic_dict()),
        )

    def intrinsic_dict(self) -> dict[str, object]:
        """Return source-location-independent evidence used by ``member_id``."""
        return {
            "hkl": list(self.hkl),
            "normal_crystal": self.normal_crystal.tolist(),
            "bragg_half_width_rad": self.bragg_half_width_rad,
            "structure_factor_magnitude": self.structure_factor_magnitude,
            "normalized_weight": self.normalized_weight,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self.intrinsic_dict(),
            "member_id": self.member_id,
            "globe_cohort": self.globe_cohort,
            "globe_eligible": self.globe_eligible,
            "tattoo_eligible": self.tattoo_eligible,
            "acceptance_state": self.acceptance_state,
            "acceptance_reason": self.acceptance_reason,
        }


@dataclass(frozen=True, eq=False)
class ArtBandCatalog:
    """Ordered, provenance-bearing art-band catalog."""

    schema_version: int
    source_structure_id: str
    source_structure_sha256: str
    source_recipe_id: str
    presentation_recipe_id: str
    eligibility_min_weight: float
    members: tuple[ArtBandMember, ...]
    catalog_id: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema_1(self.schema_version)
        _require_text(self.source_structure_id, "source_structure_id")
        if (
            not isinstance(self.source_structure_sha256, str)
            or not _SHA256.fullmatch(self.source_structure_sha256)
        ):
            raise ValueError(
                "source_structure_sha256 must be a lowercase SHA-256 digest"
            )
        _require_text(self.source_recipe_id, "source_recipe_id")
        _require_text(self.presentation_recipe_id, "presentation_recipe_id")
        threshold = _require_unit_weight(
            self.eligibility_min_weight,
            "eligibility_min_weight",
        )
        members = tuple(self.members)
        if not members:
            raise ValueError("members must be non-empty")
        if any(not isinstance(member, ArtBandMember) for member in members):
            raise ValueError("members must contain only ArtBandMember values")
        if len({member.member_id for member in members}) != len(members):
            raise ValueError("member_id values must be unique")

        object.__setattr__(self, "eligibility_min_weight", threshold)
        object.__setattr__(self, "members", members)
        object.__setattr__(
            self,
            "catalog_id",
            stable_id("art-band-catalog", self.to_dict()),
        )

    def to_dict(self) -> dict[str, object]:
        """Return complete canonical catalog content, excluding its derived ID."""
        return {
            "schema_version": self.schema_version,
            "source_structure_id": self.source_structure_id,
            "source_structure_sha256": self.source_structure_sha256,
            "source_recipe_id": self.source_recipe_id,
            "presentation_recipe_id": self.presentation_recipe_id,
            "eligibility_min_weight": self.eligibility_min_weight,
            "members": [member.to_dict() for member in self.members],
        }


@dataclass(frozen=True, eq=False)
class TattooBoundary:
    schema_version: int
    role: str
    scientific_claim: str
    center_mm: tuple[float, float]
    outer_diameter_mm: float
    width_mm: float
    ink: str
    boundary_id: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema_1(self.schema_version)
        if self.role != "stereographic_hemisphere_boundary":
            raise ValueError("boundary role must be stereographic_hemisphere_boundary")
        if self.scientific_claim != "noncrystallographic_projection_primitive":
            raise ValueError(
                "boundary scientific_claim must be "
                "noncrystallographic_projection_primitive"
            )
        center = tuple(float(value) for value in self.center_mm)
        if center != (72.5, 72.5):
            raise ValueError("boundary center_mm must be exactly (72.5, 72.5)")
        outer = _require_positive_finite(
            self.outer_diameter_mm, "outer_diameter_mm"
        )
        width = _require_positive_finite(self.width_mm, "width_mm")
        if outer != 132.0 or width != 2.2:
            raise ValueError("boundary dimensions must be exactly 132.0 and 2.2 mm")
        if self.ink != "#000000":
            raise ValueError("boundary ink must be #000000")
        object.__setattr__(self, "center_mm", center)
        object.__setattr__(self, "outer_diameter_mm", outer)
        object.__setattr__(self, "width_mm", width)
        object.__setattr__(
            self, "boundary_id", stable_id("tattoo-boundary", self.identity_dict())
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "scientific_claim": self.scientific_claim,
            "center_mm": list(self.center_mm),
            "outer_diameter_mm": self.outer_diameter_mm,
            "width_mm": self.width_mm,
            "ink": self.ink,
        }

    def to_dict(self) -> dict[str, object]:
        return {"boundary_id": self.boundary_id, **self.identity_dict()}


@dataclass(frozen=True, eq=False)
class TattooPath:
    """One selected physical center-trace path in the tattoo composition."""

    member_id: str
    tier: TattooTier
    width_mm: float
    points_mm: np.ndarray
    score_components: Mapping[str, float]
    selection_reason: str
    points_sha256: str = field(init=False)
    path_id: str = field(init=False)

    def __post_init__(self) -> None:
        _require_text(self.member_id, "member_id")
        if self.tier not in _TATTOO_TIERS:
            raise ValueError("tier must be dominant, secondary, or fine")
        width = _require_positive_finite(self.width_mm, "width_mm")
        points = _owned_points(self.points_mm)
        scores = _score_mapping(self.score_components)
        _require_text(self.selection_reason, "selection_reason")
        points_sha256 = hashlib.sha256(points.tobytes(order="C")).hexdigest()

        object.__setattr__(self, "width_mm", width)
        object.__setattr__(self, "points_mm", points)
        object.__setattr__(self, "score_components", scores)
        object.__setattr__(self, "points_sha256", points_sha256)
        object.__setattr__(
            self,
            "path_id",
            stable_id("tattoo-path", self.identity_dict()),
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "member_id": self.member_id,
            "tier": self.tier,
            "width_mm": self.width_mm,
            "points_sha256": self.points_sha256,
            "score_components": dict(self.score_components),
            "selection_reason": self.selection_reason,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "path_id": self.path_id,
            **self.identity_dict(),
            "points_mm": self.points_mm.tolist(),
        }


@dataclass(frozen=True, eq=False)
class TattooGeometry:
    """Ordered physical tattoo paths in the fixed specimen projection."""

    schema_version: int
    catalog_id: str
    orientation_id: str
    artboard_size_mm: float
    boundary: TattooBoundary
    paths: tuple[TattooPath, ...]
    projection: str
    geometry_id: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema_1(self.schema_version)
        _require_text(self.catalog_id, "catalog_id")
        _require_text(self.orientation_id, "orientation_id")
        artboard = _require_positive_finite(self.artboard_size_mm, "artboard_size_mm")
        if not isinstance(self.boundary, TattooBoundary):
            raise ValueError("boundary must be a TattooBoundary")
        paths = tuple(self.paths)
        if not paths:
            raise ValueError("paths must be non-empty")
        if any(not isinstance(path, TattooPath) for path in paths):
            raise ValueError("paths must contain only TattooPath values")
        if len({path.path_id for path in paths}) != len(paths):
            raise ValueError("path_id values must be unique")
        if len({path.member_id for path in paths}) != len(paths):
            raise ValueError("member_id values must be unique")
        if self.projection != _PROJECTION:
            raise ValueError(f"projection must be {_PROJECTION}")

        object.__setattr__(self, "artboard_size_mm", artboard)
        object.__setattr__(self, "paths", paths)
        object.__setattr__(
            self,
            "geometry_id",
            stable_id("tattoo-geometry", self.to_dict()),
        )

    def to_dict(self) -> dict[str, object]:
        """Return canonical geometry content with coordinate hashes and widths."""
        return {
            "schema_version": self.schema_version,
            "catalog_id": self.catalog_id,
            "orientation_id": self.orientation_id,
            "artboard_size_mm": self.artboard_size_mm,
            "projection": self.projection,
            "boundary": self.boundary.to_dict(),
            "paths": [path.to_dict() for path in self.paths],
        }


__all__ = [
    "AcceptanceState",
    "ArtBandCatalog",
    "ArtBandMember",
    "TattooBoundary",
    "TattooGeometry",
    "TattooPath",
    "TattooTier",
]

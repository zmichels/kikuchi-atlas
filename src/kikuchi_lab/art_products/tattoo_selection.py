"""Deterministic active rotation, center traces, scoring, and allocation."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

import numpy as np

from kikuchi_lab.art_products.contracts import ArtBandCatalog, TattooTier
from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix

from .tattoo_recipe import TattooRecipe


DecisionReason = Literal["selected", "angular_redundancy", "allocation_complete"]
_TIER_ORDER: tuple[TattooTier, ...] = ("dominant", "secondary", "fine")
_SCORE_NAMES = (
    "strength",
    "angular_width",
    "nonredundancy",
    "coverage",
    "zone_relationship",
)
_ARRAY_DTYPE = np.dtype("<f8")


def _owned_array(
    value: object,
    *,
    field_name: str,
    trailing_shape: tuple[int, ...],
) -> np.ndarray:
    try:
        converted = np.array(value, dtype=_ARRAY_DTYPE, order="C", copy=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain finite numbers") from exc
    if converted.ndim < len(trailing_shape) or converted.shape[-len(trailing_shape) :] != (
        trailing_shape
    ):
        raise ValueError(f"{field_name} must end with shape {trailing_shape}")
    if not np.isfinite(converted).all():
        raise ValueError(f"{field_name} must contain finite numbers")
    return np.frombuffer(converted.tobytes(order="C"), dtype=_ARRAY_DTYPE).reshape(
        converted.shape
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(item) for item in value)
    return value


def _scores(value: Mapping[str, float]) -> Mapping[str, float]:
    if set(value) != set(_SCORE_NAMES):
        raise ValueError("score_components must contain the five approved components")
    converted = {name: float(value[name]) for name in _SCORE_NAMES}
    if any(not math.isfinite(score) or not 0.0 <= score <= 1.0 for score in converted.values()):
        raise ValueError("score components must be finite values in [0, 1]")
    return MappingProxyType(converted)


@dataclass(frozen=True, eq=False)
class TattooCandidate:
    """One eligible catalog band represented in the rotated specimen frame."""

    member_id: str
    hkl: tuple[int, int, int]
    normalized_weight: float
    bragg_half_width_rad: float
    normal_crystal: np.ndarray
    normal_sample: np.ndarray
    great_circle_sample: np.ndarray
    center_trace: np.ndarray
    midpoint_sector: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "normal_crystal",
            _owned_array(
                self.normal_crystal,
                field_name="normal_crystal",
                trailing_shape=(3,),
            ),
        )
        object.__setattr__(
            self,
            "normal_sample",
            _owned_array(
                self.normal_sample,
                field_name="normal_sample",
                trailing_shape=(3,),
            ),
        )
        object.__setattr__(
            self,
            "great_circle_sample",
            _owned_array(
                self.great_circle_sample,
                field_name="great_circle_sample",
                trailing_shape=(3,),
            ),
        )
        object.__setattr__(
            self,
            "center_trace",
            _owned_array(
                self.center_trace,
                field_name="center_trace",
                trailing_shape=(2,),
            ),
        )


@dataclass(frozen=True, eq=False)
class SelectedTattooPath:
    """One selected normalized center trace with its graphic rank assignment."""

    member_id: str
    tier: TattooTier
    width_mm: float
    normal_sample: np.ndarray
    center_trace: np.ndarray
    score_components: Mapping[str, float]
    total_score: float
    selection_reason: str
    center_trace_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        normal = _owned_array(
            self.normal_sample,
            field_name="normal_sample",
            trailing_shape=(3,),
        )
        trace = _owned_array(
            self.center_trace,
            field_name="center_trace",
            trailing_shape=(2,),
        )
        scores = _scores(self.score_components)
        total = float(self.total_score)
        if not math.isfinite(total):
            raise ValueError("total_score must be finite")
        object.__setattr__(self, "normal_sample", normal)
        object.__setattr__(self, "center_trace", trace)
        object.__setattr__(self, "score_components", scores)
        object.__setattr__(self, "total_score", total)
        object.__setattr__(
            self,
            "center_trace_sha256",
            hashlib.sha256(trace.tobytes(order="C")).hexdigest(),
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "member_id": self.member_id,
            "tier": self.tier,
            "width_mm": self.width_mm,
            "center_trace_sha256": self.center_trace_sha256,
            "score_components": dict(self.score_components),
            "total_score": self.total_score,
            "selection_reason": self.selection_reason,
        }


@dataclass(frozen=True, eq=False)
class TattooSelection:
    """Immutable candidate sheet, selected paths, and complete decision ledger."""

    catalog_id: str
    recipe_id: str
    orientation_id: str
    candidates: tuple[TattooCandidate, ...]
    selected_paths: tuple[SelectedTattooPath, ...]
    ledger: Mapping[str, object]
    selection_id: str = field(init=False)

    def __post_init__(self) -> None:
        candidates = tuple(self.candidates)
        selected = tuple(self.selected_paths)
        ledger = _freeze(self.ledger)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "selected_paths", selected)
        object.__setattr__(self, "ledger", ledger)
        object.__setattr__(
            self,
            "selection_id",
            stable_id(
                "tattoo-selection",
                {
                    "catalog_id": self.catalog_id,
                    "recipe_id": self.recipe_id,
                    "orientation_id": self.orientation_id,
                    "selected_paths": [path.identity_dict() for path in selected],
                },
            ),
        )


def _canonical_axial_normal(normal: np.ndarray) -> np.ndarray:
    result = np.array(normal, dtype=np.float64, copy=True)
    for component in result:
        if abs(float(component)) > 5e-15:
            if component < 0.0:
                result *= -1.0
            break
    return result


def _center_trace(
    normal_sample: np.ndarray,
    sample_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    normal = _canonical_axial_normal(normal_sample)
    specimen_z = np.array([0.0, 0.0, 1.0])
    equator_anchor = np.cross(specimen_z, normal)
    anchor_norm = float(np.linalg.norm(equator_anchor))
    if anchor_norm <= 5e-14:
        equator_anchor = np.array([1.0, 0.0, 0.0])
    else:
        equator_anchor /= anchor_norm
    upper_axis = np.cross(normal, equator_anchor)
    upper_axis /= np.linalg.norm(upper_axis)
    if upper_axis[2] < 0.0:
        upper_axis *= -1.0

    angles = np.linspace(0.0, 2.0 * np.pi, sample_count, endpoint=True)
    circle = (
        np.cos(angles)[:, None] * equator_anchor[None, :]
        + np.sin(angles)[:, None] * upper_axis[None, :]
    )
    if abs(float(upper_axis[2])) <= 5e-14:
        upper_arc = circle
    else:
        upper_arc = circle[: sample_count // 2 + 1]
    projected = upper_arc[:, :2] / (1.0 + upper_arc[:, 2, None])
    return circle, projected


def _midpoint_sector(trace: np.ndarray, sector_count: int) -> int:
    midpoint = trace[len(trace) // 2]
    if float(np.linalg.norm(midpoint)) <= 5e-14:
        azimuth = 0.0
    else:
        azimuth = math.atan2(float(midpoint[1]), float(midpoint[0])) % (2.0 * math.pi)
    width = 2.0 * math.pi / sector_count
    return min(int(azimuth / width), sector_count - 1)


def _axial_separation_deg(first: np.ndarray, second: np.ndarray) -> float:
    cosine = float(np.clip(abs(float(np.dot(first, second))), 0.0, 1.0))
    return math.degrees(math.acos(cosine))


def _zone_relationship(
    normal: np.ndarray,
    selected: Sequence[TattooCandidate],
    recipe: TattooRecipe,
) -> float:
    if not selected:
        return 0.0
    polar_limit = 2.0 * math.atan(recipe.crop_radius) - math.radians(
        recipe.zone_interior_margin_deg
    )
    qualifying = 0
    for prior in selected:
        crossing = np.cross(normal, prior.normal_sample)
        crossing /= np.linalg.norm(crossing)
        if crossing[2] < 0.0:
            crossing *= -1.0
        elif abs(float(crossing[2])) <= 5e-14:
            crossing = _canonical_axial_normal(crossing)
        polar_angle = math.acos(float(np.clip(crossing[2], -1.0, 1.0)))
        if polar_angle <= polar_limit + 5e-14:
            qualifying += 1
    return float(qualifying / len(selected))


def _candidate_scores(
    candidate: TattooCandidate,
    selected: Sequence[TattooCandidate],
    used_sectors: set[int],
    max_half_width: float,
    recipe: TattooRecipe,
) -> tuple[dict[str, float], float, float]:
    separations = [
        _axial_separation_deg(candidate.normal_sample, prior.normal_sample)
        for prior in selected
    ]
    minimum_separation = min(separations, default=90.0)
    components = {
        "strength": float(candidate.normalized_weight),
        "angular_width": float(candidate.bragg_half_width_rad / max_half_width),
        "nonredundancy": float(min(minimum_separation / 90.0, 1.0)),
        "coverage": float(candidate.midpoint_sector not in used_sectors),
        "zone_relationship": _zone_relationship(candidate.normal_sample, selected, recipe),
    }
    total = sum(recipe.score_weights[name] * components[name] for name in _SCORE_NAMES)
    return components, float(total), minimum_separation


def _tier_assignments(recipe: TattooRecipe) -> tuple[tuple[TattooTier, float], ...]:
    result: list[tuple[TattooTier, float]] = []
    for tier in _TIER_ORDER:
        count = recipe.path_allocation[tier]
        widths = recipe.stroke_widths_mm[tier]
        if len(widths) != count:
            raise ValueError(f"{tier} widths must match its path allocation")
        result.extend((tier, width) for width in widths)
    return tuple(result)


def select_tattoo_paths(
    catalog: ArtBandCatalog,
    recipe: TattooRecipe,
) -> TattooSelection:
    """Select the approved 11-path hierarchy from rotated eligible bands."""
    if not isinstance(catalog, ArtBandCatalog):
        raise TypeError("catalog must be an ArtBandCatalog")
    if not isinstance(recipe, TattooRecipe):
        raise TypeError("recipe must be a TattooRecipe")
    rotation = orientation_matrix(recipe.orientation)
    candidates: list[TattooCandidate] = []
    rejections: dict[str, str] = {}
    score_history: dict[str, list[dict[str, object]]] = {}
    for member in catalog.members:
        score_history[member.member_id] = []
        if not member.tattoo_eligible:
            rejections[member.member_id] = "tattoo_ineligible"
            continue
        normal_sample = rotation @ member.normal_crystal
        circle, trace = _center_trace(normal_sample, recipe.great_circle_samples)
        candidates.append(
            TattooCandidate(
                member_id=member.member_id,
                hkl=member.hkl,
                normalized_weight=member.normalized_weight,
                bragg_half_width_rad=member.bragg_half_width_rad,
                normal_crystal=member.normal_crystal,
                normal_sample=normal_sample,
                great_circle_sample=circle,
                center_trace=trace,
                midpoint_sector=_midpoint_sector(trace, recipe.coverage_sectors),
            )
        )

    target_count = sum(recipe.path_allocation.values())
    if len(candidates) < target_count:
        raise ValueError(
            f"tattoo catalog has {len(candidates)} eligible candidates; "
            f"{target_count} are required"
        )
    max_half_width = max(candidate.bragg_half_width_rad for candidate in candidates)
    remaining = list(candidates)
    selected_candidates: list[TattooCandidate] = []
    selected_scores: dict[str, tuple[dict[str, float], float]] = {}
    used_sectors: set[int] = set()
    iteration = 0
    while len(selected_candidates) < target_count:
        iteration += 1
        ranked: list[tuple[TattooCandidate, dict[str, float], float]] = []
        survivors: list[TattooCandidate] = []
        for candidate in remaining:
            components, total, separation = _candidate_scores(
                candidate,
                selected_candidates,
                used_sectors,
                max_half_width,
                recipe,
            )
            score_history[candidate.member_id].append(
                {
                    "iteration": iteration,
                    "score_components": components,
                    "total_score": total,
                    "minimum_axial_separation_deg": separation,
                }
            )
            if separation < recipe.redundancy_threshold_deg:
                rejections[candidate.member_id] = "angular_redundancy"
                continue
            survivors.append(candidate)
            ranked.append((candidate, components, total))
        if not ranked:
            raise ValueError(
                "tattoo catalog cannot supply 11 candidates after the hard "
                "4 degree axial-redundancy threshold"
            )
        winner, components, total = sorted(
            ranked,
            key=lambda item: (
                -item[2],
                -item[0].normalized_weight,
                item[0].member_id,
            ),
        )[0]
        selected_candidates.append(winner)
        selected_scores[winner.member_id] = (components, total)
        used_sectors.add(winner.midpoint_sector)
        remaining = [candidate for candidate in survivors if candidate is not winner]

    for candidate in remaining:
        rejections[candidate.member_id] = "allocation_complete"

    selected_paths = []
    assignments = _tier_assignments(recipe)
    selected_ledger: dict[str, dict[str, object]] = {}
    for candidate, (tier, width) in zip(selected_candidates, assignments, strict=True):
        components, total = selected_scores[candidate.member_id]
        selected_paths.append(
            SelectedTattooPath(
                member_id=candidate.member_id,
                tier=tier,
                width_mm=width,
                normal_sample=candidate.normal_sample,
                center_trace=candidate.center_trace,
                score_components=components,
                total_score=total,
                selection_reason="highest ranked nonredundant center trace",
            )
        )
        selected_ledger[candidate.member_id] = {
            "tier": tier,
            "width_mm": width,
            "selection_reason": "highest ranked nonredundant center trace",
        }

    ledger = {
        "schema_version": 1,
        "catalog_id": catalog.catalog_id,
        "recipe_id": recipe.recipe_id,
        "orientation_id": recipe.orientation.orientation_id,
        "rotation_contract": (
            "normal_sample = orientation_matrix(recipe.orientation) @ normal_crystal"
        ),
        "great_circle_samples": recipe.great_circle_samples,
        "upper_arc_policy": (
            "contiguous cyclic upper-hemisphere interval; an equatorial great "
            "circle is retained as the full closed circle"
        ),
        "score_weights": dict(recipe.score_weights),
        "candidate_scores": score_history,
        "rejections": rejections,
        "selection_order": [candidate.member_id for candidate in selected_candidates],
        "selected": selected_ledger,
    }
    return TattooSelection(
        catalog_id=catalog.catalog_id,
        recipe_id=recipe.recipe_id,
        orientation_id=recipe.orientation.orientation_id,
        candidates=tuple(candidates),
        selected_paths=tuple(selected_paths),
        ledger=ledger,
    )


__all__ = [
    "SelectedTattooPath",
    "TattooCandidate",
    "TattooSelection",
    "select_tattoo_paths",
]

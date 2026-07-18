"""Analytic, antipodally symmetric raised-ridge fields on the unit sphere."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.reflector_globe.recipes import ReflectorRidgeRecipe
from kikuchi_lab.reflectors.contracts import ReflectorCatalog


@dataclass(frozen=True)
class RidgeFieldMember:
    """One selected member's reproducible corridor parameters."""

    member_id: str
    cohort: int
    height_mm: float
    effective_half_width_rad: float


@dataclass(frozen=True)
class RidgeField:
    """Normalized field values plus the complete analytic contributor ledger."""

    values: np.ndarray
    contributor_counts: np.ndarray
    field_id: str
    ledger: tuple[RidgeFieldMember, ...]


def corridor_profile(
    distance_rad: np.ndarray, half_width_rad: float, fillet_fraction: float
) -> np.ndarray:
    """Return a flat-centered, cosine-filleted corridor in the interval [0, 1]."""
    if not math.isfinite(half_width_rad) or half_width_rad <= 0.0:
        raise ValueError("half_width_rad must be a positive finite number")
    if not math.isfinite(fillet_fraction) or not 0.0 < fillet_fraction <= 1.0:
        raise ValueError("fillet_fraction must be in (0, 1]")
    x = np.abs(np.asarray(distance_rad, dtype=np.float64)) / half_width_rad
    flat = 1.0 - fillet_fraction
    return np.where(
        x <= flat,
        1.0,
        np.where(
            x < 1.0,
            0.5 * (1.0 + np.cos(np.pi * (x - flat) / fillet_fraction)),
            0.0,
        ),
    )


def bounded_union(contributions: np.ndarray) -> np.ndarray:
    """Combine normalized raised contributions without additive overshoot."""
    array = np.asarray(contributions, dtype=np.float64)
    if array.ndim < 1:
        raise ValueError("contributions must have a contributor axis")
    return 1.0 - np.prod(1.0 - np.clip(array, 0.0, 1.0), axis=0)


def _unit_directions(directions: object) -> np.ndarray:
    try:
        array = np.asarray(directions, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("directions must be a finite N-by-3 array of unit directions") from error
    if array.ndim != 2 or array.shape[1] != 3 or not np.isfinite(array).all():
        raise ValueError("directions must be a finite N-by-3 array of unit directions")
    if not np.allclose(np.linalg.vector_norm(array, axis=1), 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("directions must be unit directions")
    return array


def _field_array(values: np.ndarray, *, dtype: np.dtype[np.generic]) -> np.ndarray:
    array = np.ascontiguousarray(values, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


def evaluate_reflector_ridges(
    catalog: ReflectorCatalog, recipe: ReflectorRidgeRecipe, directions: object
) -> RidgeField:
    """Evaluate raised great-circle corridors from eligible reflector evidence only."""
    if not isinstance(catalog, ReflectorCatalog):
        raise TypeError("catalog must be a ReflectorCatalog")
    if not isinstance(recipe, ReflectorRidgeRecipe):
        raise TypeError("recipe must be a ReflectorRidgeRecipe")
    samples = _unit_directions(directions)
    base_radius_mm = recipe.geometry.base_diameter_mm / 2.0
    contributions: list[np.ndarray] = []
    ledger: list[RidgeFieldMember] = []
    for member in catalog.members:
        if not member.eligible:
            continue
        normal = np.asarray(member.normal_crystal, dtype=np.float64)
        if (
            normal.shape != (3,)
            or not np.isfinite(normal).all()
            or not math.isclose(
                float(np.linalg.vector_norm(normal)), 1.0, rel_tol=0.0, abs_tol=1e-12
            )
        ):
            raise ValueError(f"selected member {member.member_id} must have a finite unit normal")
        if type(member.cohort) is not int or member.cohort not in recipe.tiers:
            raise ValueError(f"selected member {member.member_id} must have a recipe tier")
        tier = recipe.tiers[member.cohort]
        effective_half_width_rad = max(
            member.bragg_half_width_rad * tier.width_multiplier,
            tier.minimum_width_mm / base_radius_mm,
        )
        distance_rad = np.arcsin(np.clip(samples @ normal, -1.0, 1.0))
        profile = corridor_profile(
            distance_rad, effective_half_width_rad, tier.edge_fillet_fraction
        )
        contributions.append(profile * (tier.height_mm / recipe.geometry.maximum_relief_mm))
        ledger.append(
            RidgeFieldMember(
                member_id=member.member_id,
                cohort=member.cohort,
                height_mm=tier.height_mm,
                effective_half_width_rad=effective_half_width_rad,
            )
        )
    matrix = np.asarray(contributions, dtype=np.float64)
    if matrix.size == 0:
        matrix = np.zeros((0, len(samples)), dtype=np.float64)
    values = bounded_union(matrix)
    counts = np.sum(matrix > 0.0, axis=0, dtype=np.int64)
    frozen_ledger = tuple(ledger)
    field_id = stable_id(
        "reflector-ridge-field",
        {
            "catalog_id": catalog.catalog_id,
            "recipe_id": recipe.recipe_id,
            "members": [
                {
                    "member_id": item.member_id,
                    "cohort": item.cohort,
                    "height_mm": item.height_mm,
                    "effective_half_width_rad": item.effective_half_width_rad,
                }
                for item in frozen_ledger
            ],
        },
    )
    return RidgeField(
        values=_field_array(values, dtype=np.dtype("<f8")),
        contributor_counts=_field_array(counts, dtype=np.dtype("<i8")),
        field_id=field_id,
        ledger=frozen_ledger,
    )


__all__ = [
    "RidgeField",
    "RidgeFieldMember",
    "bounded_union",
    "corridor_profile",
    "evaluate_reflector_ridges",
]

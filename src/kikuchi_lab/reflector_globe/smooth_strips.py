"""Explicit smooth swept-strip meshes for reflector ridge globes.

This module avoids the jagged ridge-margin artifact caused by sampling a sharp
band edge on an unrelated icosphere topology.  Each selected reflector is
represented as a high-resolution spherical strip whose long edges are generated
directly from the analytic great-circle geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import trimesh

from kikuchi_lab.reflector_globe.field import RidgeFieldMember
from kikuchi_lab.reflector_globe.recipes import ReflectorRidgeRecipe
from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember


@dataclass(frozen=True)
class SmoothStripMesh:
    """Combined preview/print mesh plus analytic strip provenance."""

    mesh: trimesh.Trimesh
    ledger: tuple[RidgeFieldMember, ...]
    strip_count: int
    base_radius_mm: float
    maximum_radius_mm: float
    angular_segments: int
    cross_segments: int


def _basis_from_normal(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = np.asarray(normal, dtype=np.float64)
    n = n / np.linalg.norm(n)
    seed = np.array([1.0, 0.0, 0.0])
    if abs(float(seed @ n)) > 0.9:
        seed = np.array([0.0, 1.0, 0.0])
    a = seed - float(seed @ n) * n
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    b /= np.linalg.norm(b)
    return a, b, n


def _profile(signed_offset_rad: np.ndarray, half_width_rad: float, fillet_fraction: float) -> np.ndarray:
    x = np.abs(signed_offset_rad) / half_width_rad
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


def _faces_grid(rows: int, cols: int, *, offset: int = 0, reverse: bool = False) -> list[list[int]]:
    faces: list[list[int]] = []
    for row in range(rows - 1):
        for col in range(cols):
            nxt = (col + 1) % cols
            a = offset + row * cols + col
            b = offset + row * cols + nxt
            c = offset + (row + 1) * cols + col
            d = offset + (row + 1) * cols + nxt
            if reverse:
                faces.extend(([a, c, b], [b, c, d]))
            else:
                faces.extend(([a, b, c], [b, d, c]))
    return faces


def _strip_mesh(
    member: ReflectorMember,
    ridge: RidgeFieldMember,
    recipe: ReflectorRidgeRecipe,
    *,
    angular_segments: int,
    cross_segments: int,
) -> trimesh.Trimesh:
    base_radius = recipe.geometry.base_diameter_mm / 2.0
    underside_radius = base_radius - min(0.6, 0.15 * recipe.geometry.maximum_relief_mm)
    tier = recipe.tiers[ridge.cohort]
    a, b, n = _basis_from_normal(member.normal_crystal)
    theta = np.linspace(0.0, 2.0 * math.pi, angular_segments, endpoint=False)
    offsets = np.linspace(-ridge.effective_half_width_rad, ridge.effective_half_width_rad, cross_segments)
    profile = _profile(offsets, ridge.effective_half_width_rad, tier.edge_fillet_fraction)

    center = np.cos(theta)[:, None] * a + np.sin(theta)[:, None] * b
    top_vertices: list[np.ndarray] = []
    bottom_vertices: list[np.ndarray] = []
    for offset, weight in zip(offsets, profile, strict=True):
        directions = math.cos(float(offset)) * center + math.sin(float(offset)) * n
        directions /= np.linalg.norm(directions, axis=1)[:, None]
        top_vertices.append(directions * (base_radius + ridge.height_mm * float(weight)))
        bottom_vertices.append(directions * underside_radius)
    top = np.vstack(top_vertices)
    bottom = np.vstack(bottom_vertices)
    vertices = np.vstack((top, bottom))
    faces = _faces_grid(cross_segments, angular_segments)
    faces.extend(_faces_grid(cross_segments, angular_segments, offset=len(top), reverse=True))

    # Close the two long sides of the strip.  The top and bottom coincide at the
    # zero-height edge, but explicit side faces make each strip a complete shell
    # for slicers that inspect bodies independently.
    bottom_offset = len(top)
    for row in (0, cross_segments - 1):
        for col in range(angular_segments):
            nxt = (col + 1) % angular_segments
            t0 = row * angular_segments + col
            t1 = row * angular_segments + nxt
            b0 = bottom_offset + t0
            b1 = bottom_offset + t1
            if row == 0:
                faces.extend(([t0, b0, t1], [t1, b0, b1]))
            else:
                faces.extend(([t0, t1, b0], [t1, b1, b0]))

    return trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
        validate=False,
    )


def selected_ridge_ledger(
    catalog: ReflectorCatalog, recipe: ReflectorRidgeRecipe
) -> tuple[RidgeFieldMember, ...]:
    """Return the same physical selected-ridge parameters used by field sampling."""
    base_radius_mm = recipe.geometry.base_diameter_mm / 2.0
    ledger: list[RidgeFieldMember] = []
    for member in catalog.members:
        if not member.eligible:
            continue
        if type(member.cohort) is not int or member.cohort not in recipe.tiers:
            raise ValueError(f"selected member {member.member_id} must have a recipe tier")
        tier = recipe.tiers[member.cohort]
        effective_half_width_rad = max(
            member.bragg_half_width_rad * tier.width_multiplier,
            tier.minimum_width_mm / base_radius_mm,
        )
        ledger.append(
            RidgeFieldMember(
                member_id=member.member_id,
                cohort=member.cohort,
                height_mm=tier.height_mm,
                effective_half_width_rad=effective_half_width_rad,
            )
        )
    if not ledger:
        raise ValueError("smooth strip mesh requires at least one selected member")
    return tuple(ledger)


def build_smooth_strip_mesh(
    catalog: ReflectorCatalog,
    recipe: ReflectorRidgeRecipe,
    *,
    base_subdivisions: int = 6,
    angular_segments: int = 720,
    cross_segments: int = 17,
) -> SmoothStripMesh:
    """Build a smooth base sphere plus explicit swept reflector ridge strips."""
    if cross_segments < 5 or cross_segments % 2 == 0:
        raise ValueError("cross_segments must be an odd integer >= 5")
    if angular_segments < 64:
        raise ValueError("angular_segments must be at least 64")
    base_radius = recipe.geometry.base_diameter_mm / 2.0
    base = trimesh.creation.icosphere(subdivisions=base_subdivisions, radius=base_radius)
    base.process(validate=False)
    ledger = selected_ridge_ledger(catalog, recipe)
    members = {member.member_id: member for member in catalog.members}
    strips = [
        _strip_mesh(
            members[item.member_id],
            item,
            recipe,
            angular_segments=angular_segments,
            cross_segments=cross_segments,
        )
        for item in ledger
    ]
    mesh = trimesh.util.concatenate((base, *strips))
    return SmoothStripMesh(
        mesh=mesh,
        ledger=ledger,
        strip_count=len(strips),
        base_radius_mm=base_radius,
        maximum_radius_mm=base_radius + recipe.geometry.maximum_relief_mm,
        angular_segments=angular_segments,
        cross_segments=cross_segments,
    )


__all__ = ["SmoothStripMesh", "build_smooth_strip_mesh", "selected_ridge_ledger"]

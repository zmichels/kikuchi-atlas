"""Crystallographic expansion boundary for crystal-habit face families."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from diffpy.structure import Lattice
from orix.crystal_map import Phase
from orix.vector import Vector3d

from kikuchi_lab.habit.recipes import HabitRecipe
from kikuchi_lab.model.identity import stable_id

_FRAME = "X||a*, Y||cross(c,a*), Z||c"


@dataclass(frozen=True)
class CrystalPhase:
    name: str
    formula: str
    space_group_number: int
    point_group: str
    lattice_angstrom: tuple[float, float, float, float, float, float]
    frame: str
    cif_sha256: str


@dataclass(frozen=True)
class ExpandedPlane:
    plane_id: str
    family_label: str
    family_indices: tuple[int, ...]
    symmetry_index: int
    normal: tuple[float, float, float]
    relative_distance: float


def _hkl(indices: tuple[int, ...], convention: str) -> np.ndarray:
    if convention == "hkil":
        h, k, i, ell = indices
        if h + k + i != 0:
            raise ValueError("hkil family requires h + k + i = 0")
        return np.array([h, k, ell], dtype=np.float64)
    return np.array(indices, dtype=np.float64)


def _frame_matrix(lattice: Lattice) -> np.ndarray:
    a_star = lattice.recbase @ np.array([1.0, 0.0, 0.0])
    c_axis = lattice.cartesian([0.0, 0.0, 1.0])
    x = a_star / np.linalg.norm(a_star)
    z = c_axis / np.linalg.norm(c_axis)
    y = np.cross(z, x)
    y /= np.linalg.norm(y)
    return np.vstack([x, y, z])


def _deduplicate_and_sort_unit_normals(
    normals: np.ndarray, tolerance: float
) -> tuple[np.ndarray, ...]:
    unit_normals: list[np.ndarray] = []
    for candidate in np.asarray(normals, dtype=np.float64).reshape(-1, 3):
        magnitude = np.linalg.norm(candidate)
        if not np.isfinite(magnitude) or magnitude <= tolerance:
            raise ValueError("zero reciprocal-plane normal")
        unit_normals.append(candidate / magnitude)

    decimals = max(0, int(round(-np.log10(tolerance))))
    ordered = sorted(unit_normals, key=lambda normal: tuple(np.round(normal, decimals)))
    unique: list[np.ndarray] = []
    for candidate in ordered:
        if not any(
            np.allclose(candidate, existing, atol=tolerance, rtol=0.0)
            for existing in unique
        ):
            unique.append(candidate)
    return tuple(unique)


def _plain_phase(recipe: HabitRecipe, upstream: Phase) -> CrystalPhase:
    lattice = upstream.structure.lattice
    return CrystalPhase(
        name=recipe.phase.name,
        formula=recipe.phase.formula,
        space_group_number=recipe.phase.space_group_number,
        point_group=str(upstream.point_group.name),
        lattice_angstrom=tuple(float(value) for value in lattice.cell_parms()),
        frame=_FRAME,
        cif_sha256=recipe.phase.cif_sha256,
    )


def expand_habit_planes(
    recipe: HabitRecipe,
) -> tuple[CrystalPhase, tuple[ExpandedPlane, ...]]:
    upstream = Phase.from_cif(recipe.phase.cif_path)
    if (
        upstream.space_group is None
        or upstream.space_group.number != recipe.phase.space_group_number
    ):
        raise ValueError("CIF space group disagrees with habit recipe")

    lattice = upstream.structure.lattice
    frame = _frame_matrix(lattice)
    expanded: list[ExpandedPlane] = []
    for family in recipe.faces:
        reciprocal = lattice.recbase @ _hkl(family.family, recipe.index_convention)
        magnitude = np.linalg.norm(reciprocal)
        if not np.isfinite(magnitude) or magnitude <= 1e-12:
            raise ValueError("zero reciprocal-plane normal")
        reciprocal /= magnitude
        native_orbit = upstream.point_group.outer(Vector3d(reciprocal)).data.reshape(
            -1, 3
        )
        orbit = (frame @ native_orbit.T).T
        ordered_orbit = _deduplicate_and_sort_unit_normals(orbit, tolerance=1e-12)
        for symmetry_index, normal in enumerate(ordered_orbit):
            content = {
                "family_label": family.label,
                "family_indices": list(family.family),
                "symmetry_index": symmetry_index,
                "normal": normal.tolist(),
                "relative_distance": family.relative_distance,
            }
            expanded.append(
                ExpandedPlane(
                    plane_id=stable_id("habit-plane", content),
                    family_label=family.label,
                    family_indices=family.family,
                    symmetry_index=symmetry_index,
                    normal=tuple(float(value) for value in normal),
                    relative_distance=family.relative_distance,
                )
            )
    return _plain_phase(recipe, upstream), tuple(expanded)

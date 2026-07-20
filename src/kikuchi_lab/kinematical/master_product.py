"""Canonical spherical-field exports from retained kinematical Lambert masters."""

from __future__ import annotations

import hashlib
from importlib.metadata import version

import numpy as np

from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.model.products import MasterPatternProduct
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import KinematicalArrayProduct, KinematicalRecipe
from .kikuchipy_adapter import _phase_from_record


_EQUATOR_TOLERANCE = 1e-6
_LOWER_GRID_TRANSFORMS = (
    ("identity", lambda grid: grid),
    ("flip-left-right", np.fliplr),
    ("flip-top-bottom", np.flipud),
    ("rotate-180", lambda grid: np.rot90(grid, 2)),
)


def _recipe_sha256(recipe: KinematicalRecipe) -> str:
    payload = recipe.to_dict()
    del payload["source_record"]
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_retained_master(
    master: KinematicalArrayProduct,
    *,
    source: StructureRecord,
    recipe: KinematicalRecipe,
) -> None:
    if master.label != "master-lambert":
        raise ValueError("canonical export requires the retained master-lambert product")
    if (
        master.intensity.ndim != 3
        or master.intensity.shape[0] != 2
        or master.intensity.shape[1] != master.intensity.shape[2]
        or master.intensity.shape[1] < 3
        or master.intensity.shape[1] % 2 != 1
    ):
        raise ValueError("retained Lambert master must have shape (2, odd N, odd N)")
    metadata = master.metadata
    if metadata.get("projection") != "lambert-square-equal-area":
        raise ValueError("retained source must be a Lambert square master")
    if metadata.get("hemisphere") != "both":
        raise ValueError("retained source must contain both hemispheres")
    if metadata.get("source_id") != source.source_record.source_id:
        raise ValueError("retained source ID disagrees with the structure record")
    if metadata.get("source_sha256") != source.sha256:
        raise ValueError("retained source SHA-256 disagrees with the structure record")
    if metadata.get("recipe_id") != recipe.recipe_id:
        raise ValueError("retained source recipe ID disagrees with the requested recipe")
    if metadata.get("energy_kev") != recipe.energy_kev:
        raise ValueError("retained source energy disagrees with the requested recipe")


def _canonical_lambert_array(master: KinematicalArrayProduct) -> tuple[np.ndarray, dict[str, object]]:
    """Align the retained lower slab to the upper slab at the equator.

    kikuchipy retains its own square-grid convention for each stereographic
    hemisphere.  The raw lower slab therefore needs a documented in-plane
    dihedral alignment before it can be consumed as one continuous spherical
    Lambert field.  The physical invariant is exact equality at the shared
    equator; no intensities are interpolated or otherwise altered.
    """
    north = np.asarray(master.intensity[0], dtype=np.float32)
    lower_raw = np.asarray(master.intensity[1], dtype=np.float32)
    boundary = np.zeros(north.shape, dtype=bool)
    boundary[[0, -1], :] = True
    boundary[:, [0, -1]] = True
    scale = max(float(np.ptp(master.intensity)), float(np.finfo(np.float32).eps))

    candidates: list[tuple[float, int, str, np.ndarray]] = []
    for priority, (name, transform) in enumerate(_LOWER_GRID_TRANSFORMS):
        lower = np.ascontiguousarray(transform(lower_raw))
        residual = float(np.max(np.abs(north[boundary] - lower[boundary])))
        candidates.append((residual / scale, priority, name, lower))
    normalized_residual, _, operation, lower = min(candidates, key=lambda item: item[:2])
    if normalized_residual > _EQUATOR_TOLERANCE:
        raise ValueError(
            "retained Lambert hemispheres cannot be aligned at the equator: "
            f"{normalized_residual:.17g} > {_EQUATOR_TOLERANCE:.17g}"
        )
    aligned = np.ascontiguousarray(np.stack((north, lower)), dtype=np.float32)
    return aligned, {
        "source_hemisphere_order": ["upper", "lower"],
        "canonical_hemisphere_order": ["north", "south"],
        "upper_operation": "identity",
        "lower_operation": operation,
        "selection": "minimum normalized equator residual among supported in-plane transforms",
        "normalized_equator_residual": normalized_residual,
        "tolerance": _EQUATOR_TOLERANCE,
    }


def canonical_master_product(
    master: KinematicalArrayProduct,
    *,
    source: StructureRecord,
    recipe: KinematicalRecipe,
) -> MasterPatternProduct:
    """Wrap a verified Lambert master in the common spherical-field contract.

    Raw retained samples are never recalculated. The lower slab is only
    re-indexed by a recorded in-plane transform so both slabs describe one
    continuous north/south Lambert field at their shared equator.
    """
    _validate_retained_master(master, source=source, recipe=recipe)
    intensity, hemisphere_grid_alignment = _canonical_lambert_array(master)
    recipe_sha256 = _recipe_sha256(recipe)
    if recipe.recipe_id != f"recipe-{recipe_sha256[:16]}":
        raise ValueError("kinematical recipe ID disagrees with its canonical payload")
    lattice = tuple(
        float(value)
        for value in _phase_from_record(source).structure.lattice.cell_parms()
    )
    metadata = {
        "phase": {
            "name": source.name,
            "formula": source.formula,
            "space_group": {
                "number": source.space_group_number,
                "setting": source.simulation_setting["target_setting"],
            },
            "lattice": {"values": list(lattice), "units": "angstrom"},
        },
        "source_structure": {
            "identifier": source.identifier,
            "sha256": source.sha256,
            "source_id": source.source_record.source_id,
            "retrieved": source.retrieved,
            "page_uri": source.page_uri,
            "provenance": source.source_record.to_dict(),
            "thermal_factor_policy": source.thermal_factor_policy,
            "simulation_setting": source.simulation_setting,
        },
        "generator": {
            "name": "kikuchi-lab kinematical Lambert exporter",
            "version": f"kikuchipy {version('kikuchipy')}; diffsims {version('diffsims')}",
        },
        "simulation": {
            "recipe_id": recipe.recipe_id,
            "recipe_sha256": recipe_sha256,
            "voltage_kv": recipe.energy_kev,
            "tier": "kinematical",
            "source_product_id": master.product_id,
            "source_array_sha256": master.array_sha256,
        },
        "projection": "Lambert square equal-area",
        "hemisphere_order": ["north", "south"],
        "hemisphere_grid_alignment": hemisphere_grid_alignment,
        "energy_kev": recipe.energy_kev,
        "intensity_units": "kinematical intensity proportional to |F_hkl|^2",
        "coordinate_frame": (
            "crystal:" + str(source.simulation_setting["target_setting"])
            + "; right-handed direct and reciprocal Cartesian frames"
        ),
        "provenance_links": [
            source.source_record.source_id,
            recipe.recipe_id,
            master.product_id,
            master.array_sha256,
        ],
    }
    return MasterPatternProduct.from_array(intensity, metadata=metadata)


__all__ = ["canonical_master_product"]

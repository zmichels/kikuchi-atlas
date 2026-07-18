"""Adapter-local diffsims and kikuchipy calls for the bounded Ice master."""

from __future__ import annotations

import math
from importlib.metadata import version
from typing import Any

import numpy as np
from diffsims.crystallography import ReciprocalLatticeVector
from kikuchipy.simulations import KikuchiPatternSimulator
from numba import get_num_threads, set_num_threads
from orix.crystal_map import Phase

from kikuchi_lab.projection.kikuchipy_adapter import transform_crystal_direction_to_sample
from kikuchi_lab.reflectors.catalog import build_reflector_catalog
from kikuchi_lab.reflectors.diffsims_adapter import _allowed_mask as _catalog_allowed_mask
from kikuchi_lab.reflectors.diffsims_adapter import _phase_from_record as _catalog_phase_from_record
from kikuchi_lab.reflectors.recipe import ReflectorRecipe
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import KinematicalArrayProduct, KinematicalRecipe, KinematicalSimulation


def _phase_from_record(record: StructureRecord) -> Phase:
    """Use the verified Ice source conversion already owned by the catalog adapter."""
    return _catalog_phase_from_record(record)


def _allowed_mask(reflectors: ReciprocalLatticeVector) -> np.ndarray:
    """Keep primitive-hexagonal vectors when diffsims lacks an allowed shortcut."""
    return _catalog_allowed_mask(reflectors)


def _master_reflectors(
    source: StructureRecord, reflector_recipe: ReflectorRecipe
) -> ReciprocalLatticeVector:
    """Recover the recorded 0.03 source-master gate from catalog evidence."""
    phase = _phase_from_record(source)
    vectors = ReciprocalLatticeVector.from_min_dspacing(
        phase, min_dspacing=reflector_recipe.min_dspacing_angstrom
    )
    vectors = vectors[_allowed_mask(vectors)].unique(use_symmetry=True).symmetrise()
    vectors.sanitise_phase()
    vectors.calculate_structure_factor(scattering_params=reflector_recipe.scattering_params)
    amplitudes = np.abs(np.asarray(vectors.structure_factor, dtype=np.complex128))
    if not amplitudes.size or not np.isfinite(amplitudes).all() or float(amplitudes.max()) <= 0:
        raise ValueError("catalog evidence produced no finite reflection strengths")
    selected = vectors[
        amplitudes >= reflector_recipe.source_master_relative_factor * float(amplitudes.max())
    ]
    selected.calculate_theta(reflector_recipe.energy_kev * 1_000.0)
    return selected


def _calculate_master(simulator: KikuchiPatternSimulator, recipe: KinematicalRecipe) -> Any:
    """Bound numba accumulation while preserving the upstream public calculation."""
    workers = get_num_threads()
    try:
        set_num_threads(1)
        return simulator.calculate_master_pattern(
            half_size=recipe.half_size,
            hemisphere=recipe.hemisphere,
            scaling=recipe.scaling,
        )
    finally:
        set_num_threads(workers)


def _known_axis_check(source: StructureRecord, recipe: KinematicalRecipe) -> dict[str, object]:
    lattice = _phase_from_record(source).structure.lattice
    crystal = np.asarray(lattice.cartesian(recipe.zone_axis_uvw), dtype=float)
    crystal /= np.linalg.norm(crystal)
    sample = transform_crystal_direction_to_sample(crystal, recipe.orientation)
    sample /= np.linalg.norm(sample)
    expected = np.asarray((0.0, 0.0, 1.0))
    angle = math.degrees(math.acos(float(np.clip(np.dot(sample, expected), -1.0, 1.0))))
    return {
        "zone_axis_uvw": list(recipe.zone_axis_uvw),
        "crystal_direction_unit": crystal.tolist(),
        "active_crystal_to_sample_direction": sample.tolist(),
        "expected_sample_direction": expected.tolist(),
        "misalignment_deg": angle,
        "angle_units": "degree",
    }


def _projection_ledger(
    source: StructureRecord, recipe: KinematicalRecipe, reflector_recipe: ReflectorRecipe
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_method": {
            "phase_source_id": source.source_record.source_id,
            "reflection_engine": {"name": "diffsims", "version": version("diffsims")},
            "projection_engine": {"name": "kikuchipy", "version": version("kikuchipy")},
            "reflector_recipe_id": reflector_recipe.recipe_id,
        },
        "frames": {
            "crystal": f"{source.simulation_setting['target_setting']} direct and reciprocal Cartesian frames",
            "orientation": recipe.orientation.to_dict(),
            "sample": "EDAX-TSL [RD, TD, ND]",
            "handedness": "right-handed",
            "source_to_crystal": {
                "source_setting": source.setting,
                "target_setting": source.simulation_setting["target_setting"],
                "lattice_transform": {
                    "target_from_source": source.simulation_setting["target_lattice_from_source"]
                },
                "fractional_coordinate_transform": {
                    "target_from_source": source.simulation_setting["target_fractional_from_source"]
                },
            },
        },
        "projections": {
            "stereographic": {
                "hemisphere": "both",
                "hemisphere_order": ["upper", "lower"],
                "origin": "projection center",
                "grid_formula": "coordinate[k] = -1 + 2*k/(N-1)",
                "valid_domain": "X^2 + Y^2 <= 1",
                "transform_owner": "kikuchipy.KikuchiPatternSimulator.calculate_master_pattern",
            }
        },
        "known_axis_check": _known_axis_check(source, recipe),
    }


def simulate_kinematical_master(
    source: StructureRecord, recipe: KinematicalRecipe, reflector_recipe: ReflectorRecipe
) -> KinematicalSimulation:
    """Produce one finite, two-hemisphere owned master from recorded evidence."""
    if recipe.energy_kev != reflector_recipe.energy_kev:
        raise ValueError("kinematical and reflector recipes must use the same energy")
    catalog = build_reflector_catalog(source, reflector_recipe)
    reflectors = _master_reflectors(source, reflector_recipe)
    signal = _calculate_master(KikuchiPatternSimulator(reflectors), recipe)
    metadata = {
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "recipe_id": recipe.recipe_id,
        "reflector_recipe_id": reflector_recipe.recipe_id,
        "reflector_catalog_id": catalog.catalog_id,
        "energy_kev": recipe.energy_kev,
        "projection": "stereographic",
        "hemisphere": "both",
        "intensity_meaning": "kinematical band intensity proportional to |F_hkl|^2",
        "provenance_links": [
            source.source_record.source_id,
            recipe.recipe_id,
            reflector_recipe.recipe_id,
            catalog.catalog_id,
            f"sha256:{source.sha256}",
        ],
    }
    evidence = {
        "catalog_id": catalog.catalog_id,
        "reflection_recipe_id": catalog.reflection_recipe_id,
        "selection": dict(catalog.selection),
        "member_count": len(catalog.members),
        "master_retained_count": int(reflectors.size),
        "master_threshold": {
            "relative_factor": reflector_recipe.source_master_relative_factor,
            "source": "reflector catalog selection evidence",
        },
    }
    return KinematicalSimulation(
        master_stereographic=KinematicalArrayProduct.from_array(
            "master-stereographic", signal.data, metadata=metadata
        ),
        reflector_catalog=evidence,
        projection_ledger=_projection_ledger(source, recipe, reflector_recipe),
    )

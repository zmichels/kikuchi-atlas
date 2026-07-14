"""Private adapters for the public diffsims kinematical reflection APIs."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import version
from types import MappingProxyType
from typing import Any

import numpy as np
from diffpy.structure import Atom, Lattice, Structure
from diffsims.crystallography import ReciprocalLatticeVector
from kikuchipy.simulations import KikuchiPatternSimulator
from numba import get_num_threads, set_num_threads
from orix.crystal_map import Phase

from kikuchi_lab.projection.kikuchipy_adapter import (
    _to_kikuchipy_detector,
    _to_kikuchipy_rotation,
    transform_crystal_direction_to_sample,
)
from kikuchi_lab.sources.structure import StructureRecord, verify_structure

from .contracts import (
    KinematicalArrayProduct,
    KinematicalExecution,
    KinematicalRecipe,
    KinematicalSimulation,
)


_SPHERICAL_CAMERA_DEG = {
    "elevation": 20.0,
    "azimuth": -35.0,
    "roll": 0.0,
}


def _calculate_master_pattern_single_worker(
    simulator: KikuchiPatternSimulator,
    *,
    half_size: int,
    hemisphere: str,
    scaling: str | None,
) -> Any:
    """Bound kikuchipy's parallel accumulation without changing its signal."""
    worker_count = get_num_threads()
    try:
        set_num_threads(1)
        return simulator.calculate_master_pattern(
            half_size=half_size,
            hemisphere=hemisphere,
            scaling=scaling,
        )
    finally:
        set_num_threads(worker_count)


@dataclass(frozen=True)
class _KikuchipyContext:
    """Upstream objects retained privately for one kinematical run."""

    master_simulator: KikuchiPatternSimulator
    overlay_simulators: Mapping[str, KikuchiPatternSimulator]
    master_signal: Any
    lambert_signal: Any
    detector_signal: Any
    detector_geometry: Any

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "overlay_simulators", MappingProxyType(dict(self.overlay_simulators))
        )


def _phase_from_record(record: StructureRecord) -> Phase:
    verify_structure(record)
    if record.simulation_setting["target_lattice_from_source"] != ["b", "c", "a"]:
        raise ValueError("unsupported kinematical lattice transform")
    if record.simulation_setting["target_fractional_from_source"] != ["y", "z", "x"]:
        raise ValueError("unsupported kinematical coordinate transform")
    a, b, c, alpha, beta, gamma = record.lattice_angstrom
    lattice = Lattice(b, c, a, beta, gamma, alpha)
    atoms = [
        Atom(
            site.element,
            xyz=(site.fract[1], site.fract[2], site.fract[0]),
            label=site.label,
            occupancy=site.occupancy,
            Uisoequiv=site.u_iso_angstrom_sq,
        )
        for site in record.sites
    ]
    return Phase(
        name=record.name,
        space_group=record.space_group_number,
        structure=Structure(atoms=atoms, lattice=lattice, title=record.name),
    )


def _enumerate_reflectors(
    phase: Phase, recipe: KinematicalRecipe
) -> ReciprocalLatticeVector:
    reflectors = ReciprocalLatticeVector.from_min_dspacing(
        phase, min_dspacing=recipe.min_dspacing_angstrom
    )
    reflectors = reflectors[reflectors.allowed]
    reflectors = reflectors.unique(use_symmetry=True).symmetrise()
    reflectors.sanitise_phase()
    reflectors.calculate_structure_factor(scattering_params=recipe.scattering_params)
    return reflectors


def _select_reflectors(
    reflectors: ReciprocalLatticeVector,
    relative_factor: float,
    energy_kev: float,
) -> ReciprocalLatticeVector:
    amplitudes = np.abs(reflectors.structure_factor)
    selected = reflectors[amplitudes >= relative_factor * float(amplitudes.max())]
    selected.calculate_theta(energy_kev * 1_000.0)
    return selected


def _reflection_catalog(
    reflectors: ReciprocalLatticeVector,
    recipe: KinematicalRecipe,
    threshold: float,
) -> dict[str, object]:
    enumerated = ReciprocalLatticeVector.from_min_dspacing(
        reflectors.phase, min_dspacing=recipe.min_dspacing_angstrom
    )
    allowed = enumerated[enumerated.allowed]
    symmetrised = allowed.unique(use_symmetry=True).symmetrise()
    reflections = [
        {
            "hkl": [int(round(float(component))) for component in hkl],
            "dspacing_angstrom": float(dspacing),
            "structure_factor_abs": float(abs(structure_factor)),
            "theta_radian": float(theta),
        }
        for hkl, dspacing, structure_factor, theta in zip(
            reflectors.hkl,
            reflectors.dspacing,
            reflectors.structure_factor,
            reflectors.theta,
            strict=True,
        )
    ]
    return {
        "units": {"dspacing": "angstrom", "theta": "radian"},
        "enumerated_count": enumerated.size,
        "allowed_count": allowed.size,
        "symmetrised_count": symmetrised.size,
        "retained_count": reflectors.size,
        "package_versions": {
            package: version(package)
            for package in ("diffpy-structure", "diffsims", "kikuchipy", "orix")
        },
        "threshold_policy": {
            "quantity": "abs(structure_factor)",
            "comparison": "greater_than_or_equal",
            "reference": "max(abs(structure_factor))",
            "relative_factor": float(threshold),
        },
        "min_dspacing_angstrom": recipe.min_dspacing_angstrom,
        "scattering_params": recipe.scattering_params,
        "energy_kev": recipe.energy_kev,
        "reflections": reflections,
    }


def _known_axis_check(
    record: StructureRecord, recipe: KinematicalRecipe
) -> dict[str, object]:
    source_a, source_b, source_c = record.lattice_angstrom[:3]
    lattice_abc = np.asarray((source_b, source_c, source_a), dtype=float)
    crystal_direction = np.asarray(recipe.zone_axis_uvw, dtype=float) * lattice_abc
    crystal_direction /= np.linalg.norm(crystal_direction)
    sample_direction = transform_crystal_direction_to_sample(
        crystal_direction, recipe.orientation
    )
    sample_direction /= np.linalg.norm(sample_direction)
    expected = np.asarray((0.0, 0.0, 1.0), dtype=float)
    cosine = float(np.clip(np.dot(sample_direction, expected), -1.0, 1.0))
    return {
        "zone_axis_uvw": list(recipe.zone_axis_uvw),
        "lattice_abc_angstrom": lattice_abc.tolist(),
        "metric_conversion": "normalize([u*a, v*b, w*c])",
        "crystal_direction_unit": crystal_direction.tolist(),
        "active_crystal_to_sample_direction": sample_direction.tolist(),
        "expected_sample_direction": expected.tolist(),
        "misalignment_deg": math.degrees(math.acos(cosine)),
        "angle_units": "degree",
    }


def _projection_ledger(
    record: StructureRecord, recipe: KinematicalRecipe
) -> dict[str, object]:
    hemisphere_order = (
        ["upper", "lower"]
        if recipe.hemisphere == "both"
        else [recipe.hemisphere]
    )
    return {
        "schema_version": 1,
        "source_method": {
            "phase_source_id": record.source_record.source_id,
            "reflection_engine": {"name": "diffsims", "version": version("diffsims")},
            "projection_engine": {
                "name": "kikuchipy",
                "version": version("kikuchipy"),
            },
        },
        "frames": {
            "crystal": "standard-Pnma direct and reciprocal Cartesian frames",
            "orientation": recipe.orientation.to_dict(),
            "sample": "EDAX-TSL [RD, TD, ND]",
            "detector": "kikuchipy EBSDDetector with explicit PC convention",
            "handedness": "right-handed",
            "units": {
                "direct_lattice": "angstrom",
                "reciprocal_lattice": "angstrom^-1",
            },
            "source_to_crystal": {
                "source_setting": record.setting,
                "target_setting": record.simulation_setting["target_setting"],
                "lattice_transform": {
                    "target_from_source": record.simulation_setting[
                        "target_lattice_from_source"
                    ],
                    "equation": "(a', b', c') = (b, c, a)",
                },
                "fractional_coordinate_transform": {
                    "target_from_source": record.simulation_setting[
                        "target_fractional_from_source"
                    ],
                    "equation": "(x', y', z') = (y, z, x)",
                },
            },
            "transform_owners": {
                "source_to_crystal": (
                    "kikuchi_lab.kinematical.kikuchipy_adapter._phase_from_record"
                ),
                "crystal_to_sample": (
                    "kikuchi_lab.projection.kikuchipy_adapter."
                    "_active_crystal_to_sample_rotation using orix"
                ),
                "sample_to_detector": "kikuchipy.EBSDDetector.sample_to_detector",
            },
        },
        "projections": {
            "stereographic": {
                "hemisphere": recipe.hemisphere,
                "hemisphere_order": hemisphere_order,
                "origin": "projection center",
                "row_axis": "Y ascending -1 to +1",
                "column_axis": "X ascending -1 to +1",
                "grid_formula": "coordinate[k] = -1 + 2*k/(N-1)",
                "valid_domain": "X^2 + Y^2 <= 1",
                "wrap": "none",
                "transform_owner": (
                    "kikuchipy.KikuchiPatternSimulator.calculate_master_pattern"
                ),
            },
            "lambert": {
                "hemisphere": recipe.hemisphere,
                "hemisphere_order": hemisphere_order,
                "origin": "square center",
                "wrap": "none",
                "transform_owner": "kikuchipy.EBSDMasterPattern.as_lambert",
            },
            "detector": {
                "projection": "gnomonic",
                "pc_convention": recipe.detector.pc_convention,
                "coordinate_units": {
                    "pixel": "pixel",
                    "gnomonic": "dimensionless",
                    "projection_center": "fraction",
                },
                "transform_owner": "kikuchipy.EBSDMasterPattern.get_patterns",
            },
            "spherical": {
                "projection": "spherical",
                "backend": "matplotlib",
                "camera_deg": dict(_SPHERICAL_CAMERA_DEG),
                "renderer_versions": {
                    "kikuchipy": version("kikuchipy"),
                    "matplotlib": version("matplotlib"),
                },
                "transform_owner": "kikuchipy.KikuchiPatternSimulator.plot",
            },
        },
        "known_axis_check": _known_axis_check(record, recipe),
        "presentation_space": ["labels", "minimum stroke width", "rim stroke"],
    }


def _product_metadata(
    record: StructureRecord,
    recipe: KinematicalRecipe,
    *,
    projection: str,
    intensity_meaning: str,
) -> dict[str, object]:
    source_id = record.source_record.source_id
    return {
        "source_id": source_id,
        "source_sha256": record.sha256,
        "recipe_id": recipe.recipe_id,
        "generators": {
            "reflection": {"name": "diffsims", "version": version("diffsims")},
            "projection": {"name": "kikuchipy", "version": version("kikuchipy")},
        },
        "energy_kev": recipe.energy_kev,
        "threshold": {
            "quantity": "abs(structure_factor)",
            "comparison": "greater_than_or_equal",
            "reference": "max(abs(structure_factor))",
            "relative_factor": recipe.master_relative_factor,
        },
        "projection": projection,
        "hemisphere": recipe.hemisphere,
        "intensity_meaning": intensity_meaning,
        "orientation": recipe.orientation.to_dict(),
        "detector": recipe.detector.to_dict(),
        "provenance_links": [
            source_id,
            recipe.recipe_id,
            f"sha256:{record.sha256}",
        ],
    }


def _catalog_with_threshold(
    reflectors: ReciprocalLatticeVector,
    recipe: KinematicalRecipe,
    threshold: float,
) -> dict[str, object]:
    return {
        "relative_factor": float(threshold),
        **_reflection_catalog(reflectors, recipe, threshold=threshold),
    }


def simulate_kinematical_arrays(
    record: StructureRecord, recipe: KinematicalRecipe
) -> tuple[KinematicalSimulation, _KikuchipyContext]:
    """Generate owned projection arrays while retaining upstream objects privately."""
    phase = _phase_from_record(record)
    reflectors = _enumerate_reflectors(phase, recipe)
    master_reflectors = _select_reflectors(
        reflectors, recipe.master_relative_factor, recipe.energy_kev
    )
    overlay_reflectors = {
        style.name: _select_reflectors(
            reflectors, style.overlay_relative_factor, recipe.energy_kev
        )
        for style in recipe.styles
    }
    master_simulator = KikuchiPatternSimulator(master_reflectors)
    overlay_simulators = {
        name: KikuchiPatternSimulator(selected)
        for name, selected in overlay_reflectors.items()
    }

    master_signal = _calculate_master_pattern_single_worker(
        master_simulator,
        half_size=recipe.half_size,
        hemisphere=recipe.hemisphere,
        scaling=recipe.master_scaling,
    )
    lambert_signal = master_signal.as_lambert(show_progressbar=False)
    rotation = _to_kikuchipy_rotation(recipe.orientation)
    detector = _to_kikuchipy_detector(recipe.detector)
    detector_signal = lambert_signal.get_patterns(
        rotation,
        detector,
        energy=recipe.energy_kev,
        dtype_out="float32",
        compute=True,
        show_progressbar=False,
    )
    detector_array = np.asarray(detector_signal.data, dtype=np.float32).squeeze()
    detector_geometry = master_simulator.on_detector(detector, rotation)

    catalog = {
        "master": _catalog_with_threshold(
            master_reflectors, recipe, recipe.master_relative_factor
        ),
        "overlays": {
            style.name: _catalog_with_threshold(
                overlay_reflectors[style.name], recipe, style.overlay_relative_factor
            )
            for style in recipe.styles
        },
    }
    simulation = KinematicalSimulation(
        master_stereographic=KinematicalArrayProduct.from_array(
            "master-stereographic",
            master_signal.data,
            metadata=_product_metadata(
                record,
                recipe,
                projection="stereographic",
                intensity_meaning="kinematical band intensity proportional to |F_hkl|^2",
            ),
        ),
        master_lambert=KinematicalArrayProduct.from_array(
            "master-lambert",
            lambert_signal.data,
            metadata=_product_metadata(
                record,
                recipe,
                projection="lambert-square-equal-area",
                intensity_meaning=(
                    "kinematical band intensity proportional to |F_hkl|^2, "
                    "resampled from stereographic coordinates"
                ),
            ),
        ),
        detector=KinematicalArrayProduct.from_array(
            "detector",
            detector_array,
            metadata=_product_metadata(
                record,
                recipe,
                projection="gnomonic",
                intensity_meaning=(
                    "float32 detector interpolation of kinematical Lambert intensity"
                ),
            ),
        ),
        reflector_catalog=catalog,
        projection_ledger=_projection_ledger(record, recipe),
    )
    context = _KikuchipyContext(
        master_simulator=master_simulator,
        overlay_simulators=overlay_simulators,
        master_signal=master_signal,
        lambert_signal=lambert_signal,
        detector_signal=detector_signal,
        detector_geometry=detector_geometry,
    )
    return simulation, context


def execute_kinematical(
    record: StructureRecord, recipe: KinematicalRecipe
) -> KinematicalExecution:
    """Simulate project-owned arrays and render their deterministic figures."""
    from .render import render_kinematical_figures

    simulation, context = simulate_kinematical_arrays(record, recipe)
    figures = render_kinematical_figures(context, simulation, recipe)
    return KinematicalExecution(simulation=simulation, figures=figures)

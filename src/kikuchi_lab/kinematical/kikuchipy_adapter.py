"""Private adapters for the public diffsims kinematical reflection APIs."""

from __future__ import annotations

from importlib.metadata import version

import numpy as np
from diffpy.structure import Atom, Lattice, Structure
from diffsims.crystallography import ReciprocalLatticeVector
from orix.crystal_map import Phase

from kikuchi_lab.sources.structure import StructureRecord, verify_structure

from .contracts import KinematicalRecipe


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

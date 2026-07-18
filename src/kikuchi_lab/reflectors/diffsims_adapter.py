"""Public diffsims adapter for phase-neutral reflector members."""

from __future__ import annotations

from collections import Counter

import numpy as np
from diffpy.structure import Atom, Lattice, Structure
from diffsims.crystallography import ReciprocalLatticeVector
from orix.crystal_map import Phase

from kikuchi_lab.sources.structure import StructureRecord, verify_structure

from .contracts import ReflectorMember
from .recipe import ReflectorRecipe


def _phase_from_record(source: StructureRecord) -> Phase:
    """Build a public orix phase in the tracked source crystal frame."""
    verify_structure(source)
    a, b, c, alpha, beta, gamma = source.lattice_angstrom
    lattice = Lattice(a, b, c, alpha, beta, gamma)
    atoms = [
        Atom(
            site.element,
            xyz=site.fract,
            label=site.label,
            occupancy=site.occupancy,
            Uisoequiv=site.u_iso_angstrom_sq,
        )
        for site in source.sites
    ]
    phase = Phase(
        name=source.name,
        space_group=source.space_group_number,
        structure=Structure(atoms=atoms, lattice=lattice, title=source.name),
    ).expand_asymmetric_unit()
    expected_multiplicities = source.simulation_setting.get(
        "reflector_target_site_multiplicities"
    )
    if expected_multiplicities is not None and expected_multiplicities != "unchecked":
        expected = Counter(
            {
                site.label: multiplicity
                for site, multiplicity in zip(
                    source.sites,
                    expected_multiplicities,
                    strict=True,
                )
            }
        )
        observed = Counter(atom.label for atom in phase.structure)
        if observed != expected:
            raise ValueError(
                f"phase expansion produced {dict(observed)!r}; expected {dict(expected)!r}"
            )
    return phase


def _allowed_mask(vectors: ReciprocalLatticeVector) -> np.ndarray:
    """Keep centering-allowed vectors, including primitive hexagonal Ice."""
    try:
        return vectors.allowed
    except NotImplementedError:
        centering = vectors.phase.space_group.short_name[0]
        if centering == "P" and vectors.has_hexagonal_lattice:
            return np.ones(vectors.shape, dtype=bool)
        raise


def _canonical_hkl(hkl: np.ndarray) -> tuple[tuple[int, int, int], int]:
    indices = np.rint(np.asarray(hkl, dtype=np.float64)).astype(np.int64)
    if not np.allclose(hkl, indices, rtol=0.0, atol=1e-8):
        raise ValueError("diffsims returned non-integer HKLs")
    nonzero = np.flatnonzero(indices)
    if not nonzero.size:
        raise ValueError("diffsims returned a zero reciprocal vector")
    sign = 1 if int(indices[int(nonzero[0])]) > 0 else -1
    return tuple(int(value) for value in sign * indices), sign


def enumerate_reflector_members(
    source: StructureRecord, recipe: ReflectorRecipe
) -> tuple[ReflectorMember, ...]:
    """Enumerate axial crystal-frame members using only public diffsims APIs."""
    phase = _phase_from_record(source)
    vectors = ReciprocalLatticeVector.from_min_dspacing(
        phase, min_dspacing=recipe.min_dspacing_angstrom
    )
    vectors = vectors[_allowed_mask(vectors)].unique(use_symmetry=True).symmetrise()
    vectors.sanitise_phase()
    vectors.calculate_structure_factor(scattering_params=recipe.scattering_params)
    vectors.calculate_theta(recipe.energy_kev * 1_000.0)
    strengths = np.abs(np.asarray(vectors.structure_factor, dtype=np.complex128))
    if strengths.ndim != 1 or not strengths.size or not np.isfinite(strengths).all():
        raise ValueError("structure-factor strengths must be finite and non-empty")
    maximum = float(strengths.max())
    if maximum <= 0.0:
        raise ValueError("structure-factor normalization requires a finite positive maximum")
    vectors = vectors[strengths >= recipe.selection_relative_factor * maximum]

    groups: dict[tuple[int, int, int], list[tuple[np.ndarray, float, float, float]]] = {}
    for hkl, normal, spacing, theta, factor in zip(
        vectors.hkl,
        vectors.unit.data,
        vectors.dspacing,
        vectors.theta,
        vectors.structure_factor,
        strict=True,
    ):
        key, sign = _canonical_hkl(hkl)
        groups.setdefault(key, []).append(
            (
                sign * np.asarray(normal, dtype=np.float64),
                float(spacing),
                float(theta),
                float(abs(factor)),
            )
        )

    collapsed: list[tuple[tuple[int, int, int], np.ndarray, float, float, float]] = []
    for hkl, entries in groups.items():
        normals = np.stack([entry[0] for entry in entries])
        spacings = np.asarray([entry[1] for entry in entries])
        widths = np.asarray([entry[2] for entry in entries])
        factors = np.asarray([entry[3] for entry in entries])
        if not np.allclose(normals, normals[0], rtol=0.0, atol=1e-9):
            raise ValueError(f"axial family {hkl} has inconsistent crystal normals")
        if not np.allclose(spacings, spacings[0], rtol=1e-9, atol=1e-11):
            raise ValueError(f"axial family {hkl} has inconsistent d-spacings")
        if not np.allclose(widths, widths[0], rtol=1e-9, atol=1e-11):
            raise ValueError(f"axial family {hkl} has inconsistent Bragg widths")
        normal = normals.mean(axis=0)
        normal /= np.linalg.norm(normal)
        collapsed.append(
            (hkl, normal, float(spacings.mean()), float(widths.mean()), float(factors.max()))
        )

    members = (
        ReflectorMember(
            hkl=hkl,
            normal_crystal=normal,
            dspacing_angstrom=spacing,
            bragg_half_width_rad=width,
            structure_factor_abs=factor,
            normalized_weight=min(1.0, (factor / maximum) ** recipe.weight_exponent),
        )
        for hkl, normal, spacing, width, factor in collapsed
    )
    return tuple(
        sorted(
            members,
            key=lambda member: (-member.normalized_weight, member.hkl, member.member_id),
        )
    )

"""Private adapters for the public diffsims kinematical reflection APIs."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import version
from types import MappingProxyType
from typing import Any, Protocol

import numpy as np
from diffpy.structure import Atom, Lattice, Structure
from diffsims.crystallography import ReciprocalLatticeVector
from diffsims.utils.sim_utils import _get_kinematical_structure_factor
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
from .reflector_evidence import (
    DirectReflectorEvidence,
    DirectReflectorRecipe,
    own_direct_reflector_evidence,
)


_SPHERICAL_CAMERA_DEG = {
    "elevation": 20.0,
    "azimuth": -35.0,
    "roll": 0.0,
}

_DIRECT_AXIS_INDEX = {"a": 0, "b": 1, "c": 2}
_FRACTIONAL_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


class _ReflectorEnumerationRecipe(Protocol):
    """Inputs shared by kinematical and direct reflector recipes."""

    min_dspacing_angstrom: float
    scattering_params: str


def _axis_permutation(
    values: object,
    *,
    indices: Mapping[str, int],
    field_name: str,
) -> tuple[int, int, int]:
    """Validate one explicit, unsigned crystallographic axis permutation."""
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError(f"{field_name} must contain exactly three axes")
    try:
        permutation = tuple(indices[str(value)] for value in values)
    except KeyError as exc:
        raise ValueError(f"unsupported axis in {field_name}: {exc.args[0]}") from exc
    if sorted(permutation) != [0, 1, 2]:
        raise ValueError(f"{field_name} must be an axis permutation")
    return permutation  # type: ignore[return-value]


def _fractional_origin_shift(value: object) -> tuple[float, float, float]:
    """Validate a target-frame origin-choice shift in fractional coordinates."""
    if value is None:
        return (0.0, 0.0, 0.0)
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(
            isinstance(component, bool)
            or not isinstance(component, (int, float))
            or not math.isfinite(float(component))
            for component in value
        )
    ):
        raise ValueError(
            "target_fractional_origin_shift must contain three finite numbers"
        )
    return tuple(float(component) for component in value)  # type: ignore[return-value]


def _permuted_lattice(
    record: StructureRecord, permutation: tuple[int, int, int]
) -> Lattice:
    a, b, c, alpha, beta, gamma = record.lattice_angstrom
    lengths = (a, b, c)
    source_angle = {
        frozenset((1, 2)): alpha,
        frozenset((0, 2)): beta,
        frozenset((0, 1)): gamma,
    }
    target_a, target_b, target_c = (lengths[index] for index in permutation)
    target_alpha = source_angle[frozenset((permutation[1], permutation[2]))]
    target_beta = source_angle[frozenset((permutation[0], permutation[2]))]
    target_gamma = source_angle[frozenset((permutation[0], permutation[1]))]
    return Lattice(
        target_a,
        target_b,
        target_c,
        target_alpha,
        target_beta,
        target_gamma,
    )


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
    lattice_permutation = _axis_permutation(
        record.simulation_setting["target_lattice_from_source"],
        indices=_DIRECT_AXIS_INDEX,
        field_name="target_lattice_from_source",
    )
    coordinate_permutation = _axis_permutation(
        record.simulation_setting["target_fractional_from_source"],
        indices=_FRACTIONAL_AXIS_INDEX,
        field_name="target_fractional_from_source",
    )
    if coordinate_permutation != lattice_permutation:
        raise ValueError(
            "fractional-coordinate permutation must match the direct-lattice "
            "permutation"
        )
    origin_shift = _fractional_origin_shift(
        record.simulation_setting.get("target_fractional_origin_shift")
    )
    lattice = _permuted_lattice(record, lattice_permutation)
    atoms = [
        Atom(
            site.element,
            xyz=tuple(
                (site.fract[source_index] + origin_shift[target_index]) % 1.0
                for target_index, source_index in enumerate(coordinate_permutation)
            ),
            label=site.label,
            occupancy=site.occupancy,
            Uisoequiv=site.u_iso_angstrom_sq,
        )
        for site in record.sites
    ]
    phase = Phase(
        name=record.name,
        space_group=record.space_group_number,
        structure=Structure(atoms=atoms, lattice=lattice, title=record.name),
    )
    raw_multiplicities = record.simulation_setting.get("target_site_multiplicities")
    if (
        not isinstance(raw_multiplicities, list)
        or len(raw_multiplicities) != len(record.sites)
        or any(type(value) is not int or value <= 0 for value in raw_multiplicities)
    ):
        raise ValueError(
            "simulation setting must define one positive integer target site "
            "multiplicity per source site"
        )
    expected = Counter(
        {
            site.label: multiplicity
            for site, multiplicity in zip(
                record.sites, raw_multiplicities, strict=True
            )
        }
    )
    expanded = phase.expand_asymmetric_unit()
    observed = Counter(atom.label for atom in expanded.structure)
    if observed != expected:
        raise ValueError(
            "alignment-aware phase expansion produced site multiplicities "
            f"{dict(observed)!r}; expected {dict(expected)!r}"
        )
    return expanded


def _allowed_mask(reflectors: ReciprocalLatticeVector) -> np.ndarray:
    """Return centering-allowed vectors, including primitive hexagonal cells.

    diffsims currently raises for primitive hexagonal lattices because its
    ``allowed`` shortcut does not encode their non-centering systematic
    absences. A primitive lattice has no centering extinctions, so all vectors
    can safely proceed here; the expanded unit-cell structure-factor
    calculation below removes screw/glide extinctions through vanishing F_hkl.
    """
    try:
        return reflectors.allowed
    except NotImplementedError:
        centering = reflectors.phase.space_group.short_name[0]
        if centering == "P" and reflectors.has_hexagonal_lattice:
            return np.ones(reflectors.shape, dtype=bool)
        raise


def _reciprocal_rotation_matrices(phase: Phase) -> tuple[np.ndarray, ...]:
    """Return exact unique reciprocal-index rotations from space-group operators."""
    matrices: list[np.ndarray] = []
    for operation in phase.space_group.symop_list:
        direct_float = np.asarray(operation.R, dtype=np.float64)
        direct = np.rint(direct_float).astype(np.int64)
        if not np.allclose(direct_float, direct, rtol=0.0, atol=1e-12):
            raise ValueError("space-group direct rotations must be integer-valued")
        reciprocal_float = np.linalg.inv(direct).T
        reciprocal = np.rint(reciprocal_float).astype(np.int64)
        if not np.allclose(reciprocal_float, reciprocal, rtol=0.0, atol=1e-12):
            raise ValueError("space-group reciprocal rotations must be integer-valued")
        if not any(np.array_equal(reciprocal, existing) for existing in matrices):
            matrices.append(reciprocal)
    if not matrices:
        raise ValueError("space group must provide at least one reciprocal rotation")
    return tuple(matrices)


def _canonical_axial_hkl(indices: np.ndarray) -> tuple[int, int, int]:
    nonzero = np.flatnonzero(indices)
    if not nonzero.size:
        raise ValueError("direct reflector HKLs must be nonzero")
    sign = 1 if int(indices[int(nonzero[0])]) > 0 else -1
    return tuple(int(value) for value in sign * indices)


def _symmetrise_exact_integer_hkls(
    reflectors: ReciprocalLatticeVector,
) -> ReciprocalLatticeVector:
    """Expand exact reciprocal-index orbits without Cartesian point-group drift."""
    hkl_float = np.asarray(reflectors.hkl, dtype=np.float64)
    hkl = np.rint(hkl_float).astype(np.int64)
    if not np.allclose(hkl_float, hkl, rtol=0.0, atol=1e-8):
        raise ValueError("enumerated reflector HKLs must be integer-valued")
    rotations = _reciprocal_rotation_matrices(reflectors.phase)
    orbit = np.concatenate([hkl @ rotation.T for rotation in rotations], axis=0)
    unique = np.unique(orbit, axis=0)
    return ReciprocalLatticeVector(reflectors.phase, hkl=unique)


def _enumerate_reflectors(
    phase: Phase, recipe: _ReflectorEnumerationRecipe
) -> ReciprocalLatticeVector:
    reflectors = ReciprocalLatticeVector.from_min_dspacing(
        phase, min_dspacing=recipe.min_dspacing_angstrom
    )
    reflectors = reflectors[_allowed_mask(reflectors)]
    upstream_symmetrised = reflectors.unique(use_symmetry=True).symmetrise()
    upstream_hkl = np.asarray(upstream_symmetrised.hkl, dtype=np.float64)
    if np.allclose(upstream_hkl, np.rint(upstream_hkl), rtol=0.0, atol=1e-8):
        # Preserve the reviewed upstream representation when it remains a valid
        # reciprocal-index orbit. Some non-orthogonal settings (notably
        # monoclinic 2/m) rotate about orix's Cartesian convention and yield
        # non-integer pseudo-HKLs; those must use the exact fractional-space path.
        reflectors = upstream_symmetrised
    else:
        reflectors = _symmetrise_exact_integer_hkls(reflectors)
    return _calculate_axial_structure_factors(
        reflectors, recipe.scattering_params
    )


def _select_reflectors(
    reflectors: ReciprocalLatticeVector,
    relative_factor: float,
    energy_kev: float,
) -> ReciprocalLatticeVector:
    amplitudes = np.abs(reflectors.structure_factor)
    selected = reflectors[amplitudes >= relative_factor * float(amplitudes.max())]
    selected.calculate_theta(energy_kev * 1_000.0)
    return selected


def _calculate_axial_structure_factors(
    reflectors: ReciprocalLatticeVector, scattering_params: str
) -> ReciprocalLatticeVector:
    """Calculate pair-safe factors with exact point-symmetry magnitude ties."""
    hkl_float = np.asarray(reflectors.hkl, dtype=np.float64)
    hkl = np.rint(hkl_float).astype(np.int64)
    if not np.allclose(hkl_float, hkl, rtol=0.0, atol=1e-8):
        raise ValueError("direct reflector HKLs must be integer-valued")

    keys: list[tuple[int, int, int]] = []
    signs: list[int] = []
    for indices in hkl:
        nonzero = np.flatnonzero(indices)
        if not nonzero.size:
            raise ValueError("direct reflector HKLs must be nonzero")
        sign = 1 if int(indices[int(nonzero[0])]) > 0 else -1
        keys.append(tuple(int(value) for value in sign * indices))
        signs.append(sign)

    canonical = np.asarray(sorted(set(keys)), dtype=np.int64)
    factors = _get_kinematical_structure_factor(
        structure=reflectors.phase.structure,
        g_indices=canonical,
        g_hkls_array=reflectors.phase.structure.lattice.rnorm(canonical),
        scattering_params=scattering_params,
    )
    factor_by_key = dict(zip(map(tuple, canonical), factors, strict=True))
    rotations = _reciprocal_rotation_matrices(reflectors.phase)
    factor_keys = set(factor_by_key)
    representative_by_key: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for key in factor_by_key:
        indices = np.asarray(key, dtype=np.int64)
        family_keys = {
            _canonical_axial_hkl(rotation @ indices) for rotation in rotations
        }
        missing = family_keys - factor_keys
        if missing:
            raise ValueError(
                "direct reflector symmetry orbit is incomplete after exact "
                f"integer symmetrisation: {sorted(missing)!r}"
            )
        representative_by_key[key] = min(family_keys)
    # Kikuchi intensity uses |F|. Reuse one actually calculated family
    # representative so symmetry-equivalent magnitudes remain exact ties;
    # the opposite axial direction receives its exact conjugate below.
    symmetry_tied_factor = {
        key: factor_by_key[representative_by_key[key]] for key in factor_by_key
    }
    paired = np.asarray(
        [
            symmetry_tied_factor[key]
            if sign == 1
            else np.conjugate(symmetry_tied_factor[key])
            for key, sign in zip(keys, signs, strict=True)
        ],
        dtype=np.complex128,
    )
    reflectors._structure_factor = paired
    return reflectors


def build_direct_reflector_evidence(
    record: StructureRecord,
    recipe: DirectReflectorRecipe,
) -> DirectReflectorEvidence:
    """Calculate owned reflector evidence without constructing a master simulator."""
    verify_structure(record)
    phase = _phase_from_record(record)
    enumerated = _enumerate_reflectors(phase, recipe)
    selected = _select_reflectors(
        enumerated,
        recipe.candidate_relative_factor,
        recipe.energy_kev,
    )
    return own_direct_reflector_evidence(
        selected,
        source_structure_id=record.identifier,
        source_structure_sha256=record.sha256,
        calculation_id=recipe.calculation_id,
        weighting_id=recipe.weighting_id,
        weight_exponent=recipe.weight_exponent,
        eligibility_min_weight=recipe.eligibility_min_weight,
        counts={"enumerated": enumerated.size, "selected_signed": selected.size},
    )


def _reflection_catalog(
    reflectors: ReciprocalLatticeVector,
    recipe: KinematicalRecipe,
    threshold: float,
) -> dict[str, object]:
    enumerated = ReciprocalLatticeVector.from_min_dspacing(
        reflectors.phase, min_dspacing=recipe.min_dspacing_angstrom
    )
    allowed = enumerated[_allowed_mask(enumerated)]
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
    lattice = _phase_from_record(record).structure.lattice
    lattice_abc = np.asarray(lattice.cell_parms()[:3], dtype=float)
    crystal_direction = np.asarray(
        lattice.cartesian(recipe.zone_axis_uvw), dtype=float
    )
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
        "metric_conversion": (
            "diffpy.structure.Lattice.cartesian([u, v, w]) then normalize"
        ),
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
    lattice_axes = record.simulation_setting["target_lattice_from_source"]
    fractional_axes = record.simulation_setting["target_fractional_from_source"]
    target_setting = record.simulation_setting["target_setting"]
    crystal_frame = (
        "standard-Pnma direct and reciprocal Cartesian frames"
        if target_setting == "P n m a"
        else f"{target_setting} direct and reciprocal Cartesian frames"
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
            "crystal": crystal_frame,
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
                "target_setting": target_setting,
                "lattice_transform": {
                    "target_from_source": lattice_axes,
                    "equation": (
                        "(a', b', c') = (" + ", ".join(lattice_axes) + ")"
                    ),
                },
                "fractional_coordinate_transform": {
                    "target_from_source": fractional_axes,
                    "equation": (
                        "(x', y', z') = (" + ", ".join(fractional_axes) + ")"
                    ),
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

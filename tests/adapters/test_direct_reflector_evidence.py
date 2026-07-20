from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import kikuchi_lab.kinematical.kikuchipy_adapter as adapter
from kikuchi_lab.kinematical import DirectReflectorRecipe, load_direct_reflector_recipe
from kikuchi_lab.sources.structure import (
    SiteRecord,
    StructureRecord,
    load_structure_record,
)


ROOT = Path(__file__).parents[2]


def _synthetic_quartz_record() -> StructureRecord:
    return replace(
        load_structure_record(ROOT / "phases/ice-ih/source.yml"),
        identifier="synthetic-quartz",
        name="alpha-quartz",
        formula="SiO2",
        space_group_number=152,
        setting="P 31 2 1",
        lattice_angstrom=(4.914, 4.914, 5.406, 90.0, 90.0, 120.0),
        sites=(
            SiteRecord("Si1", "Si", (0.4699, 0.0, 0.33333), 1.0, 0.00646),
            SiteRecord("O1", "O", (0.413, 0.2668, 0.214), 1.0, 0.01089),
        ),
        simulation_setting={
            "source_setting": "P 31 2 1",
            "target_setting": "P 31 2 1",
            "target_lattice_from_source": ["a", "b", "c"],
            "target_fractional_from_source": ["x", "y", "z"],
            "target_site_multiplicities": [3, 6],
        },
    )


def _synthetic_quartz_recipe() -> DirectReflectorRecipe:
    return DirectReflectorRecipe(
        schema_version=1,
        name="synthetic-quartz-art-bands",
        source_record="../../phases/quartz/source.yml",
        energy_kev=20.0,
        min_dspacing_angstrom=0.7,
        scattering_params="xtables",
        candidate_relative_factor=0.03,
        weight_exponent=2.0,
        eligibility_min_weight=0.08,
    )


@pytest.mark.parametrize(
    ("phase_slug", "expected_label_counts"),
    [
        ("ice-ih", {"O1": 4}),
        (
            "forsterite",
            {"Mg1": 4, "Mg2": 4, "Si": 4, "O1": 4, "O2": 4, "O3": 8},
        ),
    ],
)
def test_phase_adapter_expands_each_verified_site_to_its_target_multiplicity(
    phase_slug: str, expected_label_counts: dict[str, int]
) -> None:
    record = load_structure_record(ROOT / f"phases/{phase_slug}/source.yml")

    phase = adapter._phase_from_record(record)

    assert Counter(atom.label for atom in phase.structure) == expected_label_counts


def test_phase_adapter_expands_quartz_to_si3o6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _synthetic_quartz_record()
    monkeypatch.setattr(adapter, "verify_structure", lambda _record: None)

    phase = adapter._phase_from_record(record)

    assert Counter(atom.label for atom in phase.structure) == {"Si1": 3, "O1": 6}
    assert Counter(atom.element for atom in phase.structure) == {"Si": 3, "O": 6}


def test_phase_adapter_rejects_expansion_that_disagrees_with_site_multiplicity() -> None:
    record = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    tampered = replace(
        record,
        simulation_setting={
            **record.simulation_setting,
            "target_site_multiplicities": [2],
        },
    )

    with pytest.raises(ValueError, match="site multiplicities"):
        adapter._phase_from_record(tampered)


def test_reflector_enumeration_preserves_the_alignment_aware_expanded_cell() -> None:
    record = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / "recipes/reflectors/ice-ih-art-bands.yml"
    )
    phase = adapter._phase_from_record(record)

    reflectors = adapter._enumerate_reflectors(phase, recipe)

    assert Counter(atom.label for atom in reflectors.phase.structure) == {"O1": 4}


def _first_nonzero_positive(indices: np.ndarray) -> tuple[tuple[int, int, int], int]:
    nonzero = np.flatnonzero(indices)
    assert nonzero.size
    sign = 1 if int(indices[int(nonzero[0])]) > 0 else -1
    return tuple(int(value) for value in sign * indices), sign


def _assert_exact_friedel_factors(reflectors: object) -> None:
    hkl = np.rint(np.asarray(getattr(reflectors, "hkl"))).astype(np.int64)
    factors = np.asarray(getattr(reflectors, "structure_factor"))
    grouped: dict[tuple[int, int, int], dict[int, list[complex]]] = {}
    for indices, factor in zip(hkl, factors, strict=True):
        key, sign = _first_nonzero_positive(indices)
        grouped.setdefault(key, {}).setdefault(sign, []).append(complex(factor))
    for key, signed in grouped.items():
        assert set(signed) == {-1, 1}, f"missing Friedel partner for {key}"
        positive = np.asarray(signed[1], dtype=np.complex128)
        negative = np.asarray(signed[-1], dtype=np.complex128)
        np.testing.assert_array_equal(
            positive, np.full(positive.shape, positive[0], dtype=np.complex128)
        )
        np.testing.assert_array_equal(
            negative,
            np.full(negative.shape, np.conjugate(positive[0]), dtype=np.complex128),
        )


def test_reflector_enumeration_is_pair_safe_before_any_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _synthetic_quartz_record()
    recipe = _synthetic_quartz_recipe()
    monkeypatch.setattr(adapter, "verify_structure", lambda _record: None)

    reflectors = adapter._enumerate_reflectors(
        adapter._phase_from_record(record), recipe
    )

    _assert_exact_friedel_factors(reflectors)


def test_reflector_enumeration_preserves_exact_symmetry_magnitude_ties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _synthetic_quartz_record()
    monkeypatch.setattr(adapter, "verify_structure", lambda _record: None)
    reflectors = adapter._enumerate_reflectors(
        adapter._phase_from_record(record), _synthetic_quartz_recipe()
    )
    magnitudes = np.abs(reflectors.structure_factor)

    for family_indices in reflectors.get_hkl_sets().values():
        family = magnitudes[family_indices]
        np.testing.assert_array_equal(
            family, np.full(family.shape, family.flat[0], dtype=np.float64)
        )


def test_quartz_direct_factors_are_exact_friedel_conjugates_before_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _synthetic_quartz_record()
    recipe = _synthetic_quartz_recipe()
    real_select = adapter._select_reflectors
    observed_preselection = False

    def inspect_then_select(reflectors, relative_factor, energy_kev):
        nonlocal observed_preselection
        _assert_exact_friedel_factors(reflectors)
        observed_preselection = True
        selected = real_select(reflectors, relative_factor, energy_kev)
        _assert_exact_friedel_factors(selected)
        return selected

    monkeypatch.setattr(adapter, "verify_structure", lambda _record: None)
    monkeypatch.setattr(adapter, "_select_reflectors", inspect_then_select)

    evidence = adapter.build_direct_reflector_evidence(record, recipe)

    assert observed_preselection
    assert evidence.hkl.shape[0] > 0


def test_direct_evidence_never_constructs_a_master(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter,
        "KikuchiPatternSimulator",
        lambda *_args, **_kwargs: pytest.fail("master simulator constructed"),
    )
    record = load_structure_record(ROOT / "phases/ice-ih/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / "recipes/reflectors/ice-ih-art-bands.yml"
    )

    evidence = adapter.build_direct_reflector_evidence(record, recipe)

    assert evidence.ledger["simulation_count"] == 0
    assert evidence.hkl.shape[0] >= 11


def test_direct_evidence_preserves_reflector_physics() -> None:
    record = load_structure_record(ROOT / "phases/forsterite/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / "recipes/reflectors/forsterite-art-bands.yml"
    )

    evidence = adapter.build_direct_reflector_evidence(record, recipe)

    assert np.all(evidence.dspacing_angstrom > 0)
    assert np.all(evidence.bragg_half_width_rad > 0)
    assert np.max(evidence.normalized_weight) == pytest.approx(1.0)
    np.testing.assert_allclose(
        np.linalg.norm(evidence.normal_crystal, axis=1), 1.0, atol=1e-12
    )


def _independent_axial_channels(
    reflectors: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    hkl = np.rint(np.asarray(getattr(reflectors, "hkl"))).astype(np.int64)
    normals = np.asarray(getattr(getattr(reflectors, "unit"), "data"), dtype=np.float64)
    dspacing = np.asarray(getattr(reflectors, "dspacing"), dtype=np.float64)
    theta = np.asarray(getattr(reflectors, "theta"), dtype=np.float64)
    strength = np.abs(np.asarray(getattr(reflectors, "structure_factor")))
    grouped: dict[tuple[int, int, int], list[tuple[np.ndarray, float, float, float]]] = {}
    for indices, normal, spacing, angle, magnitude in zip(
        hkl, normals, dspacing, theta, strength, strict=True
    ):
        nonzero = np.flatnonzero(indices)
        assert nonzero.size
        sign = 1 if int(indices[int(nonzero[0])]) > 0 else -1
        key = tuple(int(value) for value in sign * indices)
        grouped.setdefault(key, []).append(
            (sign * normal, float(spacing), float(angle), float(magnitude))
        )

    output_hkl: list[tuple[int, int, int]] = []
    output_normals: list[np.ndarray] = []
    output_dspacing: list[float] = []
    output_theta: list[float] = []
    output_strength: list[float] = []
    for key in sorted(grouped):
        group = grouped[key]
        normal = np.mean([item[0] for item in group], axis=0)
        normal /= np.linalg.norm(normal)
        output_hkl.append(key)
        output_normals.append(normal)
        output_dspacing.append(float(np.mean([item[1] for item in group])))
        output_theta.append(float(np.mean([item[2] for item in group])))
        output_strength.append(float(np.mean([item[3] for item in group])))
    return (
        np.asarray(output_hkl, dtype=np.int32),
        np.asarray(output_normals, dtype=np.float64),
        np.asarray(output_dspacing, dtype=np.float64),
        np.asarray(output_theta, dtype=np.float64),
        np.asarray(output_strength, dtype=np.float64),
    )


@pytest.mark.parametrize("phase_slug", ["ice-ih", "forsterite"])
def test_direct_evidence_matches_pair_safe_pre_master_path(phase_slug: str) -> None:
    record = load_structure_record(ROOT / f"phases/{phase_slug}/source.yml")
    recipe = load_direct_reflector_recipe(
        ROOT / f"recipes/reflectors/{phase_slug}-art-bands.yml"
    )
    enumerated = adapter._enumerate_reflectors(adapter._phase_from_record(record), recipe)
    selected = adapter._select_reflectors(
        enumerated,
        recipe.candidate_relative_factor,
        recipe.energy_kev,
    )
    expected = _independent_axial_channels(selected)

    evidence = adapter.build_direct_reflector_evidence(record, recipe)

    np.testing.assert_array_equal(evidence.hkl, expected[0])
    for actual, reference in zip(
        (
            evidence.normal_crystal,
            evidence.dspacing_angstrom,
            evidence.bragg_half_width_rad,
            evidence.structure_factor_magnitude,
        ),
        expected[1:],
        strict=True,
    ):
        np.testing.assert_allclose(actual, reference, rtol=1e-12, atol=1e-12)

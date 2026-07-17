from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import kikuchi_lab.kinematical.kikuchipy_adapter as adapter
from kikuchi_lab.kinematical import load_direct_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]


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
def test_direct_evidence_matches_current_pre_master_path(phase_slug: str) -> None:
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

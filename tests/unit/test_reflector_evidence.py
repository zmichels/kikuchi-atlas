from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from kikuchi_lab.kinematical.reflector_evidence import (
    DirectReflectorEvidence,
    DirectReflectorRecipe,
    load_direct_reflector_recipe,
    own_direct_reflector_evidence,
)


ICE_RECIPE = Path("recipes/reflectors/ice-ih-art-bands.yml")
FORSTERITE_RECIPE = Path("recipes/reflectors/forsterite-art-bands.yml")


def _recipe_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "ice-ih-direct-art-reflectors",
        "source_record": "../../phases/ice-ih/source.yml",
        "energy_kev": 20.0,
        "reflections": {
            "min_dspacing_angstrom": 0.7,
            "scattering_params": "xtables",
            "candidate_relative_factor": 0.03,
        },
        "art_weight": {
            "exponent": 2.0,
            "eligibility_min_weight": 0.08,
        },
    }


def _write_recipe(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "direct-reflectors.yml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _evidence_kwargs() -> dict[str, object]:
    return {
        "source_structure_id": "COD-test",
        "source_structure_sha256": "a" * 64,
        "calculation_id": "reflector-calculation-test",
        "weighting_id": "reflector-weighting-test",
        "hkl": np.array([[1, 0, 0]], dtype=np.int32),
        "normal_crystal": np.array([[1.0, 0.0, 0.0]]),
        "dspacing_angstrom": np.array([2.0]),
        "bragg_half_width_rad": np.array([0.01]),
        "structure_factor_magnitude": np.array([10.0]),
        "normalized_weight": np.array([1.0]),
        "ledger": {"simulation_count": 0},
    }


def _reflectors() -> SimpleNamespace:
    return SimpleNamespace(
        hkl=np.array(
            [
                [0, -1, 0],
                [-2, 0, 0],
                [0, 1, 0],
                [2, 0, 0],
            ],
            dtype=np.int32,
        ),
        unit=SimpleNamespace(
            data=np.array(
                [
                    [0.0, -1.0, 0.0],
                    [-1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [1.0, 0.0, 0.0],
                ]
            )
        ),
        dspacing=np.array([3.0, 2.0, 3.0, 2.0]),
        theta=np.array([0.02, 0.01, 0.02, 0.01]),
        structure_factor=np.array([5.0 + 0.0j, 10.0 + 0.0j, 5.0 + 0.0j, 10.0 + 0.0j]),
    )


def test_tracked_direct_recipe_has_exact_first_series_policy() -> None:
    recipe = load_direct_reflector_recipe(ICE_RECIPE)
    assert recipe.energy_kev == 20.0
    assert recipe.min_dspacing_angstrom == 0.7
    assert recipe.scattering_params == "xtables"
    assert recipe.candidate_relative_factor == 0.03
    assert recipe.weight_exponent == 2.0
    assert recipe.eligibility_min_weight == 0.08
    assert recipe.calculation_id.startswith("reflector-calculation-")
    assert recipe.weighting_id.startswith("reflector-weighting-")


def test_recipe_identities_are_path_and_phase_neutral() -> None:
    ice = load_direct_reflector_recipe(ICE_RECIPE)
    forsterite = load_direct_reflector_recipe(FORSTERITE_RECIPE)

    assert isinstance(ice, DirectReflectorRecipe)
    assert ice.calculation_id == forsterite.calculation_id
    assert ice.weighting_id == forsterite.weighting_id


def test_owned_evidence_rejects_inconsistent_or_writeable_channels() -> None:
    evidence = DirectReflectorEvidence(**_evidence_kwargs())
    assert not evidence.normal_crystal.flags.writeable
    assert evidence.evidence_id.startswith("reflector-evidence-")


def test_evidence_owns_little_endian_arrays_and_deeply_frozen_ledger() -> None:
    kwargs = _evidence_kwargs()
    source_hkl = kwargs["hkl"]
    source_normal = kwargs["normal_crystal"]
    source_ledger = {"simulation_count": 0, "counts": {"selected_signed": 2}}
    kwargs["ledger"] = source_ledger

    evidence = DirectReflectorEvidence(**kwargs)
    source_hkl[:] = 9
    source_normal[:] = 0.0
    source_ledger["counts"]["selected_signed"] = 99

    assert evidence.hkl.dtype.str == "<i4"
    for channel in (
        evidence.normal_crystal,
        evidence.dspacing_angstrom,
        evidence.bragg_half_width_rad,
        evidence.structure_factor_magnitude,
        evidence.normalized_weight,
    ):
        assert channel.dtype.str == "<f8"
        assert not channel.flags.writeable
    np.testing.assert_array_equal(evidence.hkl, [[1, 0, 0]])
    np.testing.assert_array_equal(evidence.normal_crystal, [[1.0, 0.0, 0.0]])
    assert evidence.ledger["counts"]["selected_signed"] == 2
    with pytest.raises(TypeError):
        evidence.ledger["counts"]["selected_signed"] = 3  # type: ignore[index]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), True),
        (("energy_kev",), True),
        (("energy_kev",), float("nan")),
        (("energy_kev",), 19.9),
        (("reflections", "min_dspacing_angstrom"), 0.8),
        (("reflections", "scattering_params"), "lobato"),
        (("reflections", "candidate_relative_factor"), 0.04),
        (("art_weight", "exponent"), 1.0),
        (("art_weight", "eligibility_min_weight"), 0.1),
    ],
)
def test_recipe_rejects_noncanonical_first_series_values(
    tmp_path: Path, path: tuple[str, ...], value: object
) -> None:
    payload = deepcopy(_recipe_payload())
    target = payload
    for field in path[:-1]:
        child = target[field]
        assert isinstance(child, dict)
        target = child
    target[path[-1]] = value

    with pytest.raises(ValueError):
        load_direct_reflector_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize("section", [(), ("reflections",), ("art_weight",)])
@pytest.mark.parametrize("mutation", ["missing", "additional"])
def test_recipe_requires_exact_keys(
    tmp_path: Path, section: tuple[str, ...], mutation: str
) -> None:
    payload = deepcopy(_recipe_payload())
    target = payload
    for field in section:
        child = target[field]
        assert isinstance(child, dict)
        target = child
    if mutation == "missing":
        del target[next(iter(target))]
    else:
        target["unsupported"] = "value"

    with pytest.raises(ValueError, match="fields differ"):
        load_direct_reflector_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize(
    "source_record",
    [
        "/tmp/source.yml",
        r"C:\\phases\\ice-ih\\source.yml",
        r"\\\\server\\share\\source.yml",
        "../../../outside/source.yml",
        "../../phases/../outside/source.yml",
    ],
)
def test_recipe_rejects_source_path_escapes(
    tmp_path: Path, source_record: str
) -> None:
    payload = _recipe_payload()
    payload["source_record"] = source_record

    with pytest.raises(ValueError, match="source_record"):
        load_direct_reflector_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("hkl", np.array([[0, 0, 0]]), "nonzero"),
        ("hkl", np.array([[-1, 0, 0]]), "canonical"),
        ("normal_crystal", np.array([[2.0, 0.0, 0.0]]), "unit"),
        ("dspacing_angstrom", np.array([0.0]), "positive"),
        ("bragg_half_width_rad", np.array([0.0]), "positive"),
        ("structure_factor_magnitude", np.array([0.0]), "positive"),
        ("normalized_weight", np.array([1.1]), r"\[0, 1\]"),
    ],
)
def test_evidence_rejects_invalid_channel_values(
    field: str, value: np.ndarray, message: str
) -> None:
    kwargs = _evidence_kwargs()
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        DirectReflectorEvidence(**kwargs)


def test_evidence_rejects_inconsistent_shapes_and_duplicate_hkls() -> None:
    kwargs = _evidence_kwargs()
    kwargs["normal_crystal"] = np.ones((2, 3))
    with pytest.raises(ValueError, match="shape"):
        DirectReflectorEvidence(**kwargs)

    kwargs = _evidence_kwargs()
    kwargs["hkl"] = np.array([[1, 0, 0], [1, 0, 0]])
    kwargs["normal_crystal"] = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    for field in (
        "dspacing_angstrom",
        "bragg_half_width_rad",
        "structure_factor_magnitude",
        "normalized_weight",
    ):
        kwargs[field] = np.repeat(kwargs[field], 2)
    with pytest.raises(ValueError, match="unique"):
        DirectReflectorEvidence(**kwargs)


@pytest.mark.parametrize("checksum", ["not-a-sha256", None])
def test_evidence_rejects_invalid_structure_checksum(checksum: object) -> None:
    kwargs = _evidence_kwargs()
    kwargs["source_structure_sha256"] = checksum

    with pytest.raises(ValueError, match="64"):
        DirectReflectorEvidence(**kwargs)


def test_own_evidence_collapses_signed_pairs_sorts_and_weights() -> None:
    evidence = own_direct_reflector_evidence(
        _reflectors(),
        source_structure_id="COD-test",
        source_structure_sha256="a" * 64,
        calculation_id="reflector-calculation-test",
        weighting_id="reflector-weighting-test",
        weight_exponent=2.0,
        eligibility_min_weight=0.08,
        counts={"enumerated": 8, "selected_signed": 4},
    )

    np.testing.assert_array_equal(evidence.hkl, [[0, 1, 0], [2, 0, 0]])
    np.testing.assert_allclose(evidence.normalized_weight, [0.25, 1.0])
    assert evidence.ledger["simulation_count"] == 0
    assert evidence.ledger["orientation_dependency"] == "none"
    assert evidence.ledger["counts"]["axial"] == 2


def test_own_evidence_rejects_inconsistent_signed_pairs() -> None:
    reflectors = _reflectors()
    reflectors.theta[-1] = 0.02

    with pytest.raises(ValueError, match="inconsistent antipodal angles"):
        own_direct_reflector_evidence(
            reflectors,
            source_structure_id="COD-test",
            source_structure_sha256="a" * 64,
            calculation_id="reflector-calculation-test",
            weighting_id="reflector-weighting-test",
            weight_exponent=2.0,
            eligibility_min_weight=0.08,
            counts={"enumerated": 8, "selected_signed": 4},
        )

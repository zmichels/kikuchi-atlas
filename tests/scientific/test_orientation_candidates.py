from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.model import Orientation, canonical_json
from kikuchi_lab.orientations.candidates import (
    SUPPORTED_ORIENTATION_CONVENTION,
    crystal_disorientation_deg,
    load_candidate_set,
    pairwise_crystal_disorientation_deg,
    zone_axis_sample_misalignment_deg,
)


RECIPE = Path("recipes/proof/forsterite-candidates.yml")
EXPECTED_IDS = (
    "fo-001-phi1-000",
    "fo-001-phi1-035",
    "fo-100-phi1-180",
    "fo-100-phi1-220",
    "fo-010-phi1-015",
    "fo-010-phi1-055",
    "fo-110-phi1-100",
    "fo-101-phi1-205",
    "fo-011-phi1-045",
    "fo-111-phi1-090",
    "fo-210-phi1-120",
    "fo-012-phi1-060",
)


def test_forsterite_candidates_have_stable_order_and_project_contracts() -> None:
    candidate_set = load_candidate_set(RECIPE)

    assert candidate_set.candidate_ids == EXPECTED_IDS
    assert len(candidate_set.candidates) == 12
    assert all(type(candidate.orientation) is Orientation for candidate in candidate_set.candidates)
    assert all(candidate.orientation.frame == "crystal_to_sample" for candidate in candidate_set.candidates)
    expected_convention = (
        "active crystal-to-sample Bunge ZXZ Euler angles in degrees; "
        "sample axes are EDAX-TSL [RD, TD, ND]"
    )
    assert SUPPORTED_ORIENTATION_CONVENTION == expected_convention
    assert candidate_set.orientation_convention == expected_convention
    assert candidate_set.phi1_semantics == (
        "bunge_phi1_deg is the explicit first Bunge Euler angle; it is a reproducible "
        "in-plane composition choice, not an absolute roll measured from a zone-axis "
        "alignment reference"
    )


def test_candidate_angles_are_finite_and_in_canonical_bunge_ranges() -> None:
    candidate_set = load_candidate_set(RECIPE)

    for candidate in candidate_set.candidates:
        phi1, phi, phi2 = candidate.orientation.euler_bunge_deg
        assert candidate.bunge_phi1_deg == phi1
        assert all(math.isfinite(angle) for angle in (phi1, phi, phi2))
        assert 0.0 <= phi1 < 360.0
        assert 0.0 <= phi <= 180.0
        assert 0.0 <= phi2 < 360.0


def test_loader_rejects_noncanonical_bunge_angles(tmp_path: Path) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    recipe["candidates"][0]["euler_bunge_deg"] = [360.0, 0.0, 0.0]
    invalid = tmp_path / "noncanonical.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical Bunge ranges"):
        load_candidate_set(invalid)


@pytest.mark.parametrize(
    "contradictory_convention",
    [
        "passive crystal-to-sample Bunge ZXZ Euler angles in degrees",
        "active crystal-to-sample Bunge ZXZ Euler angles in radians",
    ],
)
def test_loader_rejects_any_other_orientation_convention(
    tmp_path: Path, contradictory_convention: str
) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    recipe["orientation_convention"] = contradictory_convention
    invalid = tmp_path / "contradictory-convention.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match="orientation_convention"):
        load_candidate_set(invalid)


def test_loader_rejects_phi1_metadata_that_disagrees_with_euler_triple(tmp_path: Path) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    recipe["candidates"][0]["bunge_phi1_deg"] = 91.0
    invalid = tmp_path / "contradictory-phi1.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match="bunge_phi1_deg"):
        load_candidate_set(invalid)


def test_every_candidate_documents_zone_axis_and_compositional_intent() -> None:
    candidate_set = load_candidate_set(RECIPE)

    for candidate in candidate_set.candidates:
        assert len(candidate.zone_axis_uvw) == 3
        assert any(index != 0 for index in candidate.zone_axis_uvw)
        assert candidate.zone_axis_label.startswith("[")
        assert "sample ND" in candidate.zone_axis_intent
        assert len(candidate.composition_intent) >= 30

    by_id = {candidate.candidate_id: candidate for candidate in candidate_set.candidates}
    assert "shortest c-axis" in by_id["fo-001-phi1-000"].composition_intent
    assert "longest a-axis" in by_id["fo-100-phi1-180"].composition_intent
    assert "intermediate b-axis" in by_id["fo-010-phi1-015"].composition_intent


def test_documented_zone_axes_are_centered_on_sample_normal() -> None:
    candidate_set = load_candidate_set(RECIPE)

    # These are the repository's verified standard-Pnma simulation axes, not
    # the differently ordered lattice lengths of the source Pbnm CIF.
    assert candidate_set.lattice_abc_angstrom == pytest.approx((10.207, 5.980, 4.756))
    for candidate in candidate_set.candidates:
        assert zone_axis_sample_misalignment_deg(
            candidate,
            lattice_abc_angstrom=candidate_set.lattice_abc_angstrom,
        ) < 1e-6


def test_forsterite_candidates_are_distinct_under_fixed_sample_crystal_mmm() -> None:
    candidate_set = load_candidate_set(RECIPE)
    distances = pairwise_crystal_disorientation_deg(candidate_set)

    assert candidate_set.point_group == "mmm"
    assert candidate_set.equivalence_tolerance_deg == pytest.approx(0.01)
    assert len(distances) == 66
    assert (distances[0].candidate_a_id, distances[0].candidate_b_id) == (
        "fo-001-phi1-000",
        "fo-001-phi1-035",
    )
    assert (distances[-1].candidate_a_id, distances[-1].candidate_b_id) == (
        "fo-210-phi1-120",
        "fo-012-phi1-060",
    )
    assert min(distance.distance_deg for distance in distances) > 0.01


def test_disorientation_reduces_crystal_mmm_but_keeps_sample_frame_fixed() -> None:
    identity = Orientation((0.0, 0.0, 0.0))
    crystal_twofold_equivalent = Orientation((0.0, 180.0, 0.0))
    one_degree_sample_rotation = Orientation((1.0, 0.0, 0.0))

    assert crystal_disorientation_deg(identity, crystal_twofold_equivalent) == pytest.approx(
        0.0, abs=1e-7
    )
    assert crystal_disorientation_deg(identity, one_degree_sample_rotation) == pytest.approx(
        1.0, abs=1e-7
    )


def test_candidate_set_identity_and_serialization_are_stable() -> None:
    first = load_candidate_set(RECIPE)
    second = load_candidate_set(RECIPE)

    assert first.candidate_set_id == second.candidate_set_id
    assert first.candidate_set_id == "candidate-set-770010a96a2dbf3e"
    assert canonical_json(first.to_dict()) == canonical_json(second.to_dict())
    assert [candidate.orientation.orientation_id for candidate in first.candidates] == [
        candidate.orientation.orientation_id for candidate in second.candidates
    ]


def test_candidate_set_owns_candidate_tuple_and_resists_source_list_mutation() -> None:
    baseline = load_candidate_set(RECIPE)
    mutable_candidates = list(baseline.candidates)
    owned = replace(baseline, candidates=mutable_candidates)
    accepted_id = owned.candidate_set_id

    mutable_candidates.pop()

    assert type(owned.candidates) is tuple
    assert len(owned.candidates) == 12
    assert owned.candidate_set_id == accepted_id


def test_candidate_set_rejects_non_candidate_entries() -> None:
    baseline = load_candidate_set(RECIPE)

    with pytest.raises(ValueError, match="candidates must contain OrientationCandidate"):
        replace(baseline, candidates=[*baseline.candidates[:-1], object()])


def test_zone_axis_display_formatting_does_not_change_scientific_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kikuchi_lab.orientations import candidates as candidate_module

    baseline = load_candidate_set(RECIPE)
    accepted_id = baseline.candidate_set_id
    original_label = baseline.candidates[0].zone_axis_label

    monkeypatch.setattr(candidate_module, "_zone_axis_label", lambda uvw: f"[{', '.join(map(str, uvw))}]")

    assert baseline.candidates[0].zone_axis_label != original_label
    assert baseline.candidate_set_id == accepted_id
    assert "zone_axis_label" not in baseline.identity_payload()["candidates"][0]
    assert baseline.to_dict()["candidates"][0]["zone_axis_label"] == "[0, 0, 1]"


@pytest.mark.parametrize("invalid_exhaustive", [True, "false", 0, None])
def test_v1_bounded_proof_set_requires_literal_false(
    tmp_path: Path, invalid_exhaustive: object
) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    recipe["exhaustive"] = invalid_exhaustive
    invalid = tmp_path / "invalid-exhaustive.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match="exhaustive must be false"):
        load_candidate_set(invalid)


@pytest.mark.parametrize("invalid_schema", [True, 1.0, "1", None, 2])
def test_schema_version_requires_exact_integer_one(tmp_path: Path, invalid_schema: object) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    recipe["schema_version"] = invalid_schema
    invalid = tmp_path / "invalid-schema.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version must be integer 1"):
        load_candidate_set(invalid)


@pytest.mark.parametrize("invalid_number", [True, "0.0", None, float("inf")])
@pytest.mark.parametrize(
    ("field", "mutate", "message"),
    [
        (
            "euler",
            lambda recipe, value: recipe["candidates"][0].__setitem__(
                "euler_bunge_deg", [value, 0.0, 0.0]
            ),
            "euler_bunge_deg",
        ),
        (
            "phi1",
            lambda recipe, value: recipe["candidates"][0].__setitem__(
                "bunge_phi1_deg", value
            ),
            "bunge_phi1_deg",
        ),
        (
            "lattice",
            lambda recipe, value: recipe.__setitem__(
                "lattice_abc_angstrom", [value, 5.980, 4.756]
            ),
            "lattice_abc_angstrom",
        ),
        (
            "tolerance",
            lambda recipe, value: recipe.__setitem__("equivalence_tolerance_deg", value),
            "equivalence_tolerance_deg",
        ),
    ],
)
def test_scientific_real_fields_reject_coercible_or_nonfinite_values(
    tmp_path: Path,
    field: str,
    mutate: object,
    message: str,
    invalid_number: object,
) -> None:
    del field
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    mutate(recipe, invalid_number)
    invalid = tmp_path / "invalid-real.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_candidate_set(invalid)


@pytest.mark.parametrize("invalid_index", [True, "1", None, 1.5, float("inf")])
def test_zone_axis_uvw_requires_finite_integer_indices(
    tmp_path: Path, invalid_index: object
) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    recipe["candidates"][0]["zone_axis_uvw"] = [invalid_index, 0, 1]
    invalid = tmp_path / "invalid-uvw.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match="zone_axis_uvw"):
        load_candidate_set(invalid)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda recipe: recipe.__setitem__("candidates", [None]), "candidate entry must be a mapping"),
        (lambda recipe: recipe.__setitem__("candidates", [17]), "candidate entry must be a mapping"),
        (lambda recipe: recipe.__setitem__("lattice_abc_angstrom", None), "lattice_abc_angstrom"),
        (lambda recipe: recipe.__setitem__("lattice_abc_angstrom", 10.207), "lattice_abc_angstrom"),
        (lambda recipe: recipe.__setitem__("lattice_abc_angstrom", [1.0, 2.0]), "lattice_abc_angstrom"),
        (lambda recipe: recipe.__setitem__("equivalence_tolerance_deg", None), "equivalence_tolerance_deg"),
    ],
)
def test_malformed_nested_yaml_reports_field_specific_value_error(
    tmp_path: Path, mutation: object, message: str
) -> None:
    recipe = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    mutation(recipe)
    invalid = tmp_path / "malformed-nested.yml"
    invalid.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_candidate_set(invalid)

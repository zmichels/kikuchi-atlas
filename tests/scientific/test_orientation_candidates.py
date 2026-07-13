from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.model import Orientation, canonical_json
from kikuchi_lab.orientations.candidates import (
    crystal_disorientation_deg,
    load_candidate_set,
    pairwise_crystal_disorientation_deg,
    zone_axis_sample_misalignment_deg,
)


RECIPE = Path("recipes/proof/forsterite-candidates.yml")
EXPECTED_IDS = (
    "fo-001-r000",
    "fo-001-r035",
    "fo-100-r000",
    "fo-100-r040",
    "fo-010-r015",
    "fo-010-r055",
    "fo-110-r010",
    "fo-101-r025",
    "fo-011-r045",
    "fo-111-r000",
    "fo-210-r030",
    "fo-012-r060",
)


def test_forsterite_candidates_have_stable_order_and_project_contracts() -> None:
    candidate_set = load_candidate_set(RECIPE)

    assert candidate_set.candidate_ids == EXPECTED_IDS
    assert len(candidate_set.candidates) == 12
    assert all(type(candidate.orientation) is Orientation for candidate in candidate_set.candidates)
    assert all(candidate.orientation.frame == "crystal_to_sample" for candidate in candidate_set.candidates)
    assert candidate_set.orientation_convention == (
        "active crystal-to-sample Bunge ZXZ Euler angles in degrees; "
        "sample axes are EDAX-TSL [RD, TD, ND]"
    )


def test_candidate_angles_are_finite_and_in_canonical_bunge_ranges() -> None:
    candidate_set = load_candidate_set(RECIPE)

    for candidate in candidate_set.candidates:
        phi1, phi, phi2 = candidate.orientation.euler_bunge_deg
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


def test_every_candidate_documents_zone_axis_and_compositional_intent() -> None:
    candidate_set = load_candidate_set(RECIPE)

    for candidate in candidate_set.candidates:
        assert len(candidate.zone_axis_hkl) == 3
        assert any(index != 0 for index in candidate.zone_axis_hkl)
        assert candidate.zone_axis_label.startswith("[")
        assert "sample ND" in candidate.zone_axis_intent
        assert len(candidate.composition_intent) >= 30


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
        "fo-001-r000",
        "fo-001-r035",
    )
    assert (distances[-1].candidate_a_id, distances[-1].candidate_b_id) == (
        "fo-210-r030",
        "fo-012-r060",
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
    assert first.candidate_set_id.startswith("candidate-set-")
    assert canonical_json(first.to_dict()) == canonical_json(second.to_dict())
    assert [candidate.orientation.orientation_id for candidate in first.candidates] == [
        candidate.orientation.orientation_id for candidate in second.candidates
    ]

from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest

from kikuchi_lab.dictionary.ice_ih import (
    build_candidate_matrix,
    compose_quaternions_wxyz,
    ice_ih_s2_directions,
    ice_ih_so3_orientations,
    local_refine_candidate,
    publish_ice_ih_candidate_dictionary,
    quaternion_from_rotation_vectors_degrees,
    quaternion_misorientation_degrees,
    rank_candidate_matrix,
    run_synthetic_recovery,
    sample_stereographic_master,
    verify_ice_ih_candidate_dictionary,
)


def _anisotropic_master(size: int = 9) -> np.ndarray:
    coordinates = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinates, coordinates, indexing="xy")
    upper = 10.0 + 2.0 * x + 3.0 * y + 1.5 * x * y + 0.75 * y * y
    lower = 20.0 - 4.0 * x + 5.0 * y - 1.25 * x * y + 0.5 * x * x
    return np.stack((upper, lower)).astype(np.float32)


def test_ice_ih_grids_are_deterministic_unit_and_symmetry_reduced() -> None:
    orientations = ice_ih_so3_orientations(5.0)
    directions = ice_ih_s2_directions(5.0)

    assert orientations.shape == (13_155, 4)
    assert directions.shape == (1_946, 3)
    assert np.allclose(np.linalg.norm(orientations, axis=1), 1.0, rtol=0.0, atol=5e-13)
    assert np.all(orientations[:, 0] >= 0.0)
    assert np.allclose(np.linalg.norm(directions, axis=1), 1.0, rtol=0.0, atol=5e-13)


def test_stereographic_sampler_uses_upper_at_equator_and_correct_poles() -> None:
    master = _anisotropic_master()
    values = sample_stereographic_master(
        master,
        np.asarray(((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0))),
    )

    assert values[0] == pytest.approx(10.0)
    assert values[1] == pytest.approx(20.0)
    assert values[2] == pytest.approx(12.0)


def test_candidate_cache_ranks_the_explicit_active_crystal_to_sample_rotation() -> None:
    master = _anisotropic_master()
    directions = ice_ih_s2_directions(20.0)
    root_half = math.sqrt(0.5)
    quaternions = np.asarray(
        (
            (1.0, 0.0, 0.0, 0.0),
            (root_half, 0.0, 0.0, root_half),
        ),
        dtype=np.float64,
    )

    cache = build_candidate_matrix(master, quaternions, directions, batch_size=1)
    matches = rank_candidate_matrix(cache, cache[1], top_k=2)

    assert matches[0].entry_index == 1
    assert matches[0].score == pytest.approx(1.0, abs=1e-6)
    assert matches[1].entry_index == 0


def test_candidate_cache_rejects_flat_uninformative_rows() -> None:
    master = np.ones((2, 5, 5), dtype=np.float32)
    directions = np.asarray(((0.0, 0.0, 1.0), (1.0, 0.0, 0.0)), dtype=np.float64)
    quaternions = np.asarray(((1.0, 0.0, 0.0, 0.0),), dtype=np.float64)

    with pytest.raises(ValueError, match="zero-variance"):
        build_candidate_matrix(master, quaternions, directions)


def test_published_candidate_dictionary_is_portable_and_ranks_its_fixture(tmp_path) -> None:
    result = publish_ice_ih_candidate_dictionary(
        output_root=tmp_path / "ice-ih-candidate-cache",
        master=_anisotropic_master(),
        master_array_sha256=hashlib.sha256(_anisotropic_master().tobytes()).hexdigest(),
        source={
            "phase_source_id": "ice-ih-test-source",
            "phase_source_sha256": "b" * 64,
            "phase_source_uri": "https://example.invalid/ice-ih.cif",
            "structural_citation": "Synthetic Ice Ih unit-test provenance.",
            "kinematical_recipe_id": "recipe-test",
            "master_product_id": "master-test",
            "energy_kev": 20.0,
        },
        recipe={"recipe_id": "ice-ih-test-dictionary", "sampling": "unit-test"},
        dictionary_version="0.1.0-test",
        created_at="2026-07-20T00:00:00Z",
        authors=("Kikuchi Lab unit test",),
        orientation_resolution_degrees=30.0,
        direction_resolution_degrees=30.0,
        synthetic_recovery={
            "held_out_rotation_vector_degrees": (0.0, 0.0, 1.0),
            "local_half_width_degrees": 2.0,
            "local_step_degrees": 0.5,
        },
    )

    assert result.path.is_dir()
    manifest = json.loads((result.path / "dictionary.manifest.json").read_text(encoding="utf-8"))
    assert manifest["representation_kind"] == "spherical"
    assert manifest["phase"]["phase_name"] == "Ice Ih average oxygen sublattice"
    assert manifest["candidate_cache"]["score_metric"] == "normalized-cosine"
    assert manifest["refinement"]["source"] == "canonical-master-stereographic"
    assert manifest["citation"]["cff_path"] == "CITATION.cff"
    assert manifest["phase"]["lattice_parameters"]["a"] == pytest.approx(4.3815)
    assert (
        manifest["orientation_convention"]["coverage_validation"]["unique_entry_count"]
        == (manifest["entries"]["count"])
    )
    assert manifest["representation"]["sphere_axis_labels"] == [
        "sample_x",
        "sample_y",
        "sample_z",
    ]
    assert manifest["representation"]["canonical_master_frame"] == "crystal"
    assert manifest["representation"]["sphere_frame"] == "sample"
    assert manifest["candidate_cache"]["direction_frame"] == "sample"
    assert manifest["matching_compatibility"]["detector_pattern_input"] == (
        "not accepted directly; explicit adapter required"
    )
    assert (result.path / "master/ice-ih-master-stereographic.npy").is_file()
    assert (result.path / "cache/candidate-matrix.npy").is_file()
    assert (result.path / "entries.csv").is_file()
    roles = {record["path"]: record["role"] for record in manifest["files"]}
    assert roles["entries.csv"] == "entries"
    assert roles["master/ice-ih-master-stereographic.npy"] == "spherical_signal"
    assert roles["validation/expected-recovery.json"] == "validation"
    assert manifest["validation"]["kind"] == "held-out synthetic coarse-to-refined recovery"
    expected = json.loads(
        (result.path / "validation/expected-recovery.json").read_text(encoding="utf-8")
    )
    assert (
        expected["recovery"]["refined_error_degrees"] < expected["recovery"]["coarse_error_degrees"]
    )

    verification = verify_ice_ih_candidate_dictionary(result.path)
    assert verification.dictionary_id == result.dictionary_id
    assert verification.entry_count == manifest["entries"]["count"]
    assert verification.expected_top_entry_index == expected["recovery"]["coarse_entry_index"]


def test_local_refinement_improves_an_off_grid_synthetic_orientation() -> None:
    master = _anisotropic_master()
    directions = ice_ih_s2_directions(20.0)
    center = np.asarray(((1.0, 0.0, 0.0, 0.0),), dtype=np.float64)
    held_out = compose_quaternions_wxyz(
        center,
        quaternion_from_rotation_vectors_degrees(np.asarray(((0.0, 0.0, 2.5),))),
    )[0]
    observed = build_candidate_matrix(master, held_out[None, :], directions)[0]

    refined = local_refine_candidate(
        master,
        center[0],
        directions,
        observed,
        half_width_degrees=4.0,
        step_degrees=1.0,
    )

    coarse_error = quaternion_misorientation_degrees(center[0], held_out)
    refined_error = quaternion_misorientation_degrees(refined.quaternion_wxyz, held_out)
    assert refined_error < coarse_error
    assert refined_error <= 0.6
    assert refined.score > 0.999


def test_synthetic_recovery_reports_improved_coarse_to_refined_diagnostic() -> None:
    master = _anisotropic_master()
    directions = ice_ih_s2_directions(20.0)
    quaternions = np.asarray(((1.0, 0.0, 0.0, 0.0),), dtype=np.float64)
    cache = build_candidate_matrix(master, quaternions, directions)

    recovery = run_synthetic_recovery(
        master,
        quaternions,
        directions,
        cache,
        held_out_rotation_vector_degrees=(0.0, 0.0, 2.5),
        local_half_width_degrees=4.0,
        local_step_degrees=1.0,
    )

    assert recovery.reference_entry_index == 0
    assert recovery.coarse_entry_index == 0
    assert recovery.refined_error_degrees < recovery.coarse_error_degrees
    assert recovery.refined_error_degrees <= 0.6

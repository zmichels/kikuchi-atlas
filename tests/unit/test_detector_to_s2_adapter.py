from __future__ import annotations

import numpy as np
import pytest

from kikuchi_lab.dictionary.detector_to_s2 import (
    local_refine_masked_candidate,
    rank_masked_candidate_matrix,
    reproject_stereographic_master_to_detector,
    sample_detector_to_s2,
)
from kikuchi_lab.dictionary.ice_ih import (
    compose_quaternions_wxyz,
    quaternion_from_rotation_vectors_degrees,
    quaternion_misorientation_degrees,
    quaternion_rotation_matrices,
)
from kikuchi_lab.dictionary.signal_space_bridge import sample_frame_rays_from_gnomonic
from kikuchi_lab.model.recipes import DetectorRecipe
from kikuchi_lab.projection.kikuchipy_adapter import _to_kikuchipy_detector


def _detector_recipe() -> DetectorRecipe:
    return DetectorRecipe(
        shape=(5, 7),
        pcx=0.5,
        pcy=0.5,
        pcz=0.8,
        pc_convention="tsl",
        sample_tilt_deg=0.0,
        detector_tilt_deg=0.0,
        detector_azimuth_deg=0.0,
        detector_twist_deg=0.0,
        pixel_size_um=5.0,
        binning=1,
        supersampling=1,
    )


def test_detector_to_s2_round_trips_declared_pixel_rays_and_masks_backside() -> None:
    recipe = _detector_recipe()
    detector = _to_kikuchipy_detector(recipe)
    pixels = np.asarray(((0.0, 0.0), (0.0, 6.0), (2.0, 3.0), (4.0, 0.0), (4.0, 6.0)))
    gnomonic = np.asarray(detector.to_gnomonic_coords(pixels), dtype=np.float64)[0]
    matrix = np.asarray(detector.sample_to_detector.to_matrix(), dtype=np.float64)[0]
    directions = sample_frame_rays_from_gnomonic(gnomonic, matrix)
    backside = np.asarray((0.0, 0.0, -1.0)) @ matrix
    directions = np.vstack((directions, backside))
    image = np.fromfunction(lambda row, column: 10.0 * row + column, recipe.shape)

    sampled = sample_detector_to_s2(image, directions, recipe)

    assert sampled.covered.tolist() == [True, True, True, True, True, False]
    np.testing.assert_allclose(sampled.pixel_coordinates_yx[:5], pixels, atol=1e-12)
    np.testing.assert_allclose(sampled.values[:5], image[pixels[:, 0].astype(int), pixels[:, 1].astype(int)])
    assert np.isnan(sampled.values[-1])


def test_masked_candidate_ranking_uses_only_declared_coverage() -> None:
    cache = np.asarray(
        (
            (0.0, 1.0, 2.0, 3.0, 100.0),
            (3.0, 2.0, 1.0, 0.0, -100.0),
            (0.0, 0.0, 0.0, 0.0, 0.0),
        ),
        dtype=np.float32,
    )
    observed = np.asarray((10.0, 11.0, 12.0, 13.0, np.nan))
    covered = np.asarray((True, True, True, True, False))

    matches = rank_masked_candidate_matrix(cache, observed, covered, top_k=2)

    assert matches[0].entry_index == 0
    assert matches[0].score == pytest.approx(1.0)
    assert matches[1].entry_index == 1


def test_master_reprojection_returns_raw_detector_shape_and_honors_rotation() -> None:
    recipe = _detector_recipe()
    coordinate = np.linspace(-1.0, 1.0, 9)
    xx, yy = np.meshgrid(coordinate, coordinate, indexing="xy")
    master = np.stack((1.0 + xx + 2.0 * yy, 1.0 - xx + 2.0 * yy)).astype(np.float32)

    identity = reproject_stereographic_master_to_detector(master, recipe, batch_rows=2)
    rotated = reproject_stereographic_master_to_detector(
        master,
        recipe,
        crystal_to_sample_matrix=np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))),
        batch_rows=3,
    )

    assert identity.shape == recipe.shape
    assert np.all(np.isfinite(identity))
    assert np.all(np.isfinite(rotated))
    assert not np.allclose(identity, rotated)


def test_master_reprojection_rejects_invalid_batch_or_rotation() -> None:
    recipe = _detector_recipe()
    master = np.ones((2, 9, 9), dtype=np.float32)

    with pytest.raises(ValueError, match="batch_rows"):
        reproject_stereographic_master_to_detector(master, recipe, batch_rows=0)
    with pytest.raises(ValueError, match="crystal_to_sample_matrix"):
        reproject_stereographic_master_to_detector(
            master,
            recipe,
            crystal_to_sample_matrix=np.eye(2),
        )


def test_masked_local_refinement_improves_a_held_out_detector_orientation() -> None:
    recipe = _detector_recipe()
    detector = _to_kikuchipy_detector(recipe)
    pixels = np.asarray(
        tuple((float(row), float(column)) for row in range(5) for column in range(7))
    )
    gnomonic = np.asarray(detector.to_gnomonic_coords(pixels), dtype=np.float64)[0]
    sample_to_detector = np.asarray(detector.sample_to_detector.to_matrix(), dtype=np.float64)[0]
    directions = sample_frame_rays_from_gnomonic(gnomonic, sample_to_detector)
    coordinate = np.linspace(-1.0, 1.0, 21)
    xx, yy = np.meshgrid(coordinate, coordinate, indexing="xy")
    master = np.stack(
        (
            1.0 + xx + 2.0 * yy + 0.7 * xx * yy,
            1.0 - 1.5 * xx + 0.4 * yy - 0.5 * xx * yy,
        )
    ).astype(np.float32)
    center = np.asarray(((1.0, 0.0, 0.0, 0.0),), dtype=np.float64)
    held_out = compose_quaternions_wxyz(
        center,
        quaternion_from_rotation_vectors_degrees(np.asarray(((0.0, 0.0, 2.5),))),
    )[0]
    detector_image = reproject_stereographic_master_to_detector(
        master,
        recipe,
        crystal_to_sample_matrix=quaternion_rotation_matrices(held_out[None, :])[0],
        batch_rows=2,
    )
    sampled = sample_detector_to_s2(detector_image, directions, recipe)

    refined = local_refine_masked_candidate(
        master,
        center[0],
        directions,
        sampled.values,
        sampled.covered,
        half_width_degrees=4.0,
        step_degrees=1.0,
    )

    coarse_error = quaternion_misorientation_degrees(center[0], held_out)
    refined_error = quaternion_misorientation_degrees(refined.quaternion_wxyz, held_out)
    assert int(np.sum(sampled.covered)) >= 30
    assert refined_error < coarse_error
    assert refined_error < 1.2
    assert refined.score > 0.999


def test_masked_local_refinement_rejects_invalid_search_or_center() -> None:
    master = np.ones((2, 5, 5), dtype=np.float32)
    directions = np.asarray(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)))
    observed = np.asarray((1.0, 2.0))
    covered = np.asarray((True, True))

    with pytest.raises(ValueError, match="half_width_degrees"):
        local_refine_masked_candidate(
            master,
            (1.0, 0.0, 0.0, 0.0),
            directions,
            observed,
            covered,
            half_width_degrees=0.0,
            step_degrees=1.0,
        )
    with pytest.raises(ValueError, match="center_quaternion_wxyz"):
        local_refine_masked_candidate(
            master,
            (0.0, 0.0, 0.0, 0.0),
            directions,
            observed,
            covered,
            half_width_degrees=1.0,
            step_degrees=1.0,
        )

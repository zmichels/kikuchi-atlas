from __future__ import annotations

import numpy as np
import pytest

from kikuchi_lab.dictionary.detector_to_s2 import (
    rank_masked_candidate_matrix,
    reproject_stereographic_master_to_detector,
    sample_detector_to_s2,
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

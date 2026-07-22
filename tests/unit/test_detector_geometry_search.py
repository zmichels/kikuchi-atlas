from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from kikuchi_lab.dictionary.detector_to_s2 import reproject_stereographic_master_to_detector
from kikuchi_lab.dictionary.geometry_search import rank_detector_geometry_candidates
from kikuchi_lab.dictionary.ice_ih import build_candidate_matrix
from kikuchi_lab.dictionary.signal_space_bridge import sample_frame_rays_from_gnomonic
from kikuchi_lab.model.recipes import DetectorRecipe
from kikuchi_lab.projection.kikuchipy_adapter import _to_kikuchipy_detector


def _detector() -> DetectorRecipe:
    return DetectorRecipe(
        shape=(9, 11),
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


def _directions(detector_recipe: DetectorRecipe) -> np.ndarray:
    detector = _to_kikuchipy_detector(detector_recipe)
    pixels = np.asarray(
        tuple((float(row), float(column)) for row in range(1, 8) for column in range(1, 10))
    )
    gnomonic = np.asarray(detector.to_gnomonic_coords(pixels), dtype=np.float64)[0]
    matrix = np.asarray(detector.sample_to_detector.to_matrix(), dtype=np.float64)[0]
    return sample_frame_rays_from_gnomonic(gnomonic, matrix)


def _master() -> np.ndarray:
    coordinate = np.linspace(-1.0, 1.0, 31)
    xx, yy = np.meshgrid(coordinate, coordinate, indexing="xy")
    return np.stack(
        (
            1.0 + xx + 1.5 * yy + 0.9 * xx * yy,
            1.0 - 1.2 * xx + 0.7 * yy - 0.5 * xx * yy,
        )
    ).astype(np.float32)


def test_geometry_search_uses_common_coverage_and_recovers_true_candidate() -> None:
    detector = _detector()
    directions = _directions(detector)
    master = _master()
    quaternions = np.asarray(((1.0, 0.0, 0.0, 0.0),), dtype=np.float64)
    cache = build_candidate_matrix(master, quaternions, directions)
    image = reproject_stereographic_master_to_detector(master, detector, batch_rows=3)
    shifted = replace(detector, pcx=0.9)

    result = rank_detector_geometry_candidates(
        image,
        directions,
        cache,
        (shifted, detector),
        top_k=1,
    )

    assert result.best.candidate_index == 1
    assert result.best.matches[0].entry_index == 0
    assert result.best.score > 0.999
    assert int(np.sum(result.common_coverage)) < len(directions)
    assert result.candidates[0].score > result.candidates[1].score


def test_geometry_search_rejects_incompatible_candidate_shapes() -> None:
    detector = _detector()
    directions = _directions(detector)
    with pytest.raises(ValueError, match="same supersampled shape"):
        rank_detector_geometry_candidates(
            np.ones(detector.shape),
            directions,
            np.ones((1, len(directions))),
            (detector, replace(detector, shape=(10, 11))),
            top_k=1,
        )


def test_geometry_search_breaks_equal_scores_by_candidate_index() -> None:
    detector = _detector()
    directions = _directions(detector)
    master = _master()
    cache = build_candidate_matrix(
        master,
        np.asarray(((1.0, 0.0, 0.0, 0.0),), dtype=np.float64),
        directions,
    )
    image = reproject_stereographic_master_to_detector(master, detector, batch_rows=3)

    result = rank_detector_geometry_candidates(
        image,
        directions,
        cache,
        (detector, detector),
        top_k=1,
    )

    assert [candidate.candidate_index for candidate in result.candidates] == [0, 1]
    assert result.candidates[0].score == result.candidates[1].score

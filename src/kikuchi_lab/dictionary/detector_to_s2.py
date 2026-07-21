"""Explicit detector-plane to partial-S2 sampling for dictionary experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kikuchi_lab.dictionary.ice_ih import CandidateMatch
from kikuchi_lab.model.recipes import DetectorRecipe
from kikuchi_lab.projection.kikuchipy_adapter import _to_kikuchipy_detector


_UNIT_TOLERANCE = 5.0e-13


@dataclass(frozen=True)
class DetectorToS2Sample:
    """Raw detector values sampled at declared sample-frame S2 directions."""

    values: np.ndarray
    covered: np.ndarray
    pixel_coordinates_yx: np.ndarray


def _unit_directions(value: object) -> np.ndarray:
    directions = np.asarray(value, dtype=np.float64)
    if directions.ndim != 2 or directions.shape[1] != 3 or len(directions) == 0:
        raise ValueError("directions must be a non-empty (N, 3) array")
    if not np.all(np.isfinite(directions)):
        raise ValueError("directions must contain finite values")
    if not np.allclose(
        np.linalg.norm(directions, axis=1), 1.0, rtol=0.0, atol=_UNIT_TOLERANCE
    ):
        raise ValueError("directions must be unit vectors")
    return np.ascontiguousarray(directions)


def _sample_to_detector_matrix(detector: DetectorRecipe) -> np.ndarray:
    model = _to_kikuchipy_detector(detector)
    matrices = np.asarray(model.sample_to_detector.to_matrix(), dtype=np.float64).reshape(-1, 3, 3)
    if len(matrices) != 1:
        raise ValueError("one detector recipe must resolve to one geometry matrix")
    matrix = matrices[0]
    identity = np.eye(3, dtype=np.float64)
    if not np.allclose(matrix @ matrix.T, identity, rtol=0.0, atol=_UNIT_TOLERANCE):
        raise ValueError("sample-to-detector matrix must be orthonormal")
    if not np.isclose(np.linalg.det(matrix), 1.0, rtol=0.0, atol=_UNIT_TOLERANCE):
        raise ValueError("sample-to-detector matrix must be right-handed")
    return matrix


def _pixel_coordinates_from_s2(
    directions: np.ndarray,
    detector: DetectorRecipe,
) -> tuple[np.ndarray, np.ndarray]:
    model = _to_kikuchipy_detector(detector)
    matrix = _sample_to_detector_matrix(detector)
    detector_rays = directions @ matrix.T
    forward = detector_rays[:, 2] > np.finfo(np.float64).eps
    gnomonic = np.full((len(directions), 2), np.nan, dtype=np.float64)
    gnomonic[forward, 0] = detector_rays[forward, 1] / detector_rays[forward, 2]
    gnomonic[forward, 1] = detector_rays[forward, 0] / detector_rays[forward, 2]
    pixels = np.full((len(directions), 2), np.nan, dtype=np.float64)
    if np.any(forward):
        converted = np.asarray(model.to_pixel_coords(gnomonic[forward]), dtype=np.float64)
        if converted.ndim == 3 and converted.shape[0] == 1:
            converted = converted[0]
        if converted.shape != (int(np.sum(forward)), 2):
            raise ValueError("kikuchipy returned unexpected pixel-coordinate shape")
        pixels[forward] = converted
    rows, columns = detector.supersampled_shape
    covered = (
        forward
        & (pixels[:, 0] >= 0.0)
        & (pixels[:, 0] <= rows - 1.0)
        & (pixels[:, 1] >= 0.0)
        & (pixels[:, 1] <= columns - 1.0)
    )
    return pixels, covered


def _bilinear_sample(image: np.ndarray, coordinates_yx: np.ndarray) -> np.ndarray:
    rows, columns = image.shape
    y, x = coordinates_yx.T
    y0 = np.floor(y).astype(np.intp)
    x0 = np.floor(x).astype(np.intp)
    y1 = np.minimum(y0 + 1, rows - 1)
    x1 = np.minimum(x0 + 1, columns - 1)
    dy = y - y0
    dx = x - x0
    return (
        (1.0 - dy) * (1.0 - dx) * image[y0, x0]
        + dy * (1.0 - dx) * image[y1, x0]
        + (1.0 - dy) * dx * image[y0, x1]
        + dy * dx * image[y1, x1]
    )


def sample_detector_to_s2(
    detector_intensity: object,
    directions: object,
    detector: DetectorRecipe,
) -> DetectorToS2Sample:
    """Sample raw detector values onto covered directions of an exact S2 grid.

    Directions outside the declared gnomonic camera view are represented by a
    false coverage mask and ``NaN`` values. No fill, tone mapping, background
    correction, or detector preprocessing is applied.
    """
    image = np.asarray(detector_intensity, dtype=np.float64)
    if image.shape != detector.supersampled_shape or not np.all(np.isfinite(image)):
        raise ValueError("detector_intensity must be finite and match the declared detector shape")
    samples = _unit_directions(directions)
    pixels, covered = _pixel_coordinates_from_s2(samples, detector)
    values = np.full(len(samples), np.nan, dtype=np.float64)
    if np.any(covered):
        values[covered] = _bilinear_sample(image, pixels[covered])
    return DetectorToS2Sample(
        values=np.ascontiguousarray(values),
        covered=np.ascontiguousarray(covered),
        pixel_coordinates_yx=np.ascontiguousarray(pixels),
    )


def rank_masked_candidate_matrix(
    candidate_matrix: object,
    observed_signal: object,
    covered: object,
    *,
    top_k: int = 8,
) -> tuple[CandidateMatch, ...]:
    """Rank only covered S2 directions using per-mask centered cosine scores.

    This is deliberately separate from the current full-S2 package matcher:
    each candidate is re-centered and normalized on the detector's explicit
    coverage mask, so scores must not be compared across different masks.
    """
    cache = np.asarray(candidate_matrix, dtype=np.float64)
    if cache.ndim != 2 or cache.shape[0] == 0 or cache.shape[1] == 0:
        raise ValueError("candidate_matrix must be a non-empty two-dimensional array")
    if not np.all(np.isfinite(cache)):
        raise ValueError("candidate_matrix must contain finite values")
    mask = np.asarray(covered, dtype=bool)
    if mask.shape != (cache.shape[1],) or int(np.sum(mask)) < 2:
        raise ValueError("covered must retain at least two directions matching cache width")
    observed = np.asarray(observed_signal, dtype=np.float64)
    if observed.shape != (cache.shape[1],) or not np.all(np.isfinite(observed[mask])):
        raise ValueError("observed_signal must be finite on covered directions and match cache width")
    if type(top_k) is not int or not 1 <= top_k <= cache.shape[0]:
        raise ValueError("top_k must be a positive integer no greater than candidate count")
    observed_masked = observed[mask]
    observed_centered = observed_masked - float(np.mean(observed_masked))
    observed_norm = float(np.linalg.norm(observed_centered))
    if observed_norm <= np.finfo(np.float64).eps:
        raise ValueError("observed_signal must vary on covered directions")
    normalized_observed = observed_centered / observed_norm
    candidates = cache[:, mask]
    candidates -= np.mean(candidates, axis=1, keepdims=True)
    candidate_norms = np.linalg.norm(candidates, axis=1)
    valid = candidate_norms > np.finfo(np.float64).eps
    scores = np.full(len(cache), -np.inf, dtype=np.float64)
    scores[valid] = candidates[valid] @ normalized_observed / candidate_norms[valid]
    ordered = np.lexsort((np.arange(len(scores)), -scores))[:top_k]
    return tuple(CandidateMatch(int(index), float(scores[index])) for index in ordered)

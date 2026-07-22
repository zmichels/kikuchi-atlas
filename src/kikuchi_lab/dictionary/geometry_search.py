"""Comparable detector-geometry candidate ranking on a shared partial-S2 mask."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from kikuchi_lab.dictionary.detector_to_s2 import rank_masked_candidate_matrix, sample_detector_to_s2
from kikuchi_lab.dictionary.ice_ih import CandidateMatch
from kikuchi_lab.model.recipes import DetectorRecipe


@dataclass(frozen=True)
class DetectorGeometryCandidateResult:
    """One detector-geometry candidate and its best masked dictionary match."""

    candidate_index: int
    detector: DetectorRecipe
    covered_direction_count: int
    matches: tuple[CandidateMatch, ...]

    @property
    def score(self) -> float:
        return self.matches[0].score


@dataclass(frozen=True)
class DetectorGeometrySearchResult:
    """Ranked geometry candidates evaluated on one common S2 coverage mask."""

    common_coverage: np.ndarray
    candidates: tuple[DetectorGeometryCandidateResult, ...]

    @property
    def best(self) -> DetectorGeometryCandidateResult:
        return self.candidates[0]


def _candidate_detectors(value: Sequence[DetectorRecipe]) -> tuple[DetectorRecipe, ...]:
    detectors = tuple(value)
    if not detectors or any(not isinstance(detector, DetectorRecipe) for detector in detectors):
        raise ValueError("detectors must be a non-empty sequence of DetectorRecipe values")
    shape = detectors[0].supersampled_shape
    if any(detector.supersampled_shape != shape for detector in detectors):
        raise ValueError("all detector candidates must have the same supersampled shape")
    return detectors


def rank_detector_geometry_candidates(
    detector_intensity: object,
    directions: object,
    candidate_matrix: object,
    detectors: Sequence[DetectorRecipe],
    *,
    top_k: int = 3,
) -> DetectorGeometrySearchResult:
    """Rank proposed detector geometries against a shared observation footprint.

    Every geometry candidate maps the same detector image onto the supplied S2
    grid. Their coverage masks are intersected before scoring, so the resulting
    masked normalized-cosine values refer to identical directions and can be
    ranked across the supplied finite candidate set. This is a candidate-grid
    diagnostic, not a continuous calibration method or an acquired-pattern
    uncertainty estimate.
    """
    candidate_detectors = _candidate_detectors(detectors)
    image = np.asarray(detector_intensity, dtype=np.float64)
    if image.shape != candidate_detectors[0].supersampled_shape or not np.all(np.isfinite(image)):
        raise ValueError("detector_intensity must be finite and match every detector candidate")
    sampled = tuple(
        sample_detector_to_s2(image, directions, detector) for detector in candidate_detectors
    )
    common = np.logical_and.reduce([item.covered for item in sampled])
    if int(np.sum(common)) < 2:
        raise ValueError("detector geometry candidates have fewer than two common covered directions")
    entries: list[DetectorGeometryCandidateResult] = []
    for index, (detector, item) in enumerate(zip(candidate_detectors, sampled, strict=True)):
        matches = rank_masked_candidate_matrix(
            candidate_matrix,
            item.values,
            common,
            top_k=top_k,
        )
        entries.append(
            DetectorGeometryCandidateResult(
                candidate_index=index,
                detector=detector,
                covered_direction_count=int(np.sum(item.covered)),
                matches=matches,
            )
        )
    entries.sort(key=lambda item: (-item.score, item.candidate_index))
    return DetectorGeometrySearchResult(
        common_coverage=np.ascontiguousarray(common),
        candidates=tuple(entries),
    )


__all__ = [
    "DetectorGeometryCandidateResult",
    "DetectorGeometrySearchResult",
    "rank_detector_geometry_candidates",
]

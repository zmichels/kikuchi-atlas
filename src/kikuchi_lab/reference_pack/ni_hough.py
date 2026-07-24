"""Small, testable summaries for pinned Ni Hough protocol studies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class HoughVariantSummary:
    """Aggregate diagnostics for one fixed preprocessing variant."""

    identifier: str
    pattern_count: int
    indexed_count: int
    fit_mean: float
    confidence_mean: float
    orientation_delta_mean_deg: float
    orientation_delta_max_deg: float

    def as_dict(self) -> dict[str, float | int | str]:
        """Return a JSON-compatible record with stable field names."""
        return asdict(self)


def summarize_variant(
    *,
    identifier: str,
    fit: Sequence[float],
    confidence: Sequence[float],
    indexed: Sequence[bool],
    symmetry_reduced_orientation_delta_deg: Sequence[float],
) -> HoughVariantSummary:
    """Summarize one Hough variant with explicit symmetry-reduced deltas.

    The deltas are comparisons with a declared reference variant. They are not
    independent orientation errors and deliberately remain separate from the
    fit/confidence metrics.
    """
    values = {
        "fit": np.asarray(fit, dtype=np.float64),
        "confidence": np.asarray(confidence, dtype=np.float64),
        "indexed": np.asarray(indexed, dtype=bool),
        "symmetry_reduced_orientation_delta_deg": np.asarray(
            symmetry_reduced_orientation_delta_deg, dtype=np.float64
        ),
    }
    lengths = {array.size for array in values.values()}
    if len(lengths) != 1 or not lengths or 0 in lengths:
        raise ValueError("Hough variant inputs must be non-empty and the same length")
    for name, array in values.items():
        if name != "indexed" and not np.isfinite(array).all():
            raise ValueError(f"Hough variant {name} values must be finite")
    return HoughVariantSummary(
        identifier=identifier,
        pattern_count=int(values["fit"].size),
        indexed_count=int(np.count_nonzero(values["indexed"])),
        fit_mean=float(values["fit"].mean()),
        confidence_mean=float(values["confidence"].mean()),
        orientation_delta_mean_deg=float(values["symmetry_reduced_orientation_delta_deg"].mean()),
        orientation_delta_max_deg=float(values["symmetry_reduced_orientation_delta_deg"].max()),
    )

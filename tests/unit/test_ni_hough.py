from __future__ import annotations

import math

import pytest

from kikuchi_lab.reference_pack.ni_hough import summarize_variant


def test_summarize_variant_retains_metrics_and_symmetry_reduced_orientation_change() -> None:
    summary = summarize_variant(
        identifier="static-divide",
        fit=[0.25, 0.27, 0.26],
        confidence=[0.74, 0.76, 0.75],
        indexed=[True, True, False],
        symmetry_reduced_orientation_delta_deg=[0.02, 0.03, 0.01],
    )

    assert summary.identifier == "static-divide"
    assert summary.pattern_count == 3
    assert summary.indexed_count == 2
    assert summary.fit_mean == pytest.approx(0.26)
    assert summary.confidence_mean == pytest.approx(0.75)
    assert summary.orientation_delta_mean_deg == pytest.approx(0.02)
    assert summary.orientation_delta_max_deg == pytest.approx(0.03)


def test_summarize_variant_rejects_mismatched_or_nonfinite_inputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        summarize_variant(
            identifier="bad",
            fit=[0.2],
            confidence=[0.8, 0.9],
            indexed=[True],
            symmetry_reduced_orientation_delta_deg=[0.0],
        )

    with pytest.raises(ValueError, match="finite"):
        summarize_variant(
            identifier="bad",
            fit=[math.nan],
            confidence=[0.8],
            indexed=[True],
            symmetry_reduced_orientation_delta_deg=[0.0],
        )

from __future__ import annotations

import numpy as np
import pytest

from kikuchi_lab.diagnostics import image_hough_lines


def test_hough_diagnostic_recovers_vertical_and_horizontal_line_evidence() -> None:
    image = np.zeros((128, 160), dtype=np.float32)
    image[62:66, :] = 1.0
    image[:, 78:82] += 1.0

    result = image_hough_lines(
        image,
        edge_percentile=95.0,
        theta_step_degrees=0.5,
        peak_count=12,
        min_peak_distance_pixels=10,
        min_peak_angle_degrees=1.0,
    )

    assert result.gradient_magnitude.shape == image.shape
    assert result.edge_mask.shape == image.shape
    assert result.accumulator.shape[1] == 360
    assert 0 < np.mean(result.edge_mask) < 0.1
    peak_degrees = np.degrees(result.peak_theta_radians)
    assert np.any(np.abs(peak_degrees) < 2.0)
    assert np.any(np.abs(np.abs(peak_degrees) - 90.0) < 2.0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"edge_percentile": 100.0}, "edge_percentile"),
        ({"theta_step_degrees": 0.0}, "theta_step_degrees"),
        ({"peak_count": 0}, "peak_count"),
    ),
)
def test_hough_diagnostic_rejects_invalid_configuration(kwargs, message) -> None:
    image = np.eye(16, dtype=np.float32)

    with pytest.raises(ValueError, match=message):
        image_hough_lines(image, **kwargs)

from __future__ import annotations

import numpy as np
import pytest

from kikuchi_lab.diagnostics import image_metrics


def test_image_metrics_reports_known_percentiles_clipping_and_gradient() -> None:
    image = np.arange(25, dtype=np.float32).reshape(5, 5)

    metrics = image_metrics(image, black_point=4.0, white_point=20.0)

    assert metrics["percentiles"] == pytest.approx(
        {"p0_5": 0.12, "p1": 0.24, "p50": 12.0, "p99": 23.76, "p99_5": 23.88}
    )
    assert metrics["clipping"] == pytest.approx(
        {"below_black": 4 / 25, "above_white": 4 / 25}
    )
    assert metrics["gradient"]["mean"] == pytest.approx(np.sqrt(26.0))
    assert metrics["gradient"]["p95"] == pytest.approx(np.sqrt(26.0))
    assert sum(metrics["radial_frequency_energy"].values()) == pytest.approx(1.0)
    assert metrics["radial_frequency_bands"] == {
        "units": "cycles_per_pixel",
        "low": [0.0, 0.15],
        "mid": [0.15, 0.35],
        "high": [0.35, None],
    }


def test_radial_frequency_energy_distinguishes_low_and_high_frequency_images() -> None:
    yy, xx = np.indices((64, 64))
    low = np.cos(2 * np.pi * xx / 32).astype(np.float32)
    high = ((-1.0) ** (xx + yy)).astype(np.float32)

    low_energy = image_metrics(low)["radial_frequency_energy"]
    high_energy = image_metrics(high)["radial_frequency_energy"]

    assert low_energy["low"] > low_energy["high"]
    assert high_energy["high"] > high_energy["low"]


def test_rectangular_frequency_energy_is_axis_invariant_in_cycles_per_pixel() -> None:
    yy, xx = np.indices((64, 128))
    along_x = np.cos(2 * np.pi * 0.25 * xx).astype(np.float32)
    along_y = np.cos(2 * np.pi * 0.25 * yy).astype(np.float32)

    x_energy = image_metrics(along_x)["radial_frequency_energy"]
    y_energy = image_metrics(along_y)["radial_frequency_energy"]

    assert x_energy == pytest.approx(y_energy, abs=1e-12)
    assert x_energy["mid"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "image",
    [np.zeros((0, 2), dtype=np.float32), np.zeros((2, 2, 2)), [[0.0, float("nan")]]],
)
def test_image_metrics_rejects_malformed_images(image: object) -> None:
    with pytest.raises(ValueError):
        image_metrics(image)

"""Deterministic image-quality metrics with explicit frequency bands."""

from __future__ import annotations

from typing import Any

import numpy as np

LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL = 0.15
HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL = 0.35


def _image(value: Any) -> np.ndarray:
    image = np.asarray(value, dtype=np.float64)
    if image.ndim != 2 or not image.size or not np.isfinite(image).all():
        raise ValueError("image must be a non-empty finite two-dimensional array")
    return image


def _frequency_energy(image: np.ndarray) -> dict[str, float]:
    centered = image - np.mean(image)
    power = np.abs(np.fft.fft2(centered)) ** 2
    frequency_y = np.fft.fftfreq(image.shape[0])[:, np.newaxis]
    frequency_x = np.fft.fftfreq(image.shape[1])[np.newaxis, :]
    radius = np.hypot(frequency_y, frequency_x)
    bands = {
        "low": power[radius < LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL].sum(dtype=np.float64),
        "mid": power[
            (radius >= LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL)
            & (radius < HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL)
        ].sum(dtype=np.float64),
        "high": power[radius >= HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL].sum(
            dtype=np.float64
        ),
    }
    total = float(sum(bands.values()))
    if total == 0.0:
        return {name: 0.0 for name in bands}
    return {name: float(value / total) for name, value in bands.items()}


def image_metrics(
    value: Any,
    *,
    black_point: float | None = None,
    white_point: float | None = None,
) -> dict[str, Any]:
    """Measure robust range, clipping, gradients, and radial FFT energy."""
    image = _image(value)
    percentiles = np.percentile(image, [0.5, 1.0, 50.0, 99.0, 99.5])
    black = float(percentiles[0] if black_point is None else black_point)
    white = float(percentiles[-1] if white_point is None else white_point)
    if not np.isfinite([black, white]).all() or white < black:
        raise ValueError("black and white points must be finite and ordered")
    gradient_y, gradient_x = np.gradient(image)
    magnitude = np.hypot(gradient_x, gradient_y)
    return {
        "percentiles": {
            "p0_5": float(percentiles[0]),
            "p1": float(percentiles[1]),
            "p50": float(percentiles[2]),
            "p99": float(percentiles[3]),
            "p99_5": float(percentiles[4]),
        },
        "clipping": {
            "below_black": float(np.count_nonzero(image < black) / image.size),
            "above_white": float(np.count_nonzero(image > white) / image.size),
        },
        "gradient": {
            "mean": float(np.mean(magnitude)),
            "p50": float(np.percentile(magnitude, 50.0)),
            "p95": float(np.percentile(magnitude, 95.0)),
            "maximum": float(np.max(magnitude)),
        },
        "radial_frequency_energy": _frequency_energy(image),
        "radial_frequency_bands": {
            "units": "cycles_per_pixel",
            "low": [0.0, LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL],
            "mid": [
                LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL,
                HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL,
            ],
            "high": [HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL, None],
        },
    }

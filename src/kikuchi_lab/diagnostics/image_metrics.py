"""Deterministic image-quality metrics with explicit frequency bands."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import fft as scipy_fft
from skimage import transform

LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL = 0.15
HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL = 0.35
RADIAL_FREQUENCY_ANALYSIS_MAX_AXIS = 512
RADIAL_FREQUENCY_ANALYSIS_VERSION = "radial-rfft-f32-aa512-v1"


def _image(value: Any) -> np.ndarray:
    image = np.asarray(value, dtype=np.float32)
    if (
        image.ndim != 2
        or any(axis < 2 for axis in image.shape)
        or not np.isfinite(image).all()
    ):
        raise ValueError("image must be a non-empty finite two-dimensional array")
    return image


def _analysis_view(image: np.ndarray) -> np.ndarray:
    longest = max(image.shape)
    if longest <= RADIAL_FREQUENCY_ANALYSIS_MAX_AXIS:
        return np.ascontiguousarray(image, dtype=np.float32)
    scale = RADIAL_FREQUENCY_ANALYSIS_MAX_AXIS / longest
    shape = tuple(max(2, int(round(axis * scale))) for axis in image.shape)
    resized = transform.resize(
        image,
        shape,
        order=1,
        mode="reflect",
        anti_aliasing=True,
        preserve_range=True,
    )
    return np.ascontiguousarray(resized, dtype=np.float32)


def _frequency_energy(image: np.ndarray) -> tuple[dict[str, float], dict[str, Any]]:
    analysis = _analysis_view(image)
    centered = analysis - np.mean(analysis, dtype=np.float32)
    spectrum = scipy_fft.rfft2(centered, workers=1)
    power = spectrum.real * spectrum.real + spectrum.imag * spectrum.imag
    spacing_y = image.shape[0] / analysis.shape[0]
    spacing_x = image.shape[1] / analysis.shape[1]
    frequency_y = scipy_fft.fftfreq(analysis.shape[0], d=spacing_y).astype(np.float32)[
        :, np.newaxis
    ]
    frequency_x = scipy_fft.rfftfreq(analysis.shape[1], d=spacing_x).astype(np.float32)[
        np.newaxis, :
    ]
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
        energy = {name: 0.0 for name in bands}
    else:
        energy = {name: float(value / total) for name, value in bands.items()}
    evidence = {
        "version": RADIAL_FREQUENCY_ANALYSIS_VERSION,
        "method": "scipy.fft.rfft2",
        "dtype": "float32",
        "anti_aliasing": True,
        "max_longest_axis": RADIAL_FREQUENCY_ANALYSIS_MAX_AXIS,
        "original_shape": list(image.shape),
        "analysis_shape": list(analysis.shape),
        "thresholds_cycles_per_pixel": {
            "low_mid": LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL,
            "mid_high": HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL,
        },
    }
    return energy, evidence


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
    frequency_energy, frequency_evidence = _frequency_energy(image)
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
        "radial_frequency_energy": frequency_energy,
        "radial_frequency_analysis": frequency_evidence,
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

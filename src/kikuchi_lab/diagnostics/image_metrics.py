"""Deterministic image-quality metrics with explicit frequency bands."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import fft as scipy_fft

LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL = 0.15
HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL = 0.35
RADIAL_FREQUENCY_TILE_MAX_SHAPE = (512, 512)
RADIAL_FREQUENCY_ANALYSIS_VERSION = "radial-rfft-f32-native-tiles512-v2"


def _image(value: Any) -> np.ndarray:
    image = np.asarray(value, dtype=np.float32)
    if (
        image.ndim != 2
        or any(axis < 2 for axis in image.shape)
        or not np.isfinite(image).all()
    ):
        raise ValueError("image must be a non-empty finite two-dimensional array")
    return image


def _tile_coordinates(shape: tuple[int, int]) -> list[tuple[int, int, int, int]]:
    height, width = shape
    tile_height = min(height, RADIAL_FREQUENCY_TILE_MAX_SHAPE[0])
    tile_width = min(width, RADIAL_FREQUENCY_TILE_MAX_SHAPE[1])
    if (tile_height, tile_width) == shape:
        return [(0, 0, tile_height, tile_width)]
    max_y = height - tile_height
    max_x = width - tile_width
    candidates = [
        (max_y // 2, max_x // 2),
        (0, 0),
        (0, max_x),
        (max_y, 0),
        (max_y, max_x),
    ]
    unique: list[tuple[int, int, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for y, x in candidates:
        if (y, x) not in seen:
            seen.add((y, x))
            unique.append((y, x, tile_height, tile_width))
    return unique


def _frequency_energy(image: np.ndarray) -> tuple[dict[str, float], dict[str, Any]]:
    coordinates = _tile_coordinates(image.shape)
    _, _, tile_height, tile_width = coordinates[0]
    frequency_y = scipy_fft.fftfreq(tile_height).astype(np.float32)[:, np.newaxis]
    frequency_x = scipy_fft.rfftfreq(tile_width).astype(np.float32)[np.newaxis, :]
    radius = np.hypot(frequency_y, frequency_x)
    masks = {
        "low": radius < LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL,
        "mid": (
            (radius >= LOW_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL)
            & (radius < HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL)
        ),
        "high": radius >= HIGH_FREQUENCY_CUTOFF_CYCLES_PER_PIXEL,
    }
    hermitian_weights = np.ones(frequency_x.shape[1], dtype=np.float32)
    if tile_width % 2 == 0:
        hermitian_weights[1:-1] = 2.0
    else:
        hermitian_weights[1:] = 2.0
    bands = {name: 0.0 for name in masks}
    tile_records: list[dict[str, list[int]]] = []
    for y, x, height, width in coordinates:
        tile = np.ascontiguousarray(image[y : y + height, x : x + width], dtype=np.float32)
        centered = tile - np.mean(tile, dtype=np.float32)
        spectrum = scipy_fft.rfft2(centered, workers=1)
        power = spectrum.real * spectrum.real + spectrum.imag * spectrum.imag
        power *= hermitian_weights[np.newaxis, :]
        for name, mask in masks.items():
            bands[name] += float(power[mask].sum(dtype=np.float64))
        tile_records.append({"origin": [y, x], "shape": [height, width]})
    total = sum(bands.values())
    if total == 0.0:
        energy = {name: 0.0 for name in bands}
    else:
        energy = {name: float(value / total) for name, value in bands.items()}
    evidence = {
        "version": RADIAL_FREQUENCY_ANALYSIS_VERSION,
        "method": "native_resolution_tiles_scipy.fft.rfft2",
        "dtype": "float32",
        "fft_dtype": "complex64",
        "tile_max_shape": list(RADIAL_FREQUENCY_TILE_MAX_SHAPE),
        "original_shape": list(image.shape),
        "tile_count": len(tile_records),
        "tiles": tile_records,
        "sampling": (
            "full_native_image"
            if len(tile_records) == 1 and tile_records[0]["shape"] == list(image.shape)
            else "center_and_corners_native_resolution"
        ),
        "aggregation": "sum_hermitian_weighted_band_energy_then_normalize",
        "observable_radial_range_cycles_per_pixel": [0.0, float(np.sqrt(0.5))],
        "observable_bands": ["low", "mid", "high"],
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

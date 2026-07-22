"""Raw detector-image Hough diagnostics with explicit edge selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from skimage.transform import hough_line, hough_line_peaks


@dataclass(frozen=True)
class HoughLineDiagnostic:
    """Native-resolution image-space line-accumulator evidence."""

    gradient_magnitude: np.ndarray
    edge_mask: np.ndarray
    accumulator: np.ndarray
    theta_radians: np.ndarray
    distance_pixels: np.ndarray
    peak_accumulator_values: np.ndarray
    peak_theta_radians: np.ndarray
    peak_distance_pixels: np.ndarray
    edge_percentile: float


def _image(value: Any) -> np.ndarray:
    image = np.asarray(value, dtype=np.float32, order="C")
    if image.ndim != 2 or min(image.shape) < 2 or not np.all(np.isfinite(image)):
        raise ValueError("image must be a finite two-dimensional array with both axes at least two")
    return image


def _finite(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def image_hough_lines(
    value: Any,
    *,
    edge_percentile: float = 99.2,
    theta_step_degrees: float = 0.5,
    peak_count: int = 16,
    min_peak_distance_pixels: int = 20,
    min_peak_angle_degrees: float = 2.0,
) -> HoughLineDiagnostic:
    """Accumulate detector-image line evidence without smoothing the input.

    Edges are the native-resolution finite-difference gradient magnitudes at
    or above ``edge_percentile``. The Hough accumulator is image-space only;
    it does not introduce detector geometry, band indexing, or an orientation
    solution.
    """
    image = _image(value)
    percentile = _finite(edge_percentile, name="edge_percentile")
    if not 0.0 < percentile < 100.0:
        raise ValueError("edge_percentile must be strictly between 0 and 100")
    theta_step = _finite(theta_step_degrees, name="theta_step_degrees")
    if not 0.0 < theta_step <= 10.0:
        raise ValueError("theta_step_degrees must be in (0, 10]")
    if type(peak_count) is not int or peak_count <= 0:
        raise ValueError("peak_count must be a positive integer")
    if type(min_peak_distance_pixels) is not int or min_peak_distance_pixels <= 0:
        raise ValueError("min_peak_distance_pixels must be a positive integer")
    min_peak_angle = _finite(min_peak_angle_degrees, name="min_peak_angle_degrees")
    if min_peak_angle <= 0.0:
        raise ValueError("min_peak_angle_degrees must be positive")
    gradient_y, gradient_x = np.gradient(image)
    magnitude = np.ascontiguousarray(np.hypot(gradient_x, gradient_y), dtype=np.float32)
    threshold = float(np.percentile(magnitude, percentile))
    if threshold <= 0.0:
        raise ValueError("image must have non-zero finite-difference contrast")
    edges = np.ascontiguousarray(magnitude >= threshold, dtype=bool)
    if int(np.sum(edges)) < 2:
        raise ValueError("edge threshold retained too few pixels")
    theta = np.deg2rad(np.arange(-90.0, 90.0, theta_step, dtype=np.float64))
    accumulator, theta_values, distances = hough_line(edges, theta=theta)
    minimum_angle_bins = max(1, int(np.ceil(min_peak_angle / theta_step)))
    peak_values, peak_theta, peak_distances = hough_line_peaks(
        accumulator,
        theta_values,
        distances,
        min_distance=min_peak_distance_pixels,
        min_angle=minimum_angle_bins,
        num_peaks=peak_count,
    )
    return HoughLineDiagnostic(
        gradient_magnitude=magnitude,
        edge_mask=edges,
        accumulator=np.ascontiguousarray(accumulator),
        theta_radians=np.ascontiguousarray(theta_values, dtype=np.float64),
        distance_pixels=np.ascontiguousarray(distances, dtype=np.float64),
        peak_accumulator_values=np.ascontiguousarray(peak_values),
        peak_theta_radians=np.ascontiguousarray(peak_theta, dtype=np.float64),
        peak_distance_pixels=np.ascontiguousarray(peak_distances, dtype=np.float64),
        edge_percentile=percentile,
    )

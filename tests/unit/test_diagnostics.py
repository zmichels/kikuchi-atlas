from __future__ import annotations

import importlib

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


def test_large_rectangular_frequency_analysis_is_bounded_and_axis_invariant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("kikuchi_lab.diagnostics.image_metrics")
    real_rfft2 = module.scipy_fft.rfft2
    fft_calls: list[tuple[np.dtype, tuple[int, ...], np.dtype]] = []

    def observed_rfft2(value: np.ndarray, **kwargs: object) -> np.ndarray:
        result = real_rfft2(value, **kwargs)
        fft_calls.append((value.dtype, value.shape, result.dtype))
        return result

    monkeypatch.setattr(module.scipy_fft, "rfft2", observed_rfft2)
    yy, xx = np.indices((700, 1400), dtype=np.float32)
    along_x = np.cos(2 * np.pi * 0.05 * xx).astype(np.float32)
    along_y = np.cos(2 * np.pi * 0.05 * yy).astype(np.float32)

    x_metrics = image_metrics(along_x)
    y_metrics = image_metrics(along_y)
    analysis = x_metrics["radial_frequency_analysis"]

    assert analysis == {
        "version": "radial-rfft-f32-native-tiles512-v2",
        "method": "native_resolution_tiles_scipy.fft.rfft2",
        "dtype": "float32",
        "fft_dtype": "complex64",
        "tile_max_shape": [512, 512],
        "original_shape": [700, 1400],
        "tile_count": 5,
        "tiles": [
            {"origin": [94, 444], "shape": [512, 512]},
            {"origin": [0, 0], "shape": [512, 512]},
            {"origin": [0, 888], "shape": [512, 512]},
            {"origin": [188, 0], "shape": [512, 512]},
            {"origin": [188, 888], "shape": [512, 512]},
        ],
        "sampling": "center_and_corners_native_resolution",
        "aggregation": "sum_hermitian_weighted_band_energy_then_normalize",
        "observable_radial_range_cycles_per_pixel": [0.0, pytest.approx(np.sqrt(0.5))],
        "observable_bands": ["low", "mid", "high"],
        "thresholds_cycles_per_pixel": {"low_mid": 0.15, "mid_high": 0.35},
    }
    assert all(max(tile["shape"]) <= 512 for tile in analysis["tiles"])
    assert fft_calls == [
        (np.dtype("float32"), (512, 512), np.dtype("complex64")),
    ] * 10
    assert x_metrics["radial_frequency_energy"] == pytest.approx(
        y_metrics["radial_frequency_energy"], abs=2e-3
    )


@pytest.mark.parametrize("size", [512, 1024, 2048])
def test_native_nyquist_checkerboard_remains_high_frequency_at_large_sizes(size: int) -> None:
    axis = np.arange(size, dtype=np.int32)
    checkerboard = (1.0 - 2.0 * ((axis[:, None] + axis[None, :]) % 2)).astype(np.float32)

    metrics = image_metrics(checkerboard)

    assert metrics["radial_frequency_energy"]["high"] > 0.999
    analysis = metrics["radial_frequency_analysis"]
    assert analysis["observable_bands"] == ["low", "mid", "high"]
    assert analysis["tile_count"] == (1 if size == 512 else 5)
    assert all(tile["shape"] == [512, 512] for tile in analysis["tiles"])


@pytest.mark.parametrize(
    "image",
    [np.zeros((0, 2), dtype=np.float32), np.zeros((2, 2, 2)), [[0.0, float("nan")]]],
)
def test_image_metrics_rejects_malformed_images(image: object) -> None:
    with pytest.raises(ValueError):
        image_metrics(image)

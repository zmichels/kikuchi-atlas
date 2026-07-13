import json

import numpy as np
import pytest

from kikuchi_lab.processing import (
    HIGH_FREQUENCY_GAIN_CEILING,
    background_divide,
    downsample,
    local_contrast,
    multiscale_detail,
    robust_normalize,
    tone_map,
    unsharp,
)


def band_image(shape: tuple[int, int] = (96, 128)) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=np.float32)
    background = 0.8 + 0.003 * xx + 0.002 * yy
    band = 0.45 * np.exp(-((yy - 0.55 * xx - 18.0) ** 2) / (2 * 3.0**2))
    return np.asarray(background + band, dtype=np.float32)


def assert_stage_result(result, *, shape: tuple[int, int]) -> None:
    assert result.intensity.shape == shape
    assert result.intensity.dtype == np.float32
    assert np.isfinite(result.intensity).all()
    assert not result.intensity.flags.writeable
    assert result.record.input_id != result.record.output_id
    json.dumps(result.record.to_dict())


def test_background_divide_is_finite_positive_and_does_not_mutate_input():
    source = band_image()
    before = source.copy()

    result = background_divide(source, sigma_px=18.0, epsilon=1e-6)

    assert_stage_result(result, shape=source.shape)
    assert np.all(result.intensity > 0)
    np.testing.assert_array_equal(source, before)
    assert result.record.name == "background_divide"


def test_robust_normalize_maps_stated_percentile_window_without_clipping():
    source = np.arange(100, dtype=np.float32).reshape(10, 10)
    result = robust_normalize(source, low_percentile=10.0, high_percentile=90.0)
    low, high = np.percentile(source, (10.0, 90.0))
    expected = (source - low) / (high - low)

    np.testing.assert_allclose(result.intensity, expected)
    assert result.intensity.min() < 0.0
    assert result.intensity.max() > 1.0
    assert result.record.parameters == {
        "low_percentile": 10.0,
        "high_percentile": 90.0,
    }


def test_local_contrast_records_explicit_clahe_domain_clipping():
    source = robust_normalize(
        band_image(), low_percentile=5.0, high_percentile=95.0
    ).intensity
    result = local_contrast(
        source,
        clip_limit=0.02,
        kernel_size=(16, 16),
        input_domain="clip_0_1",
    )

    assert_stage_result(result, shape=source.shape)
    assert result.record.parameters["input_domain"] == "clip_0_1"
    assert result.record.diagnostics["input_clipped_fraction"] > 0.001
    assert [warning.code for warning in result.record.warnings] == ["clipping_fraction"]
    assert result.record.warnings[0].details["stage"] == "local_contrast"


def test_multiscale_detail_has_zero_response_on_constant_image():
    source = np.full((40, 48), 0.37, dtype=np.float32)
    result = multiscale_detail(source, scales_px=(1.0, 3.0), gains=(0.7, 0.3))

    np.testing.assert_allclose(result.intensity, source, atol=1e-6)


def test_multiscale_detail_records_measured_transfer_and_warns_without_adjusting():
    source = (np.indices((64, 64)).sum(axis=0) % 2).astype(np.float32)
    gains = (1.5,)
    result = multiscale_detail(source, scales_px=(1.0,), gains=gains)

    assert result.record.parameters["gains"] == gains
    with pytest.raises(TypeError):
        result.record.parameters["gains"] = (0.0, 0.0)
    assert [warning.code for warning in result.record.warnings] == [
        "excessive_high_frequency_gain"
    ]
    measured = result.record.diagnostics["high_frequency_amplification"]
    assert measured > HIGH_FREQUENCY_GAIN_CEILING
    assert result.record.warnings[0].details["measured_ratio"] == measured


def test_unsharp_does_not_clip_internal_overshoot():
    source = np.zeros((32, 32), dtype=np.float32)
    source[:, 16:] = 1.0
    result = unsharp(source, radius_px=1.0, amount=2.0, threshold=0.0)

    assert result.intensity.min() < 0.0
    assert result.intensity.max() > 1.0


def test_unsharp_warns_without_adjusting_excessive_gain():
    source = (np.indices((64, 64)).sum(axis=0) % 2).astype(np.float32)
    requested = 1.5
    result = unsharp(
        source, radius_px=1.0, amount=requested, threshold=0.0
    )

    assert result.record.parameters["amount"] == requested
    assert [warning.code for warning in result.record.warnings] == [
        "excessive_high_frequency_gain"
    ]
    assert result.record.diagnostics["high_frequency_amplification"] > 2.0


def test_frequency_transfer_is_robust_for_constant_and_near_zero_images():
    constant = unsharp(
        np.full((32, 32), 0.4, dtype=np.float32),
        radius_px=1.0,
        amount=4.0,
        threshold=0.0,
    )
    near_zero = multiscale_detail(
        np.full((32, 32), 1e-20, dtype=np.float32),
        scales_px=(1.0,),
        gains=(4.0,),
    )

    assert constant.record.diagnostics["high_frequency_amplification"] == 1.0
    assert near_zero.record.diagnostics["high_frequency_amplification"] == 1.0
    assert not constant.record.warnings
    assert not near_zero.record.warnings


def test_tone_map_is_monotonic_for_positive_gamma():
    source = np.linspace(-0.2, 1.2, 512, dtype=np.float32).reshape(16, 32)
    result = tone_map(source, black=0.0, white=1.0, gamma=0.8)

    assert np.all(np.diff(result.intensity.ravel()) >= 0.0)
    assert result.intensity.min() == 0.0
    assert result.intensity.max() == 1.0
    assert [warning.code for warning in result.record.warnings] == ["clipping_fraction"]
    assert result.record.warnings[0].details["fraction"] > 0.001


def test_nonmonotonic_tone_is_reported_and_not_silently_rewritten():
    source = np.linspace(0.0, 1.0, 64, dtype=np.float32).reshape(8, 8)
    result = tone_map(source, black=1.0, white=0.0, gamma=1.0)

    assert result.record.parameters["black"] == 1.0
    assert result.record.parameters["white"] == 0.0
    assert "nonmonotonic_tone" in [warning.code for warning in result.record.warnings]
    assert np.all(np.diff(result.intensity.ravel()) <= 0.0)


def test_downsample_is_antialiased_and_uses_requested_geometry():
    checker = (np.indices((128, 160)).sum(axis=0) % 2).astype(np.float32)
    result = downsample(checker, shape=(32, 40))

    assert_stage_result(result, shape=(32, 40))
    assert np.max(np.abs(result.intensity - 0.5)) < 0.02
    assert result.record.parameters["shape"] == (32, 40)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda image: background_divide(image, sigma_px=0, epsilon=1e-6), "sigma_px"),
        (
            lambda image: robust_normalize(
                image, low_percentile=50, high_percentile=50
            ),
            "percentile",
        ),
        (lambda image: tone_map(image, black=0, white=1, gamma=0), "gamma"),
        (lambda image: downsample(image, shape=(0, 4)), "shape"),
    ],
)
def test_invalid_stage_parameters_fail_explicitly(call, message):
    with pytest.raises(ValueError, match=message):
        call(band_image())

"""Pure float32 image-processing stages with inspectable execution records."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable

import numpy as np
from skimage import exposure, filters, transform

from kikuchi_lab.model.identity import plain_data, stable_id

CLIPPING_FRACTION_WARNING = 0.001
HIGH_FREQUENCY_GAIN_CEILING = 2.0


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    def freeze(item: Any) -> Any:
        item = plain_data(item)
        if isinstance(item, dict):
            return MappingProxyType({key: freeze(child) for key, child in item.items()})
        if isinstance(item, list):
            return tuple(freeze(child) for child in item)
        return item

    return freeze(value)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _owned_float32(image: Any) -> np.ndarray:
    array = np.array(image, dtype=np.float32, order="C", copy=True)
    if array.ndim != 2 or not array.size:
        raise ValueError("processing input must be a non-empty two-dimensional image")
    if not np.isfinite(array).all():
        raise ValueError("processing input must contain only finite values")
    return np.frombuffer(array.tobytes(order="C"), dtype=np.float32).reshape(array.shape)


def image_id(image: np.ndarray) -> str:
    array = np.ascontiguousarray(image, dtype=np.float32)
    checksum = hashlib.sha256(array.tobytes(order="C")).hexdigest()
    return stable_id(
        "image",
        {"shape": list(array.shape), "dtype": "float32", "sha256": checksum},
    )


@dataclass(frozen=True)
class ProcessingWarning:
    code: str
    message: str
    details: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.code or not self.message:
            raise ValueError("processing warnings require a code and message")
        object.__setattr__(self, "details", _freeze_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": _plain(self.details)}


@dataclass(frozen=True)
class StageRecord:
    name: str
    parameters: Mapping[str, Any]
    input_id: str
    output_id: str
    diagnostics: Mapping[str, Any] = MappingProxyType({})
    warnings: tuple[ProcessingWarning, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        object.__setattr__(self, "diagnostics", _freeze_mapping(self.diagnostics))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parameters": _plain(self.parameters),
            "input_id": self.input_id,
            "output_id": self.output_id,
            "diagnostics": _plain(self.diagnostics),
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


@dataclass(frozen=True, eq=False)
class StageResult:
    intensity: np.ndarray
    record: StageRecord

    def __post_init__(self) -> None:
        object.__setattr__(self, "intensity", _owned_float32(self.intensity))
        if self.record.output_id != image_id(self.intensity):
            raise ValueError("stage record output ID disagrees with intensity payload")


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _execute(
    name: str,
    image: Any,
    parameters: Mapping[str, Any],
    operation: Callable[[np.ndarray], Any],
    warnings: Sequence[ProcessingWarning] = (),
    analyzer: Callable[
        [np.ndarray, np.ndarray], tuple[Mapping[str, Any], Sequence[ProcessingWarning]]
    ]
    | None = None,
) -> StageResult:
    source = _owned_float32(image)
    output = _owned_float32(operation(source))
    diagnostics: Mapping[str, Any] = {}
    analyzed_warnings: Sequence[ProcessingWarning] = ()
    if analyzer is not None:
        diagnostics, analyzed_warnings = analyzer(source, output)
    record = StageRecord(
        name=name,
        parameters=parameters,
        input_id=image_id(source),
        output_id=image_id(output),
        diagnostics=diagnostics,
        warnings=(*warnings, *analyzed_warnings),
    )
    return StageResult(output, record)


def background_divide(image: Any, *, sigma_px: float, epsilon: float) -> StageResult:
    sigma = _finite("sigma_px", sigma_px)
    floor = _finite("epsilon", epsilon)
    if sigma <= 0:
        raise ValueError("sigma_px must be positive")
    if floor <= 0:
        raise ValueError("epsilon must be positive")

    def operation(source: np.ndarray) -> np.ndarray:
        background = filters.gaussian(source, sigma=sigma, preserve_range=True)
        return source / np.maximum(background, floor)

    return _execute(
        "background_divide",
        image,
        {"sigma_px": sigma, "epsilon": floor},
        operation,
    )


def robust_normalize(
    image: Any, *, low_percentile: float, high_percentile: float
) -> StageResult:
    low_p = _finite("low_percentile", low_percentile)
    high_p = _finite("high_percentile", high_percentile)
    if not 0 <= low_p < high_p <= 100:
        raise ValueError("percentile window must satisfy 0 <= low < high <= 100")

    def operation(source: np.ndarray) -> np.ndarray:
        low, high = np.percentile(source, (low_p, high_p))
        width = float(high - low)
        if width <= np.finfo(np.float32).eps:
            return np.zeros_like(source)
        return (source - low) / width

    return _execute(
        "robust_normalize",
        image,
        {"low_percentile": low_p, "high_percentile": high_p},
        operation,
    )


def local_contrast(
    image: Any,
    *,
    clip_limit: float,
    kernel_size: int | tuple[int, int],
    input_domain: str,
) -> StageResult:
    clip = _finite("clip_limit", clip_limit)
    if clip <= 0:
        raise ValueError("clip_limit must be positive")
    if isinstance(kernel_size, int):
        kernel = (kernel_size, kernel_size)
    else:
        kernel = tuple(kernel_size)
    if len(kernel) != 2 or any(isinstance(v, bool) or int(v) != v or v <= 0 for v in kernel):
        raise ValueError("kernel_size must contain two positive integers")
    kernel = (int(kernel[0]), int(kernel[1]))
    if input_domain != "clip_0_1":
        raise ValueError("input_domain must be 'clip_0_1'")

    def operation(source: np.ndarray) -> np.ndarray:
        domain_input = np.clip(source, 0.0, 1.0)
        return exposure.equalize_adapthist(
            domain_input, kernel_size=kernel, clip_limit=clip
        )

    def analyze(
        source: np.ndarray, _output: np.ndarray
    ) -> tuple[Mapping[str, Any], Sequence[ProcessingWarning]]:
        fraction = float(np.count_nonzero((source < 0.0) | (source > 1.0))) / source.size
        diagnostics = {"input_clipped_fraction": fraction, "input_domain": [0.0, 1.0]}
        if fraction <= CLIPPING_FRACTION_WARNING:
            return diagnostics, ()
        warning = ProcessingWarning(
            code="clipping_fraction",
            message="CLAHE input-domain conversion clips more than 0.1% of pixels.",
            details={
                "stage": "local_contrast",
                "fraction": fraction,
                "threshold": CLIPPING_FRACTION_WARNING,
                "policy": input_domain,
            },
        )
        return diagnostics, (warning,)

    return _execute(
        "local_contrast",
        image,
        {
            "clip_limit": clip,
            "kernel_size": list(kernel),
            "input_domain": input_domain,
        },
        operation,
        analyzer=analyze,
    )


def multiscale_detail(
    image: Any, *, scales_px: Sequence[float], gains: Sequence[float]
) -> StageResult:
    scales = tuple(_finite("scale", value) for value in scales_px)
    gain_values = tuple(_finite("gain", value) for value in gains)
    if not scales or len(scales) != len(gain_values) or any(scale <= 0 for scale in scales):
        raise ValueError("scales_px and gains must be non-empty, equal-length sequences")

    def operation(source: np.ndarray) -> np.ndarray:
        output = source.copy()
        for scale, gain in zip(scales, gain_values, strict=True):
            lowpass = filters.gaussian(source, sigma=scale, preserve_range=True)
            output += gain * (source - lowpass)
        return output

    return _execute(
        "multiscale_detail",
        image,
        {"scales_px": list(scales), "gains": list(gain_values)},
        operation,
        analyzer=_high_frequency_analyzer(stage="multiscale_detail"),
    )


def unsharp(
    image: Any, *, radius_px: float, amount: float, threshold: float
) -> StageResult:
    radius = _finite("radius_px", radius_px)
    gain = _finite("amount", amount)
    cutoff = _finite("threshold", threshold)
    if radius <= 0 or gain < 0 or cutoff < 0:
        raise ValueError("radius_px must be positive; amount and threshold must be non-negative")

    def operation(source: np.ndarray) -> np.ndarray:
        return filters.unsharp_mask(
            source,
            radius=radius,
            amount=gain,
            preserve_range=True,
        ) if cutoff == 0 else _thresholded_unsharp(source, radius, gain, cutoff)

    return _execute(
        "unsharp",
        image,
        {"radius_px": radius, "amount": gain, "threshold": cutoff},
        operation,
        analyzer=_high_frequency_analyzer(stage="unsharp"),
    )


def _high_frequency_amplification(source: np.ndarray, output: np.ndarray) -> float:
    """Return RMS Fourier-amplitude transfer above 0.25 cycles/pixel."""
    fy = np.fft.fftfreq(source.shape[0])[:, np.newaxis]
    fx = np.fft.rfftfreq(source.shape[1])[np.newaxis, :]
    high_frequency = np.hypot(fy, fx) >= 0.25
    if not np.any(high_frequency):
        return 1.0
    input_spectrum = np.fft.rfft2(source.astype(np.float64, copy=False))
    output_spectrum = np.fft.rfft2(output.astype(np.float64, copy=False))
    input_rms = float(np.sqrt(np.mean(np.abs(input_spectrum[high_frequency]) ** 2)))
    output_rms = float(np.sqrt(np.mean(np.abs(output_spectrum[high_frequency]) ** 2)))
    numerical_floor = 1e-12 * source.size
    if input_rms <= numerical_floor and output_rms <= numerical_floor:
        return 1.0
    return output_rms / max(input_rms, numerical_floor)


def _high_frequency_analyzer(
    *, stage: str
) -> Callable[
    [np.ndarray, np.ndarray], tuple[Mapping[str, Any], Sequence[ProcessingWarning]]
]:
    def analyze(
        source: np.ndarray, output: np.ndarray
    ) -> tuple[Mapping[str, Any], Sequence[ProcessingWarning]]:
        ratio = _high_frequency_amplification(source, output)
        diagnostics = {
            "high_frequency_amplification": ratio,
            "metric": "rms_fft_amplitude_ratio_above_0.25_cycles_per_pixel",
            "ceiling": HIGH_FREQUENCY_GAIN_CEILING,
        }
        if ratio <= HIGH_FREQUENCY_GAIN_CEILING:
            return diagnostics, ()
        warning = ProcessingWarning(
            code="excessive_high_frequency_gain",
            message="Measured high-frequency amplification exceeds the documented ceiling.",
            details={
                "stage": stage,
                "measured_ratio": ratio,
                "ceiling": HIGH_FREQUENCY_GAIN_CEILING,
                "metric": diagnostics["metric"],
            },
        )
        return diagnostics, (warning,)

    return analyze


def _thresholded_unsharp(
    source: np.ndarray, radius: float, amount: float, threshold: float
) -> np.ndarray:
    blurred = filters.gaussian(source, sigma=radius, preserve_range=True)
    detail = source - blurred
    return source + amount * np.where(np.abs(detail) >= threshold, detail, 0.0)


def tone_map(image: Any, *, black: float, white: float, gamma: float) -> StageResult:
    black_value = _finite("black", black)
    white_value = _finite("white", white)
    gamma_value = _finite("gamma", gamma)
    if black_value == white_value:
        raise ValueError("black and white must differ")
    if gamma_value <= 0:
        raise ValueError("gamma must be positive")
    source = _owned_float32(image)
    normalized = (source - black_value) / (white_value - black_value)
    clipped_fraction = float(np.count_nonzero((normalized < 0) | (normalized > 1))) / source.size
    warnings: list[ProcessingWarning] = []
    if clipped_fraction > CLIPPING_FRACTION_WARNING:
        warnings.append(
            ProcessingWarning(
                code="clipping_fraction",
                message="Tone mapping clips more than 0.1% of pixels.",
                details={
                    "fraction": clipped_fraction,
                    "threshold": CLIPPING_FRACTION_WARNING,
                },
            )
        )
    if white_value < black_value:
        warnings.append(
            ProcessingWarning(
                code="nonmonotonic_tone",
                message="Tone endpoints produce a decreasing intensity mapping.",
                details={"black": black_value, "white": white_value},
            )
        )

    def operation(_: np.ndarray) -> np.ndarray:
        return np.power(np.clip(normalized, 0.0, 1.0), 1.0 / gamma_value)

    return _execute(
        "tone_map",
        source,
        {"black": black_value, "white": white_value, "gamma": gamma_value},
        operation,
        warnings,
    )


def downsample(image: Any, *, shape: tuple[int, int] | Sequence[int]) -> StageResult:
    target = tuple(shape)
    if len(target) != 2 or any(
        isinstance(value, bool) or int(value) != value or value <= 0 for value in target
    ):
        raise ValueError("shape must contain two positive integers")
    target = (int(target[0]), int(target[1]))
    source = _owned_float32(image)
    if any(output > input_size for output, input_size in zip(target, source.shape, strict=True)):
        raise ValueError("downsample shape cannot exceed the input shape")

    def operation(array: np.ndarray) -> np.ndarray:
        return transform.resize(
            array,
            target,
            order=1,
            mode="reflect",
            anti_aliasing=True,
            preserve_range=True,
        )

    return _execute("downsample", source, {"shape": list(target)}, operation)


STAGE_FUNCTIONS: Mapping[str, Callable[..., StageResult]] = MappingProxyType(
    {
        "background_divide": background_divide,
        "robust_normalize": robust_normalize,
        "local_contrast": local_contrast,
        "multiscale_detail": multiscale_detail,
        "unsharp": unsharp,
        "tone_map": tone_map,
        "downsample": downsample,
    }
)

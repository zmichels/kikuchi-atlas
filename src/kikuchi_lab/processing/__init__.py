"""Inspectable acquisition-look and gallery-look processing."""

from .graph import ProcessingResult, run_graph
from .presets import load_processing_recipe
from .stages import (
    CLIPPING_FRACTION_WARNING,
    HIGH_FREQUENCY_GAIN_CEILING,
    ProcessingWarning,
    StageRecord,
    StageResult,
    background_divide,
    downsample,
    local_contrast,
    multiscale_detail,
    robust_normalize,
    tone_map,
    unsharp,
)

__all__ = [
    "CLIPPING_FRACTION_WARNING",
    "HIGH_FREQUENCY_GAIN_CEILING",
    "ProcessingResult",
    "ProcessingWarning",
    "StageRecord",
    "StageResult",
    "background_divide",
    "downsample",
    "load_processing_recipe",
    "local_contrast",
    "multiscale_detail",
    "robust_normalize",
    "run_graph",
    "tone_map",
    "unsharp",
]

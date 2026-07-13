"""YAML loading for explicit, version-controlled processing presets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from kikuchi_lab.model import DetectorPatternProduct, ProcessingRecipe, ProcessingStage


_PARAMETERS = {
    "background_divide": {"sigma_px", "epsilon"},
    "robust_normalize": {"low_percentile", "high_percentile"},
    "local_contrast": {"clip_limit", "kernel_size", "input_domain"},
    "multiscale_detail": {"scales_px", "gains"},
    "unsharp": {"radius_px", "amount", "threshold"},
    "tone_map": {"black", "white", "gamma"},
    "downsample": {"shape"},
}


def _numeric(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a numeric number")


def _numeric_sequence(name: str, value: Any) -> None:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be a numeric sequence")
    for item in value:
        _numeric(name, item)


def _integer_pair(name: str, value: Any) -> None:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be a numeric shape sequence")
    if len(value) != 2 or any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value
    ):
        raise ValueError(f"{name} must contain two positive integer shape values")


def _validate_stage_parameters(
    name: str, parameters: dict[str, Any], *, allow_detector_native: bool
) -> None:
    expected = _PARAMETERS.get(name)
    if expected is None:
        raise ValueError(f"unknown processing stage: {name}")
    if set(parameters) != expected:
        raise ValueError(f"{name} parameters must be exactly {sorted(expected)}")
    if name in {"background_divide", "robust_normalize", "unsharp", "tone_map"}:
        for key, value in parameters.items():
            _numeric(key, value)
    elif name == "local_contrast":
        _numeric("clip_limit", parameters["clip_limit"])
        kernel = parameters["kernel_size"]
        if isinstance(kernel, bool) or not isinstance(kernel, (int, list, tuple)):
            raise TypeError("kernel_size must be an integer or numeric shape sequence")
        if isinstance(kernel, int):
            if kernel <= 0:
                raise ValueError("kernel_size must be positive")
        else:
            _integer_pair("kernel_size", kernel)
        if parameters["input_domain"] != "clip_0_1":
            raise ValueError("input_domain must be 'clip_0_1'")
    elif name == "multiscale_detail":
        _numeric_sequence("scales_px", parameters["scales_px"])
        _numeric_sequence("gains", parameters["gains"])
    elif name == "downsample":
        shape = parameters["shape"]
        if allow_detector_native and shape == "detector_native":
            return
        _integer_pair("shape", shape)


@dataclass(frozen=True)
class ProcessingPreset:
    schema_version: int
    name: str
    intent: str
    recipe: ProcessingRecipe

    @property
    def stages(self) -> tuple[ProcessingStage, ...]:
        return self.recipe.stages

    @property
    def recipe_id(self) -> str:
        """Computational identity; descriptive name and intent are excluded."""
        return self.recipe.recipe_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "intent": self.intent,
            "stages": [stage.to_dict() for stage in self.stages],
        }


def load_processing_recipe(path: str | Path) -> ProcessingPreset:
    payload: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("stages"), list):
        raise ValueError("processing preset requires a stages list")
    schema_version = payload.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != 1:
        raise ValueError("processing preset schema_version must be supported version 1")
    for field in ("name", "intent"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"processing preset requires non-empty {field}")
    stages: list[ProcessingStage] = []
    for item in payload["stages"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("each processing stage requires a name")
        parameters = item.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("processing stage parameters must be an object")
        _validate_stage_parameters(item["name"], parameters, allow_detector_native=True)
        stages.append(ProcessingStage(name=item["name"], parameters=parameters))
    return ProcessingPreset(
        schema_version=1,
        name=payload["name"],
        intent=payload["intent"],
        recipe=ProcessingRecipe(tuple(stages)),
    )


def resolve_processing_recipe(
    recipe: ProcessingPreset | ProcessingRecipe, source: DetectorPatternProduct
) -> ProcessingRecipe:
    """Compile symbolic stage parameters against canonical detector metadata."""
    detector = source.metadata.get("detector")
    if not isinstance(detector, dict) and not hasattr(detector, "get"):
        raise ValueError("source projection requires canonical detector metadata")
    detector_shape = detector.get("shape")
    _integer_pair("detector shape", detector_shape)
    resolved: list[ProcessingStage] = []
    for stage in recipe.stages:
        parameters = stage.to_dict()["parameters"]
        if stage.name == "downsample" and parameters.get("shape") == "detector_native":
            parameters["shape"] = list(detector_shape)
        _validate_stage_parameters(stage.name, parameters, allow_detector_native=False)
        resolved.append(ProcessingStage(stage.name, parameters))
    return ProcessingRecipe(tuple(resolved))

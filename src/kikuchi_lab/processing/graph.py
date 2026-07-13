"""Immutable ordered execution of project-owned processing recipes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from kikuchi_lab.model import DetectorPatternProduct, ProcessingRecipe
from kikuchi_lab.model.identity import stable_id

from .stages import STAGE_FUNCTIONS, StageResult, image_id


@dataclass(frozen=True, eq=False)
class ProcessingResult:
    source_projection_id: str
    processing_recipe_id: str
    product_id: str
    stages: tuple[StageResult, ...]
    geometry: Mapping[str, Any]

    def __post_init__(self) -> None:
        stages = tuple(self.stages)
        if not stages:
            raise ValueError("processing result requires at least one stage")
        if any(
            left.record.output_id != right.record.input_id
            for left, right in zip(stages, stages[1:], strict=False)
        ):
            raise ValueError("processing result stage identity chain is discontinuous")
        object.__setattr__(self, "stages", stages)
        object.__setattr__(
            self,
            "geometry",
            MappingProxyType(
                {
                    key: tuple(value) if isinstance(value, list) else value
                    for key, value in self.geometry.items()
                }
            ),
        )

    @property
    def final_intensity(self) -> np.ndarray:
        return self.stages[-1].intensity

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_projection_id": self.source_projection_id,
            "processing_recipe_id": self.processing_recipe_id,
            "product_id": self.product_id,
            "final_image_id": image_id(self.final_intensity),
            "geometry": {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in self.geometry.items()
            },
            "stages": [stage.record.to_dict() for stage in self.stages],
        }


def _geometry(source: DetectorPatternProduct, output: np.ndarray) -> dict[str, Any]:
    detector = source.metadata.get("detector", {})
    geometry = {
        "source_shape": list(source.intensity.shape),
        "output_shape": list(output.shape),
        "physical_extent_um": list(detector.get("physical_extent_um", [])),
        "supersampling": int(source.metadata.get("supersampling", 1)),
    }
    expected_source = detector.get("supersampled_shape")
    if expected_source and tuple(expected_source) != source.intensity.shape:
        raise ValueError("source projection shape disagrees with detector supersampling geometry")
    expected_output = detector.get("shape")
    if expected_output and tuple(expected_output) != output.shape:
        raise ValueError("processing output shape disagrees with physical detector geometry")
    return geometry


def run_graph(
    source_projection: DetectorPatternProduct, recipe: ProcessingRecipe
) -> ProcessingResult:
    if not recipe.stages:
        raise ValueError("processing recipe must contain at least one stage")
    current = source_projection.intensity
    results: list[StageResult] = []
    for stage in recipe.stages:
        try:
            function = STAGE_FUNCTIONS[stage.name]
        except KeyError as exc:
            raise ValueError(f"unknown processing stage: {stage.name}") from exc
        parameters = stage.to_dict()["parameters"]
        result = function(current, **parameters)
        if results and result.record.input_id != results[-1].record.output_id:
            raise RuntimeError("processing stage identity chain is discontinuous")
        results.append(result)
        current = result.intensity
    geometry = _geometry(source_projection, current)
    product_id = stable_id(
        "processed",
        {
            "source_projection_id": source_projection.product_id,
            "processing_recipe_id": recipe.recipe_id,
            "final_image_id": image_id(current),
            "stages": [result.record.to_dict() for result in results],
            "geometry": geometry,
        },
    )
    return ProcessingResult(
        source_projection_id=source_projection.product_id,
        processing_recipe_id=recipe.recipe_id,
        product_id=product_id,
        stages=tuple(results),
        geometry=geometry,
    )

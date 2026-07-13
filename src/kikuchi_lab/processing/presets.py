"""YAML loading for explicit, version-controlled processing presets."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Any

import yaml

from kikuchi_lab.model import ProcessingRecipe, ProcessingStage


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
        stages.append(ProcessingStage(name=item["name"], parameters=parameters))
    return ProcessingPreset(
        schema_version=1,
        name=payload["name"],
        intent=payload["intent"],
        recipe=ProcessingRecipe(tuple(stages)),
    )

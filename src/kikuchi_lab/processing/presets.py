"""YAML loading for explicit, version-controlled processing presets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from kikuchi_lab.model import ProcessingRecipe, ProcessingStage


def load_processing_recipe(path: str | Path) -> ProcessingRecipe:
    payload: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("stages"), list):
        raise ValueError("processing preset requires a stages list")
    stages: list[ProcessingStage] = []
    for item in payload["stages"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("each processing stage requires a name")
        parameters = item.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("processing stage parameters must be an object")
        stages.append(ProcessingStage(name=item["name"], parameters=parameters))
    return ProcessingRecipe(tuple(stages))

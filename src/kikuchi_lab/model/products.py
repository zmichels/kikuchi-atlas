"""Immutable source-neutral pattern products."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from .identity import plain_data, stable_id


def _owned_float32(value: Any, *, ndim: int) -> np.ndarray:
    array = np.array(value, dtype=np.float32, order="C", copy=True)
    if array.ndim != ndim:
        raise ValueError(f"intensity must have {ndim} dimensions; got shape {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError("intensity must contain only finite values")
    array.setflags(write=False)
    return array


def _array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array, dtype=np.float32)
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def _freeze(value: Any) -> Any:
    value = plain_data(value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _required_text(metadata: Mapping[str, Any], key: str) -> None:
    if not isinstance(metadata.get(key), str) or not metadata[key]:
        raise ValueError(f"metadata requires non-empty {key}")


@dataclass(frozen=True)
class MasterPatternProduct:
    intensity: np.ndarray
    metadata: Mapping[str, Any]
    array_sha256: str
    product_id: str

    @classmethod
    def from_array(cls, intensity: Any, *, metadata: Mapping[str, Any]) -> MasterPatternProduct:
        array = _owned_float32(intensity, ndim=3)
        if array.shape[0] != 2 or array.shape[1] < 1 or array.shape[2] < 1:
            raise ValueError("master intensity shape must be (2, y, x) for north and south")
        plain = plain_data(metadata)
        for key in (
            "source_id",
            "phase_id",
            "simulation_recipe_id",
            "projection",
            "intensity_units",
            "coordinate_frame",
        ):
            _required_text(plain, key)
        if plain.get("hemisphere_order") != ["north", "south"]:
            raise ValueError("hemisphere_order must be ['north', 'south']")
        voltage = float(plain.get("simulation_voltage_kv", math.nan))
        energy = float(plain.get("energy_kev", math.nan))
        if not math.isfinite(voltage) or not math.isfinite(energy) or voltage <= 0 or energy <= 0:
            raise ValueError("simulation_voltage_kv and energy_kev must be finite and positive")
        if not math.isclose(voltage, energy, rel_tol=1e-9, abs_tol=0.0):
            raise ValueError("energy_kev is inconsistent with simulation_voltage_kv")
        checksum = _array_sha256(array)
        product_id = stable_id("master", {"metadata": plain, "array_sha256": checksum})
        return cls(array, _freeze(plain), checksum, product_id)

    def metadata_dict(self) -> dict[str, Any]:
        return _thaw(self.metadata)


@dataclass(frozen=True)
class DetectorPatternProduct:
    intensity: np.ndarray
    master_product_id: str
    projection_recipe_id: str
    metadata: Mapping[str, Any]
    array_sha256: str
    product_id: str

    @classmethod
    def from_array(
        cls,
        intensity: Any,
        *,
        master_product_id: str,
        projection_recipe_id: str,
        metadata: Mapping[str, Any],
    ) -> DetectorPatternProduct:
        array = _owned_float32(intensity, ndim=2)
        if not array.size:
            raise ValueError("detector intensity cannot be empty")
        if not master_product_id or not projection_recipe_id:
            raise ValueError("master_product_id and projection_recipe_id are required")
        plain = plain_data(metadata)
        for key in ("intensity_units", "detector_frame"):
            _required_text(plain, key)
        energy = float(plain.get("energy_kev", math.nan))
        if not math.isfinite(energy) or energy <= 0:
            raise ValueError("energy_kev must be finite and positive")
        checksum = _array_sha256(array)
        identity_payload = {
            "metadata": plain,
            "array_sha256": checksum,
            "master_product_id": master_product_id,
            "projection_recipe_id": projection_recipe_id,
        }
        return cls(
            array,
            master_product_id,
            projection_recipe_id,
            _freeze(plain),
            checksum,
            stable_id("detector", identity_payload),
        )

    def metadata_dict(self) -> dict[str, Any]:
        return _thaw(self.metadata)

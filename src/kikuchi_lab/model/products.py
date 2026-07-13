"""Immutable source-neutral pattern products."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from .identity import plain_data, stable_id

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _owned_float32(value: Any, *, ndim: int) -> np.ndarray:
    converted = np.array(value, dtype=np.float32, order="C", copy=True)
    if converted.ndim != ndim:
        raise ValueError(f"intensity must have {ndim} dimensions; got shape {converted.shape}")
    if not np.isfinite(converted).all():
        raise ValueError("intensity must contain only finite values")
    # A write-disabled owned ndarray can later have writeability re-enabled.
    # Backing this view with immutable bytes makes that escalation impossible.
    array = np.frombuffer(converted.tobytes(order="C"), dtype=np.float32).reshape(converted.shape)
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


def _required_mapping(metadata: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = metadata.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"metadata requires {key} object")
    return value


def _validate_sha256(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase 64-character SHA-256")


def _canonical_real(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a canonical JSON number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _validate_phase(metadata: Mapping[str, Any]) -> None:
    phase = _required_mapping(metadata, "phase")
    _required_text(phase, "name")
    _required_text(phase, "formula")
    space_group = _required_mapping(phase, "space_group")
    number = space_group.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 230:
        raise ValueError("phase space_group number must be an integer in [1, 230]")
    _required_text(space_group, "setting")
    lattice = _required_mapping(phase, "lattice")
    if lattice.get("units") != "angstrom":
        raise ValueError("phase lattice units must be angstrom")
    values = lattice.get("values")
    if not isinstance(values, list) or len(values) != 6:
        raise ValueError("phase lattice values must contain six values")
    numeric = [_canonical_real(value, "phase lattice value") for value in values]
    if any(value <= 0 for value in numeric[:3]) or any(
        not 0 < value <= 180 for value in numeric[3:]
    ):
        raise ValueError("phase lattice lengths and angles are invalid")


def _validate_source(metadata: Mapping[str, Any]) -> str:
    source = _required_mapping(metadata, "source_structure")
    _required_text(source, "identifier")
    _validate_sha256(source.get("sha256"), "source_structure sha256")
    provenance = _required_mapping(source, "provenance")
    for key in ("uri", "license", "citation"):
        _required_text(provenance, key)
    _required_text(source, "source_id")
    # SourceRecord owns source identity. The human/catalog identifier remains
    # useful metadata, but must not create a second incompatible identity.
    source_payload = {
        "uri": provenance["uri"],
        "sha256": source["sha256"],
        "license": provenance["license"],
        "citation": provenance["citation"],
    }
    expected_source_id = stable_id("source", source_payload)
    if source["source_id"] != expected_source_id:
        raise ValueError("source_structure source_id disagrees with its canonical record")
    return expected_source_id


def _validate_generator(metadata: Mapping[str, Any]) -> None:
    generator = _required_mapping(metadata, "generator")
    _required_text(generator, "name")
    _required_text(generator, "version")


def _validate_simulation(metadata: Mapping[str, Any]) -> tuple[float, str]:
    simulation = _required_mapping(metadata, "simulation")
    _required_text(simulation, "recipe_id")
    recipe_sha256 = simulation.get("recipe_sha256")
    _validate_sha256(recipe_sha256, "simulation recipe_sha256")
    expected_recipe_id = f"recipe-{recipe_sha256[:16]}"
    if simulation["recipe_id"] != expected_recipe_id:
        raise ValueError("simulation recipe_id disagrees with recipe_sha256")
    voltage = _canonical_real(simulation.get("voltage_kv"), "simulation voltage_kv")
    if voltage <= 0:
        raise ValueError("simulation voltage_kv must be finite and positive")
    return voltage, expected_recipe_id


def _normalize_array_metadata(
    metadata: dict[str, Any], array: np.ndarray, checksum: str
) -> None:
    actual = {"shape": list(array.shape), "dtype": "float32", "sha256": checksum}
    recorded = metadata.get("array")
    if recorded is not None:
        if not isinstance(recorded, Mapping):
            raise ValueError("array metadata must be an object")
        if recorded.get("shape") != actual["shape"]:
            raise ValueError("recorded array shape disagrees with intensity payload")
        if recorded.get("dtype") != actual["dtype"]:
            raise ValueError("recorded array dtype disagrees with canonical float32 payload")
        if recorded.get("sha256") != actual["sha256"]:
            raise ValueError("recorded array checksum disagrees with intensity payload")
    metadata["array"] = actual


@dataclass(frozen=True, init=False, eq=False)
class MasterPatternProduct:
    intensity: np.ndarray
    metadata: Mapping[str, Any]
    array_sha256: str
    product_id: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("MasterPatternProduct must be created with from_array()")

    @classmethod
    def from_array(cls, intensity: Any, *, metadata: Mapping[str, Any]) -> MasterPatternProduct:
        array = _owned_float32(intensity, ndim=3)
        if array.shape[0] != 2 or array.shape[1] < 1 or array.shape[2] < 1:
            raise ValueError("master intensity shape must be (2, y, x) for north and south")
        plain = plain_data(metadata)
        _validate_phase(plain)
        source_id = _validate_source(plain)
        _validate_generator(plain)
        voltage, recipe_id = _validate_simulation(plain)
        for key in ("projection", "intensity_units", "coordinate_frame"):
            _required_text(plain, key)
        if plain.get("hemisphere_order") != ["north", "south"]:
            raise ValueError("metadata hemisphere_order must be ['north', 'south']")
        links = plain.get("provenance_links")
        if not isinstance(links, list) or not links or any(
            not isinstance(link, str) or not link for link in links
        ):
            raise ValueError("metadata provenance_links must contain non-empty strings")
        if recipe_id not in links:
            raise ValueError("recipe must appear in metadata provenance_links")
        if source_id not in links:
            raise ValueError("source must appear in metadata provenance_links")
        energy = _canonical_real(plain.get("energy_kev"), "energy_kev")
        if energy <= 0:
            raise ValueError("energy_kev must be finite and positive")
        if not math.isclose(voltage, energy, rel_tol=1e-9, abs_tol=0.0):
            raise ValueError("energy_kev is inconsistent with simulation voltage_kv")
        checksum = _array_sha256(array)
        _normalize_array_metadata(plain, array, checksum)
        product_id = stable_id("master", {"metadata": plain, "array_sha256": checksum})
        product = object.__new__(cls)
        object.__setattr__(product, "intensity", array)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "array_sha256", checksum)
        object.__setattr__(product, "product_id", product_id)
        return product

    def metadata_dict(self) -> dict[str, Any]:
        return _thaw(self.metadata)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MasterPatternProduct):
            return NotImplemented
        return (self.product_id, self.array_sha256) == (other.product_id, other.array_sha256)

    def __hash__(self) -> int:
        return hash((self.product_id, self.array_sha256))


@dataclass(frozen=True, init=False, eq=False)
class DetectorPatternProduct:
    intensity: np.ndarray
    master_product_id: str
    projection_recipe_id: str
    metadata: Mapping[str, Any]
    array_sha256: str
    product_id: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("DetectorPatternProduct must be created with from_array()")

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
        energy = _canonical_real(plain.get("energy_kev"), "energy_kev")
        if energy <= 0:
            raise ValueError("energy_kev must be finite and positive")
        checksum = _array_sha256(array)
        _normalize_array_metadata(plain, array, checksum)
        identity_payload = {
            "metadata": plain,
            "array_sha256": checksum,
            "master_product_id": master_product_id,
            "projection_recipe_id": projection_recipe_id,
        }
        product = object.__new__(cls)
        object.__setattr__(product, "intensity", array)
        object.__setattr__(product, "master_product_id", master_product_id)
        object.__setattr__(product, "projection_recipe_id", projection_recipe_id)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "array_sha256", checksum)
        object.__setattr__(product, "product_id", stable_id("detector", identity_payload))
        return product

    def metadata_dict(self) -> dict[str, Any]:
        return _thaw(self.metadata)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DetectorPatternProduct):
            return NotImplemented
        return (self.product_id, self.array_sha256) == (other.product_id, other.array_sha256)

    def __hash__(self) -> int:
        return hash((self.product_id, self.array_sha256))

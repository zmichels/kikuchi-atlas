"""Plain, immutable products for bounded kinematical master simulations."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.model.recipes import Orientation


def _freeze(value: Any) -> Any:
    value = plain_data(value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class KinematicalRecipe:
    """The small public recipe for a source master, not a presentation product."""

    schema_version: int
    name: str
    source_record: str
    reflector_recipe: str
    energy_kev: float
    orientation: Orientation
    zone_axis_uvw: tuple[int, int, int]
    half_size: int
    hemisphere: str
    scaling: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_record": self.source_record,
            "reflector_recipe": self.reflector_recipe,
            "energy_kev": self.energy_kev,
            "orientation": {
                **self.orientation.to_dict(),
                "zone_axis_uvw": list(self.zone_axis_uvw),
            },
            "master": {
                "half_size": self.half_size,
                "hemisphere": self.hemisphere,
                "scaling": self.scaling,
            },
        }

    @property
    def recipe_id(self) -> str:
        payload = self.to_dict()
        del payload["source_record"]
        del payload["reflector_recipe"]
        return stable_id("kinematical-recipe", payload)


@dataclass(frozen=True, init=False, eq=False)
class KinematicalArrayProduct:
    """An owned finite array whose metadata contains only project data."""

    label: str
    intensity: np.ndarray
    metadata: Mapping[str, Any]
    array_sha256: str
    product_id: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("KinematicalArrayProduct must be created with from_array()")

    @classmethod
    def from_array(
        cls, label: str, intensity: Any, *, metadata: Mapping[str, Any]
    ) -> KinematicalArrayProduct:
        array = np.asarray(intensity, dtype=np.float32, order="C")
        if array.ndim != 3 or array.shape[0] != 2 or not array.size or not np.isfinite(array).all():
            raise ValueError("kinematical master must be finite, non-empty, and shaped (2, y, x)")
        owned = np.frombuffer(array.tobytes(order="C"), dtype=np.float32).reshape(array.shape)
        checksum = hashlib.sha256(owned.tobytes(order="C")).hexdigest()
        plain = plain_data(metadata)
        product = object.__new__(cls)
        object.__setattr__(product, "label", label)
        object.__setattr__(product, "intensity", owned)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "array_sha256", checksum)
        object.__setattr__(
            product,
            "product_id",
            stable_id("kinematical", {"label": label, "metadata": plain, "array_sha256": checksum}),
        )
        return product


@dataclass(frozen=True)
class KinematicalSimulation:
    """The bounded scientific source product and its public evidence ledger."""

    master_stereographic: KinematicalArrayProduct
    reflector_catalog: Mapping[str, Any]
    projection_ledger: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "reflector_catalog", _freeze(self.reflector_catalog))
        object.__setattr__(self, "projection_ledger", _freeze(self.projection_ledger))

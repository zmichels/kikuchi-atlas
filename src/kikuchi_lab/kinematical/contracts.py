"""Immutable project-owned products for kinematical reference simulations."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType

import numpy as np

from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.model.recipes import DetectorRecipe, Orientation


def _freeze(value: object) -> object:
    plain = plain_data(value)
    if isinstance(plain, dict):
        return MappingProxyType({key: _freeze(item) for key, item in plain.items()})
    if isinstance(plain, list):
        return tuple(_freeze(item) for item in plain)
    return plain


@dataclass(frozen=True)
class EtchedMasterStyle:
    name: str
    overlay_relative_factor: float
    line_alpha: float
    line_width_pt: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class KinematicalRecipe:
    schema_version: int
    name: str
    source_record: str
    energy_kev: float
    orientation: Orientation
    zone_axis_uvw: tuple[int, int, int]
    detector: DetectorRecipe
    min_dspacing_angstrom: float
    scattering_params: str
    master_relative_factor: float
    half_size: int
    hemisphere: str
    master_scaling: str
    tone_percentiles: tuple[float, float]
    tone_asinh_scale: float
    figure_size_px: int
    promoted_style: str
    styles: tuple[EtchedMasterStyle, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_record": self.source_record,
            "energy_kev": self.energy_kev,
            "orientation": self.orientation.to_dict(),
            "zone_axis_uvw": list(self.zone_axis_uvw),
            "detector": self.detector.to_dict(),
            "reflections": {
                "min_dspacing_angstrom": self.min_dspacing_angstrom,
                "scattering_params": self.scattering_params,
                "master_relative_factor": self.master_relative_factor,
            },
            "master": {
                "half_size": self.half_size,
                "hemisphere": self.hemisphere,
                "scaling": self.master_scaling,
            },
            "tone": {
                "percentiles": list(self.tone_percentiles),
                "asinh_scale": self.tone_asinh_scale,
            },
            "figure_size_px": self.figure_size_px,
            "promoted_style": self.promoted_style,
            "styles": [style.to_dict() for style in self.styles],
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())


@dataclass(frozen=True, init=False, eq=False)
class KinematicalArrayProduct:
    label: str
    intensity: np.ndarray
    metadata: Mapping[str, object]
    array_sha256: str
    product_id: str

    @classmethod
    def from_array(
        cls, label: str, intensity: object, *, metadata: Mapping[str, object]
    ) -> KinematicalArrayProduct:
        array = np.ascontiguousarray(np.asarray(intensity, dtype=np.float32))
        if array.ndim not in (2, 3) or not array.size or not np.isfinite(array).all():
            raise ValueError("kinematical intensity must be finite, non-empty, and 2D or 3D")
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
            stable_id(
                "kinematical", {"label": label, "metadata": plain, "array_sha256": checksum}
            ),
        )
        return product


@dataclass(frozen=True)
class KinematicalSimulation:
    master_stereographic: KinematicalArrayProduct
    master_lambert: KinematicalArrayProduct
    detector: KinematicalArrayProduct
    reflector_catalog: tuple[Mapping[str, object], ...]
    projection_ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "reflector_catalog", _freeze(self.reflector_catalog))
        object.__setattr__(self, "projection_ledger", _freeze(self.projection_ledger))

    def products(self) -> dict[str, KinematicalArrayProduct]:
        return {
            "master-stereographic": self.master_stereographic,
            "master-lambert": self.master_lambert,
            "detector": self.detector,
        }


@dataclass(frozen=True)
class KinematicalExecution:
    simulation: KinematicalSimulation
    figures: Mapping[str, bytes]

    def __post_init__(self) -> None:
        if not isinstance(self.figures, Mapping):
            raise TypeError("kinematical figures must be a mapping")
        frozen: dict[str, bytes] = {}
        for name, payload in self.figures.items():
            if not isinstance(name, str) or not name:
                raise ValueError("kinematical figure names must be non-empty strings")
            if not isinstance(payload, bytes):
                raise TypeError("kinematical figure payloads must be bytes")
            frozen[name] = payload
        object.__setattr__(self, "figures", MappingProxyType(frozen))

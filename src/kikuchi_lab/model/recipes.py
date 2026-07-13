"""Frozen, source-neutral simulation and rendering recipes."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .identity import plain_data, stable_id


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _freeze(value: Any) -> Any:
    value = plain_data(value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class SimulationRecipe:
    voltage_kv: float
    halfw: int
    dmin_nm: float
    energy_binwidth_kev: float
    n_trajectories: int
    sigma_deg: float
    omega_deg: float
    rank: int
    chunk_size: int
    marginal_coverage: float
    relative_image_stop: float
    mc_backend: str
    bethe_c_strong: float
    bethe_c_weak: float
    bethe_c_cutoff: float
    dbdiff_sg_cutoff: float
    mc_auto_stop: bool
    mc_relative_tol: float
    mc_min_trajectories: int
    mc_max_trajectories: int
    exact_slow_cpu: bool

    def __post_init__(self) -> None:
        for name in (
            "voltage_kv",
            "dmin_nm",
            "energy_binwidth_kev",
            "sigma_deg",
            "omega_deg",
            "marginal_coverage",
            "relative_image_stop",
            "bethe_c_strong",
            "bethe_c_weak",
            "bethe_c_cutoff",
            "dbdiff_sg_cutoff",
            "mc_relative_tol",
        ):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        for name in (
            "halfw",
            "n_trajectories",
            "rank",
            "chunk_size",
            "mc_min_trajectories",
            "mc_max_trajectories",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) != value or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
            object.__setattr__(self, name, int(value))
        if self.voltage_kv <= 0 or self.dmin_nm <= 0 or self.energy_binwidth_kev <= 0:
            raise ValueError("voltage, dmin, and energy bin width must be positive")
        if self.mc_backend not in {"gpu", "surrogate"}:
            raise ValueError("mc_backend must be 'gpu' or 'surrogate'")
        if not 0 < self.marginal_coverage <= 1:
            raise ValueError("marginal_coverage must be in (0, 1]")
        if self.relative_image_stop <= 0 or self.mc_relative_tol <= 0:
            raise ValueError("relative stopping tolerances must be positive")
        if self.mc_min_trajectories > self.mc_max_trajectories:
            raise ValueError("mc_min_trajectories cannot exceed mc_max_trajectories")

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())


@dataclass(frozen=True)
class Orientation:
    euler_bunge_deg: tuple[float, float, float]
    frame: str = "crystal_to_sample"

    def __post_init__(self) -> None:
        eulers = tuple(_finite("Euler angle", value) for value in self.euler_bunge_deg)
        if len(eulers) != 3:
            raise ValueError("euler_bunge_deg must contain exactly three angles")
        if self.frame != "crystal_to_sample":
            raise ValueError("orientation frame must be 'crystal_to_sample'")
        object.__setattr__(self, "euler_bunge_deg", eulers)

    def to_dict(self) -> dict[str, object]:
        return {
            "euler_bunge_deg": list(self.euler_bunge_deg),
            "angle_units": "degree",
            "frame": self.frame,
        }

    @property
    def orientation_id(self) -> str:
        return stable_id("orientation", self.to_dict())


@dataclass(frozen=True)
class DetectorRecipe:
    shape: tuple[int, int]
    pcx: float
    pcy: float
    pcz: float
    pc_convention: str
    sample_tilt_deg: float
    detector_tilt_deg: float
    detector_azimuth_deg: float
    detector_twist_deg: float
    pixel_size_um: float
    binning: int
    supersampling: int

    def __post_init__(self) -> None:
        shape = tuple(self.shape)
        if len(shape) != 2 or any(isinstance(v, bool) or int(v) != v or v <= 0 for v in shape):
            raise ValueError("shape must contain two positive integer dimensions")
        object.__setattr__(self, "shape", (int(shape[0]), int(shape[1])))
        for name in (
            "pcx",
            "pcy",
            "pcz",
            "sample_tilt_deg",
            "detector_tilt_deg",
            "detector_azimuth_deg",
            "detector_twist_deg",
            "pixel_size_um",
        ):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        # EMsoft PCs include pixel-valued coordinates in some conventions and
        # therefore require a unit-aware conversion boundary of their own.
        if self.pc_convention not in {"bruker", "tsl", "oxford"}:
            raise ValueError("unsupported projection-center convention")
        if not 0 <= self.pcx <= 1:
            raise ValueError("pcx must be a dimensionless fraction in [0, 1]")
        if not 0 <= self.pcy <= 1:
            raise ValueError("pcy must be a dimensionless fraction in [0, 1]")
        if self.pcz <= 0:
            raise ValueError("pcz must be a positive dimensionless fraction")
        if self.pixel_size_um <= 0:
            raise ValueError("pixel_size_um must be positive")
        for name in ("binning", "supersampling"):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) != value or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
            object.__setattr__(self, name, int(value))

    @property
    def supersampled_shape(self) -> tuple[int, int]:
        return tuple(dimension * self.supersampling for dimension in self.shape)

    @property
    def effective_pixel_size_um(self) -> float:
        return self.pixel_size_um * self.binning / self.supersampling

    @property
    def physical_extent_um(self) -> tuple[float, float]:
        return tuple(dimension * self.pixel_size_um * self.binning for dimension in self.shape)

    def to_dict(self) -> dict[str, Any]:
        return {
            "shape": list(self.shape),
            "supersampled_shape": list(self.supersampled_shape),
            "pc": {
                "x": self.pcx,
                "y": self.pcy,
                "z": self.pcz,
                "convention": self.pc_convention,
                "units": "fraction",
            },
            "sample_tilt_deg": self.sample_tilt_deg,
            "detector_tilt_deg": self.detector_tilt_deg,
            "detector_azimuth_deg": self.detector_azimuth_deg,
            "detector_twist_deg": self.detector_twist_deg,
            "angle_units": "degree",
            "pixel_size_um": self.pixel_size_um,
            "effective_pixel_size_um": self.effective_pixel_size_um,
            "physical_extent_um": list(self.physical_extent_um),
            "binning": self.binning,
            "supersampling": self.supersampling,
        }

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())


@dataclass(frozen=True)
class ProcessingStage:
    name: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("processing stage name is required")
        object.__setattr__(self, "parameters", _freeze(self.parameters))

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "parameters": _plain(self.parameters)}


@dataclass(frozen=True)
class ProcessingRecipe:
    stages: tuple[ProcessingStage, ...]

    def __post_init__(self) -> None:
        stages = tuple(self.stages)
        if any(not isinstance(stage, ProcessingStage) for stage in stages):
            raise TypeError("stages must contain ProcessingStage objects")
        object.__setattr__(self, "stages", stages)

    def to_dict(self) -> dict[str, object]:
        return {"stages": [stage.to_dict() for stage in self.stages]}

    @property
    def recipe_id(self) -> str:
        return stable_id("recipe", self.to_dict())

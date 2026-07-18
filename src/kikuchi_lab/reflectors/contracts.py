"""Immutable, phase-neutral reflection evidence contracts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np

from kikuchi_lab.model.identity import plain_data, stable_id

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _finite_positive(name: str, value: object, *, zero_allowed: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or (number < 0.0 if zero_allowed else number <= 0.0):
        qualifier = "nonnegative" if zero_allowed else "positive"
        raise ValueError(f"{name} must be a finite {qualifier} number")
    return number


def _frozen_plain(value: Any) -> Any:
    converted = plain_data(value)
    if isinstance(converted, dict):
        return MappingProxyType({key: _frozen_plain(item) for key, item in converted.items()})
    if isinstance(converted, list):
        return tuple(_frozen_plain(item) for item in converted)
    return converted


def _plain_frozen(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_frozen(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_frozen(item) for item in value]
    return value


@dataclass(frozen=True)
class ReflectorMember:
    """One axial reflection family expressed in the crystal frame."""

    hkl: tuple[int, int, int]
    normal_crystal: np.ndarray
    dspacing_angstrom: float
    bragg_half_width_rad: float
    structure_factor_abs: float
    normalized_weight: float
    member_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.hkl, tuple)
            or len(self.hkl) != 3
            or any(isinstance(value, bool) or not isinstance(value, int) for value in self.hkl)
        ):
            raise ValueError("hkl must be a tuple of three integers")
        normal = np.array(self.normal_crystal, dtype="<f8", copy=True)
        if normal.shape != (3,) or not np.isfinite(normal).all():
            raise ValueError("normal_crystal must be a finite three-vector")
        if not math.isclose(float(np.linalg.vector_norm(normal)), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("normal_crystal must be a unit normal")
        # A NumPy-owned array merely marked read-only can be made writable again
        # by a caller.  Rebuild it over immutable bytes so the public normal has
        # an immutable backing buffer as well as a read-only flag.
        normal = np.frombuffer(normal.astype("<f8", copy=False).tobytes(), dtype="<f8")
        object.__setattr__(self, "normal_crystal", normal)
        object.__setattr__(self, "dspacing_angstrom", _finite_positive("dspacing_angstrom", self.dspacing_angstrom))
        object.__setattr__(
            self,
            "bragg_half_width_rad",
            _finite_positive("bragg_half_width_rad", self.bragg_half_width_rad),
        )
        object.__setattr__(
            self,
            "structure_factor_abs",
            _finite_positive("structure_factor_abs", self.structure_factor_abs, zero_allowed=True),
        )
        weight = _finite_positive("normalized_weight", self.normalized_weight, zero_allowed=True)
        if weight > 1.0:
            raise ValueError("normalized_weight must be in [0, 1]")
        object.__setattr__(self, "normalized_weight", weight)
        object.__setattr__(
            self,
            "member_id",
            stable_id(
                "reflector-member",
                {
                    "hkl": list(self.hkl),
                    "normal_crystal": normal.tolist(),
                    "dspacing_angstrom": self.dspacing_angstrom,
                    "bragg_half_width_rad": self.bragg_half_width_rad,
                    "structure_factor_abs": self.structure_factor_abs,
                    "normalized_weight": self.normalized_weight,
                },
            ),
        )


@dataclass(frozen=True)
class ReflectorCatalog:
    """Content-addressed reflector evidence for one structure and energy."""

    source_structure_id: str
    source_structure_sha256: str
    energy_kev: float
    reflection_recipe_id: str
    selection: Mapping[str, Any]
    members: tuple[ReflectorMember, ...]
    catalog_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source_structure_id, str) or not self.source_structure_id.strip():
            raise ValueError("source_structure_id must be non-empty text")
        if not isinstance(self.source_structure_sha256, str) or not _SHA256.fullmatch(
            self.source_structure_sha256
        ):
            raise ValueError("source_structure_sha256 must be a lowercase SHA-256 string")
        object.__setattr__(self, "energy_kev", _finite_positive("energy_kev", self.energy_kev))
        if not isinstance(self.reflection_recipe_id, str) or not self.reflection_recipe_id.strip():
            raise ValueError("reflection_recipe_id must be non-empty text")
        if not isinstance(self.selection, Mapping):
            raise ValueError("selection must be a mapping")
        selection = _frozen_plain(self.selection)
        object.__setattr__(self, "selection", selection)
        members = tuple(self.members)
        if not all(isinstance(member, ReflectorMember) for member in members):
            raise ValueError("members must contain ReflectorMember values")
        object.__setattr__(self, "members", members)
        object.__setattr__(
            self,
            "catalog_id",
            stable_id(
                "reflector-catalog",
                {
                    "source_structure_id": self.source_structure_id,
                    "source_structure_sha256": self.source_structure_sha256,
                    "energy_kev": self.energy_kev,
                    "reflection_recipe_id": self.reflection_recipe_id,
                    "selection": _plain_frozen(selection),
                    "member_ids": [member.member_id for member in members],
                },
            ),
        )

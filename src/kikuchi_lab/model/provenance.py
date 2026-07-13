"""Project-owned scientific provenance records."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from numbers import Real

from .identity import stable_id

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourceRecord:
    uri: str
    sha256: str
    license: str
    citation: str

    def __post_init__(self) -> None:
        if not self.uri or not self.license or not self.citation:
            raise ValueError("source URI, license, and citation are required")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("source sha256 must be a lowercase 64-character SHA-256")

    def to_dict(self) -> dict[str, str]:
        return {
            "uri": self.uri,
            "sha256": self.sha256,
            "license": self.license,
            "citation": self.citation,
        }

    @property
    def source_id(self) -> str:
        return stable_id("source", self.to_dict())


@dataclass(frozen=True)
class PhaseRecord:
    name: str
    formula: str
    space_group_number: int
    setting: str
    lattice_angstrom: tuple[float, float, float, float, float, float]

    def __post_init__(self) -> None:
        for field in ("name", "formula", "setting"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"phase {field} must be a non-blank string")
        if isinstance(self.space_group_number, bool) or not isinstance(
            self.space_group_number, int
        ):
            raise ValueError("space_group_number must be an integer")
        raw_lattice = tuple(self.lattice_angstrom)
        if len(raw_lattice) != 6 or any(
            isinstance(value, bool) or not isinstance(value, Real) for value in raw_lattice
        ):
            raise ValueError("lattice_angstrom must contain six numeric values")
        lattice = tuple(float(value) for value in raw_lattice)
        object.__setattr__(self, "lattice_angstrom", lattice)
        if not 1 <= self.space_group_number <= 230:
            raise ValueError("space_group_number must be in [1, 230]")
        if any(not math.isfinite(value) for value in lattice):
            raise ValueError("lattice_angstrom values must be finite")
        if any(value <= 0 for value in lattice[:3]):
            raise ValueError("lattice_angstrom must contain three positive lengths and three angles")
        if any(not 0 < angle <= 180 for angle in lattice[3:]):
            raise ValueError("lattice angles must be in (0, 180]")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "formula": self.formula,
            "space_group": {"number": self.space_group_number, "setting": self.setting},
            "lattice": {"values": list(self.lattice_angstrom), "units": "angstrom"},
        }

    @property
    def phase_id(self) -> str:
        return stable_id("phase", self.to_dict())

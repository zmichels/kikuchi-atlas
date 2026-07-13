"""Load bounded orientation sets and reduce them by crystal symmetry."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from orix.quaternion import Orientation as OrixOrientation
from orix.quaternion import Rotation, symmetry

from kikuchi_lab.model import Orientation, stable_id

_CANDIDATE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
_SUPPORTED_POINT_GROUP = "mmm"
SUPPORTED_ORIENTATION_CONVENTION = (
    "active crystal-to-sample Bunge ZXZ Euler angles in degrees; "
    "sample axes are EDAX-TSL [RD, TD, ND]"
)
SUPPORTED_PHI1_SEMANTICS = (
    "bunge_phi1_deg is the explicit first Bunge Euler angle; it is a reproducible "
    "in-plane composition choice, not an absolute roll measured from a zone-axis "
    "alignment reference"
)


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value


def _finite_real(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite real number")
    return result


def _real_sequence(value: Any, field: str, *, length: int) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{field} must be a {length}-value YAML sequence")
    return tuple(_finite_real(item, field) for item in value)


def _integer_sequence(value: Any, field: str, *, length: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{field} must be a {length}-integer YAML sequence")
    if any(type(item) is not int for item in value):
        raise ValueError(f"{field} must contain finite integer indices")
    return tuple(value)


def _zone_axis_label(uvw: tuple[int, int, int]) -> str:
    return "[" + "".join(str(index) for index in uvw) + "]"


@dataclass(frozen=True)
class OrientationCandidate:
    """One explicit, reviewable orientation in a bounded comparison set."""

    candidate_id: str
    name: str
    orientation: Orientation
    bunge_phi1_deg: float
    zone_axis_uvw: tuple[int, int, int]
    zone_axis_intent: str
    composition_intent: str

    def __post_init__(self) -> None:
        if not _CANDIDATE_ID.fullmatch(self.candidate_id):
            raise ValueError("candidate_id must be a stable lowercase hyphenated identifier")
        _required_text(self.name, "candidate name")
        phi1, phi, phi2 = self.orientation.euler_bunge_deg
        if not (0 <= phi1 < 360 and 0 <= phi <= 180 and 0 <= phi2 < 360):
            raise ValueError(
                "candidate Euler angles must use canonical Bunge ranges "
                "[0, 360), [0, 180], [0, 360) degrees"
            )
        declared_phi1 = _finite_real(self.bunge_phi1_deg, "bunge_phi1_deg")
        if declared_phi1 != phi1:
            raise ValueError("bunge_phi1_deg must exactly match the first Bunge Euler angle")
        object.__setattr__(self, "bunge_phi1_deg", declared_phi1)
        if not isinstance(self.zone_axis_uvw, (list, tuple)) or len(self.zone_axis_uvw) != 3:
            raise ValueError("zone_axis_uvw must contain three integer direct-lattice indices")
        if any(type(index) is not int for index in self.zone_axis_uvw):
            raise ValueError("zone_axis_uvw must contain finite integer direct-lattice indices")
        uvw = tuple(self.zone_axis_uvw)
        if not any(uvw):
            raise ValueError("zone_axis_uvw cannot be [000]")
        object.__setattr__(self, "zone_axis_uvw", uvw)
        _required_text(self.zone_axis_intent, "zone_axis_intent")
        _required_text(self.composition_intent, "composition_intent")

    @property
    def zone_axis_label(self) -> str:
        return _zone_axis_label(self.zone_axis_uvw)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "id": self.candidate_id,
            "name": self.name,
            "orientation": self.orientation.to_dict(),
            "bunge_phi1_deg": self.bunge_phi1_deg,
            "zone_axis_uvw": list(self.zone_axis_uvw),
            "zone_axis_intent": self.zone_axis_intent,
            "composition_intent": self.composition_intent,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "zone_axis_label": self.zone_axis_label}


@dataclass(frozen=True)
class OrientationCandidateSet:
    """Source-neutral candidate collection with content-derived identity."""

    schema_version: int
    phase: str
    space_group: str
    point_group: str
    orientation_convention: str
    phi1_semantics: str
    equivalence_tolerance_deg: float
    generation_rationale: str
    exhaustive: bool
    lattice_abc_angstrom: tuple[float, float, float]
    candidates: tuple[OrientationCandidate, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("schema_version must be integer 1")
        for name in ("phase", "space_group", "orientation_convention", "generation_rationale"):
            _required_text(getattr(self, name), name)
        if self.point_group != _SUPPORTED_POINT_GROUP:
            raise ValueError("candidate reduction currently supports point group 'mmm'")
        if self.orientation_convention != SUPPORTED_ORIENTATION_CONVENTION:
            raise ValueError(
                "orientation_convention must exactly match the supported active "
                "crystal-to-sample Bunge-degree convention"
            )
        if self.phi1_semantics != SUPPORTED_PHI1_SEMANTICS:
            raise ValueError("phi1_semantics must exactly match the supported Bunge phi1 meaning")
        if type(self.exhaustive) is not bool or self.exhaustive:
            raise ValueError("schema v1 bounded proof-set exhaustive must be false")
        if not isinstance(self.lattice_abc_angstrom, (list, tuple)) or len(
            self.lattice_abc_angstrom
        ) != 3:
            raise ValueError("lattice_abc_angstrom must contain three finite positive lengths")
        lattice = tuple(
            _finite_real(value, "lattice_abc_angstrom")
            for value in self.lattice_abc_angstrom
        )
        if any(value <= 0 for value in lattice):
            raise ValueError("lattice_abc_angstrom must contain three finite positive lengths")
        object.__setattr__(self, "lattice_abc_angstrom", lattice)
        tolerance = _finite_real(
            self.equivalence_tolerance_deg, "equivalence_tolerance_deg"
        )
        if tolerance <= 0:
            raise ValueError("equivalence_tolerance_deg must be finite and positive")
        object.__setattr__(self, "equivalence_tolerance_deg", tolerance)
        if not isinstance(self.candidates, (list, tuple)):
            raise ValueError("candidates must be a sequence of OrientationCandidate values")
        candidates = tuple(self.candidates)
        if any(not isinstance(candidate, OrientationCandidate) for candidate in candidates):
            raise ValueError("candidates must contain OrientationCandidate values")
        object.__setattr__(self, "candidates", candidates)
        if not 9 <= len(candidates) <= 12:
            raise ValueError("a proof candidate set must contain 9-12 orientations")
        ids = [candidate.candidate_id for candidate in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique")

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(candidate.candidate_id for candidate in self.candidates)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "space_group": self.space_group,
            "point_group": self.point_group,
            "orientation_convention": self.orientation_convention,
            "phi1_semantics": self.phi1_semantics,
            "equivalence_tolerance_deg": self.equivalence_tolerance_deg,
            "generation_rationale": self.generation_rationale,
            "exhaustive": self.exhaustive,
            "lattice_abc_angstrom": list(self.lattice_abc_angstrom),
            "candidates": [candidate.identity_payload() for candidate in self.candidates],
        }

    @property
    def candidate_set_id(self) -> str:
        return stable_id("candidate-set", self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        serialized = self.identity_payload()
        serialized["candidates"] = [candidate.to_dict() for candidate in self.candidates]
        return {"candidate_set_id": self.candidate_set_id, **serialized}


@dataclass(frozen=True)
class CandidateDisorientation:
    candidate_a_id: str
    candidate_b_id: str
    distance_deg: float


def _crystal_orientation(orientation: Orientation) -> OrixOrientation:
    """Convert the public active contract to orix's passive crystal orientation.

    Orix applies the supplied symmetry on the left of its passive
    sample-to-crystal orientation. This reduces crystal ``mmm`` while leaving
    the sample reference frame fixed.
    """
    active = Rotation.from_euler(
        orientation.euler_bunge_deg,
        degrees=True,
        direction="crystal2lab",
    )
    return OrixOrientation(~active, symmetry=symmetry.D2h)


def crystal_disorientation_deg(
    first: Orientation,
    second: Orientation,
    *,
    point_group: str = _SUPPORTED_POINT_GROUP,
) -> float:
    """Return minimum disorientation under crystal ``mmm`` symmetry in degrees."""
    if point_group != _SUPPORTED_POINT_GROUP:
        raise ValueError("candidate reduction currently supports point group 'mmm'")
    angle = _crystal_orientation(first).angle_with(_crystal_orientation(second), degrees=True)
    return float(angle[0])


def pairwise_crystal_disorientation_deg(
    candidate_set: OrientationCandidateSet,
) -> tuple[CandidateDisorientation, ...]:
    """Return deterministic upper-triangle crystal disorientations."""
    distances: list[CandidateDisorientation] = []
    for index, first in enumerate(candidate_set.candidates):
        for second in candidate_set.candidates[index + 1 :]:
            distances.append(
                CandidateDisorientation(
                    candidate_a_id=first.candidate_id,
                    candidate_b_id=second.candidate_id,
                    distance_deg=crystal_disorientation_deg(
                        first.orientation,
                        second.orientation,
                        point_group=candidate_set.point_group,
                    ),
                )
            )
    return tuple(distances)


def zone_axis_sample_misalignment_deg(
    candidate: OrientationCandidate,
    *,
    lattice_abc_angstrom: tuple[float, float, float],
) -> float:
    """Return the angle between a metric-aware zone direction and sample ND."""
    lattice = np.asarray(lattice_abc_angstrom, dtype=float)
    if lattice.shape != (3,) or not np.isfinite(lattice).all() or np.any(lattice <= 0):
        raise ValueError("lattice_abc_angstrom must contain three finite positive lengths")
    crystal_direction = np.asarray(candidate.zone_axis_uvw, dtype=float) * lattice
    crystal_direction /= np.linalg.norm(crystal_direction)
    active = Rotation.from_euler(
        candidate.orientation.euler_bunge_deg,
        degrees=True,
        direction="crystal2lab",
    )
    sample_direction = active.to_matrix()[0] @ crystal_direction
    cosine = float(np.clip(sample_direction[2] / np.linalg.norm(sample_direction), -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def _candidate_from_data(data: Mapping[str, Any]) -> OrientationCandidate:
    if not isinstance(data, Mapping):
        raise ValueError("candidate entry must be a mapping")
    eulers = _real_sequence(data.get("euler_bunge_deg"), "euler_bunge_deg", length=3)
    uvw = _integer_sequence(data.get("zone_axis_uvw"), "zone_axis_uvw", length=3)
    return OrientationCandidate(
        candidate_id=_required_text(data.get("id"), "candidate id"),
        name=_required_text(data.get("name"), "candidate name"),
        orientation=Orientation(eulers),
        bunge_phi1_deg=data.get("bunge_phi1_deg"),
        zone_axis_uvw=uvw,
        zone_axis_intent=_required_text(data.get("zone_axis_intent"), "zone_axis_intent"),
        composition_intent=_required_text(data.get("composition_intent"), "composition_intent"),
    )


def load_candidate_set(path: str | Path) -> OrientationCandidateSet:
    """Load and validate an explicit YAML orientation candidate recipe."""
    with Path(path).open(encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream)
    if not isinstance(loaded, Mapping):
        raise ValueError("candidate recipe must contain a YAML mapping")
    data = loaded
    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("candidate recipe requires a candidates list")
    candidate_set = OrientationCandidateSet(
        schema_version=data.get("schema_version"),
        phase=_required_text(data.get("phase"), "phase"),
        space_group=_required_text(data.get("space_group"), "space_group"),
        point_group=_required_text(data.get("point_group"), "point_group"),
        orientation_convention=_required_text(
            data.get("orientation_convention"), "orientation_convention"
        ),
        phi1_semantics=_required_text(data.get("phi1_semantics"), "phi1_semantics"),
        equivalence_tolerance_deg=data.get("equivalence_tolerance_deg"),
        generation_rationale=_required_text(
            data.get("generation_rationale"), "generation_rationale"
        ),
        exhaustive=data.get("exhaustive"),
        lattice_abc_angstrom=_real_sequence(
            data.get("lattice_abc_angstrom"), "lattice_abc_angstrom", length=3
        ),
        candidates=tuple(_candidate_from_data(candidate) for candidate in raw_candidates),
    )
    minimum = min(
        distance.distance_deg for distance in pairwise_crystal_disorientation_deg(candidate_set)
    )
    if minimum <= candidate_set.equivalence_tolerance_deg:
        raise ValueError(
            "candidate recipe contains crystal-symmetry equivalents within "
            f"{candidate_set.equivalence_tolerance_deg} degrees"
        )
    return candidate_set

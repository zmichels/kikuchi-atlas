"""Strict recipes and immutable evidence for direct reflector calculations."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from types import MappingProxyType

import numpy as np
import yaml

from kikuchi_lab.model.identity import plain_data, stable_id


_TOP_LEVEL_FIELDS = {
    "schema_version",
    "name",
    "source_record",
    "energy_kev",
    "reflections",
    "art_weight",
}
_REFLECTION_FIELDS = {
    "min_dspacing_angstrom",
    "scattering_params",
    "candidate_relative_factor",
}
_ART_WEIGHT_FIELDS = {"exponent", "eligibility_min_weight"}
_FIRST_SERIES_VALUES = {
    "energy_kev": 20.0,
    "min_dspacing_angstrom": 0.7,
    "candidate_relative_factor": 0.03,
    "weight_exponent": 2.0,
    "eligibility_min_weight": 0.08,
}
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PHASE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_AXIAL_TOLERANCE = 1e-8


class _FrozenList(tuple):
    """Immutable plain-data sequence that retains list-style value equality."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence) or isinstance(other, (str, bytes, bytearray)):
            return False
        return tuple(self) == tuple(other)

    __hash__ = tuple.__hash__


def _freeze_plain(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_plain(item) for key, item in value.items()})
    if isinstance(value, list):
        return _FrozenList(_freeze_plain(item) for item in value)
    return value


def _mapping(value: object, field: str, expected: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"direct reflector recipe {field} fields differ from the schema")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"direct reflector recipe {field} must be non-empty text")
    return value


def _source_record(value: object) -> str:
    result = _text(value, "source_record")
    path = PurePosixPath(result)
    parts = path.parts
    if (
        Path(result).is_absolute()
        or re.match(r"^[A-Za-z]:[\\/]", result)
        or result.startswith("\\\\")
        or "\\" in result
        or len(parts) != 5
        or parts[:3] != ("..", "..", "phases")
        or not _PHASE_SLUG.fullmatch(parts[3])
        or parts[4] != "source.yml"
    ):
        raise ValueError(
            "direct reflector recipe source_record must remain under ../../phases"
        )
    return result


def _exact_real(value: object, field: str, expected: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"direct reflector recipe {field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"direct reflector recipe {field} must be finite")
    if result != expected:
        raise ValueError(f"direct reflector recipe {field} must be exactly {expected}")
    return result


def _positive_real(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{field} must be positive and finite")
    return result


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"direct reflector evidence {field} must be non-empty text")
    return value


def _owned_float_array(value: object, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype.kind == "b":
        raise ValueError(f"direct reflector evidence {field} must contain numbers")
    try:
        contiguous = np.ascontiguousarray(np.asarray(value, dtype=np.dtype("<f8")))
    except (TypeError, ValueError):
        raise ValueError(
            f"direct reflector evidence {field} must contain numbers"
        ) from None
    return np.frombuffer(
        contiguous.tobytes(order="C"), dtype=np.dtype("<f8")
    ).reshape(contiguous.shape)


def _integer_hkl(value: object, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype.kind == "b":
        raise ValueError(f"direct reflector evidence {field} must contain integer indices")
    try:
        numeric = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(
            f"direct reflector evidence {field} must contain integer indices"
        ) from None
    if not np.isfinite(numeric).all():
        raise ValueError(f"direct reflector evidence {field} must be finite")
    rounded = np.rint(numeric)
    if not np.allclose(numeric, rounded, rtol=0.0, atol=_AXIAL_TOLERANCE):
        raise ValueError(f"direct reflector evidence {field} must be integer-valued")
    limits = np.iinfo(np.int32)
    if np.any(rounded < limits.min) or np.any(rounded > limits.max):
        raise ValueError(f"direct reflector evidence {field} exceeds int32 range")
    contiguous = np.ascontiguousarray(rounded.astype(np.dtype("<i4")))
    return np.frombuffer(
        contiguous.tobytes(order="C"), dtype=np.dtype("<i4")
    ).reshape(contiguous.shape)


def _canonical_key(indices: np.ndarray) -> tuple[tuple[int, int, int], int]:
    nonzero = np.flatnonzero(indices)
    if not nonzero.size:
        raise ValueError("direct reflector evidence HKLs must be nonzero")
    sign = 1 if int(indices[int(nonzero[0])]) > 0 else -1
    return tuple(int(value) for value in sign * indices), sign


@dataclass(frozen=True)
class DirectReflectorRecipe:
    """Orientation-independent first-series reflector calculation policy."""

    schema_version: int
    name: str
    source_record: str
    energy_kev: float
    min_dspacing_angstrom: float
    scattering_params: str
    candidate_relative_factor: float
    weight_exponent: float
    eligibility_min_weight: float

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("direct reflector recipe schema_version must be integer 1")
        object.__setattr__(self, "name", _text(self.name, "name"))
        object.__setattr__(self, "source_record", _source_record(self.source_record))
        for field in (
            "energy_kev",
            "min_dspacing_angstrom",
            "candidate_relative_factor",
            "weight_exponent",
            "eligibility_min_weight",
        ):
            object.__setattr__(
                self,
                field,
                _exact_real(getattr(self, field), field, _FIRST_SERIES_VALUES[field]),
            )
        if self.scattering_params != "xtables":
            raise ValueError(
                "direct reflector recipe scattering_params must be exactly xtables"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_record": self.source_record,
            "energy_kev": self.energy_kev,
            "reflections": {
                "min_dspacing_angstrom": self.min_dspacing_angstrom,
                "scattering_params": self.scattering_params,
                "candidate_relative_factor": self.candidate_relative_factor,
            },
            "art_weight": {
                "exponent": self.weight_exponent,
                "eligibility_min_weight": self.eligibility_min_weight,
            },
        }

    @property
    def calculation_id(self) -> str:
        return stable_id(
            "reflector-calculation",
            {
                "energy_kev": self.energy_kev,
                "min_dspacing_angstrom": self.min_dspacing_angstrom,
                "scattering_params": self.scattering_params,
                "candidate_relative_factor": self.candidate_relative_factor,
            },
        )

    @property
    def weighting_id(self) -> str:
        return stable_id(
            "reflector-weighting",
            {
                "weight_exponent": self.weight_exponent,
                "eligibility_min_weight": self.eligibility_min_weight,
            },
        )


@dataclass(frozen=True, eq=False)
class DirectReflectorEvidence:
    """Immutable orientation-independent reflector channels and provenance."""

    source_structure_id: str
    source_structure_sha256: str
    calculation_id: str
    weighting_id: str
    hkl: np.ndarray
    normal_crystal: np.ndarray
    dspacing_angstrom: np.ndarray
    bragg_half_width_rad: np.ndarray
    structure_factor_magnitude: np.ndarray
    normalized_weight: np.ndarray
    ledger: Mapping[str, object]

    def __post_init__(self) -> None:
        source_structure_id = _identifier(self.source_structure_id, "source_structure_id")
        calculation_id = _identifier(self.calculation_id, "calculation_id")
        weighting_id = _identifier(self.weighting_id, "weighting_id")
        if not isinstance(self.source_structure_sha256, str) or not _HEX_SHA256.fullmatch(
            self.source_structure_sha256
        ):
            raise ValueError(
                "direct reflector evidence source_structure_sha256 must be 64 lowercase hex characters"
            )

        hkl = _integer_hkl(self.hkl, "hkl")
        if hkl.ndim != 2 or hkl.shape[1:] != (3,) or hkl.shape[0] == 0:
            raise ValueError("direct reflector evidence hkl must have non-empty shape (N, 3)")
        count = hkl.shape[0]
        channels = {
            "normal_crystal": _owned_float_array(self.normal_crystal, "normal_crystal"),
            "dspacing_angstrom": _owned_float_array(
                self.dspacing_angstrom, "dspacing_angstrom"
            ),
            "bragg_half_width_rad": _owned_float_array(
                self.bragg_half_width_rad, "bragg_half_width_rad"
            ),
            "structure_factor_magnitude": _owned_float_array(
                self.structure_factor_magnitude, "structure_factor_magnitude"
            ),
            "normalized_weight": _owned_float_array(
                self.normalized_weight, "normalized_weight"
            ),
        }
        if channels["normal_crystal"].shape != (count, 3):
            raise ValueError(
                "direct reflector evidence normal_crystal must have shape (N, 3)"
            )
        if any(
            channels[field].shape != (count,)
            for field in (
                "dspacing_angstrom",
                "bragg_half_width_rad",
                "structure_factor_magnitude",
                "normalized_weight",
            )
        ):
            raise ValueError(
                "direct reflector evidence scalar channels must have shape (N,)"
            )
        if not all(np.isfinite(channel).all() for channel in channels.values()):
            raise ValueError("direct reflector evidence channels must be finite")

        hkl_values: list[tuple[int, int, int]] = []
        for indices in hkl:
            canonical, sign = _canonical_key(indices)
            if sign != 1:
                raise ValueError(
                    "direct reflector evidence HKLs must use canonical first-nonzero-positive signs"
                )
            hkl_values.append(canonical)
        if len(set(hkl_values)) != count:
            raise ValueError("direct reflector evidence HKLs must be unique")

        normal_norm = np.linalg.norm(channels["normal_crystal"], axis=1)
        if not np.allclose(normal_norm, 1.0, rtol=0.0, atol=1e-12):
            raise ValueError("direct reflector evidence crystal normals must be unit length")
        for field in (
            "dspacing_angstrom",
            "bragg_half_width_rad",
            "structure_factor_magnitude",
        ):
            if np.any(channels[field] <= 0):
                raise ValueError(f"direct reflector evidence {field} must be positive")
        weights = channels["normalized_weight"]
        if np.any(weights < 0) or np.any(weights > 1):
            raise ValueError(
                "direct reflector evidence normalized_weight must be in [0, 1]"
            )

        if not isinstance(self.ledger, Mapping):
            raise ValueError("direct reflector evidence ledger must be a mapping")
        ledger_plain = plain_data(self.ledger)
        if not isinstance(ledger_plain, dict):
            raise ValueError("direct reflector evidence ledger must be a mapping")
        if type(ledger_plain.get("simulation_count")) is not int or ledger_plain.get(
            "simulation_count"
        ) != 0:
            raise ValueError("direct reflector evidence simulation_count must be integer 0")

        object.__setattr__(self, "source_structure_id", source_structure_id)
        object.__setattr__(self, "calculation_id", calculation_id)
        object.__setattr__(self, "weighting_id", weighting_id)
        object.__setattr__(self, "hkl", hkl)
        for field, channel in channels.items():
            object.__setattr__(self, field, channel)
        object.__setattr__(self, "ledger", _freeze_plain(ledger_plain))

    def identity_dict(self) -> dict[str, object]:
        return {
            "source_structure_id": self.source_structure_id,
            "source_structure_sha256": self.source_structure_sha256,
            "calculation_id": self.calculation_id,
            "weighting_id": self.weighting_id,
            "hkl": self.hkl.tolist(),
            "normal_crystal": self.normal_crystal.tolist(),
            "dspacing_angstrom": self.dspacing_angstrom.tolist(),
            "bragg_half_width_rad": self.bragg_half_width_rad.tolist(),
            "structure_factor_magnitude": self.structure_factor_magnitude.tolist(),
            "normalized_weight": self.normalized_weight.tolist(),
            "ledger": plain_data(self.ledger),
        }

    @property
    def evidence_id(self) -> str:
        return stable_id("reflector-evidence", self.identity_dict())


def load_direct_reflector_recipe(path: str | Path) -> DirectReflectorRecipe:
    """Load a strict version-1 first-series direct-reflector recipe."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("direct reflector recipe YAML is invalid") from None
    root = _mapping(payload, "top-level", _TOP_LEVEL_FIELDS)
    reflections = _mapping(root["reflections"], "reflections", _REFLECTION_FIELDS)
    art_weight = _mapping(root["art_weight"], "art_weight", _ART_WEIGHT_FIELDS)
    return DirectReflectorRecipe(
        schema_version=root["schema_version"],  # type: ignore[arg-type]
        name=root["name"],  # type: ignore[arg-type]
        source_record=root["source_record"],  # type: ignore[arg-type]
        energy_kev=root["energy_kev"],  # type: ignore[arg-type]
        min_dspacing_angstrom=reflections["min_dspacing_angstrom"],  # type: ignore[arg-type]
        scattering_params=reflections["scattering_params"],  # type: ignore[arg-type]
        candidate_relative_factor=reflections["candidate_relative_factor"],  # type: ignore[arg-type]
        weight_exponent=art_weight["exponent"],  # type: ignore[arg-type]
        eligibility_min_weight=art_weight["eligibility_min_weight"],  # type: ignore[arg-type]
    )


def _reflector_channels(
    reflectors: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    try:
        hkl = _integer_hkl(getattr(reflectors, "hkl"), "reflector hkl")
        normals = np.asarray(
            getattr(getattr(reflectors, "unit"), "data"), dtype=np.float64
        )
        dspacing = np.asarray(getattr(reflectors, "dspacing"), dtype=np.float64)
        theta = np.asarray(getattr(reflectors, "theta"), dtype=np.float64)
        structure_factor = np.asarray(getattr(reflectors, "structure_factor"))
    except (AttributeError, TypeError, ValueError):
        raise ValueError(
            "direct reflectors must expose hkl, unit.data, dspacing, theta, and structure_factor"
        ) from None
    count = hkl.shape[0] if hkl.ndim == 2 else 0
    strengths = np.asarray(np.abs(structure_factor), dtype=np.float64)
    if count == 0 or hkl.shape != (count, 3) or normals.shape != (count, 3):
        raise ValueError("direct reflector vector channels must have non-empty shape (N, 3)")
    if any(channel.shape != (count,) for channel in (dspacing, theta, strengths)):
        raise ValueError("direct reflector scalar channels must have shape (N,)")
    if not all(
        np.isfinite(channel).all()
        for channel in (normals, dspacing, theta, structure_factor, strengths)
    ):
        raise ValueError("direct reflector channels must be finite")
    if not np.allclose(np.linalg.norm(normals, axis=1), 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("direct reflector normals must be unit length")
    if np.any(dspacing <= 0) or np.any(theta <= 0) or np.any(strengths <= 0):
        raise ValueError("direct reflector d-spacings, angles, and strengths must be positive")
    return hkl, normals, dspacing, theta, strengths


def own_direct_reflector_evidence(
    reflectors: object,
    source_structure_id: str,
    source_structure_sha256: str,
    calculation_id: str,
    weighting_id: str,
    weight_exponent: float,
    eligibility_min_weight: float,
    counts: Mapping[str, int],
) -> DirectReflectorEvidence:
    """Collapse signed upstream reflectors into immutable axial evidence."""
    exponent = _positive_real(weight_exponent, "direct reflector weight_exponent")
    eligibility = _positive_real(
        eligibility_min_weight, "direct reflector eligibility_min_weight"
    )
    if eligibility > 1:
        raise ValueError("direct reflector eligibility_min_weight must be at most 1")
    if not isinstance(counts, Mapping) or any(
        not isinstance(name, str)
        or type(value) is not int
        or value < 0
        for name, value in counts.items()
    ):
        raise ValueError("direct reflector counts must map names to nonnegative integers")

    hkl, normals, dspacing, theta, strengths = _reflector_channels(reflectors)
    if "selected_signed" in counts and counts["selected_signed"] != hkl.shape[0]:
        raise ValueError("direct reflector selected_signed count does not match reflectors")

    groups: dict[
        tuple[int, int, int],
        list[tuple[tuple[int, int, int], np.ndarray, float, float, float]],
    ] = {}
    for indices, normal, spacing, angle, strength in zip(
        hkl, normals, dspacing, theta, strengths, strict=True
    ):
        key, sign = _canonical_key(indices)
        signed_indices = tuple(int(value) for value in indices)
        groups.setdefault(key, []).append(
            (
                signed_indices,
                sign * normal,
                float(spacing),
                float(angle),
                float(strength),
            )
        )

    output_hkl: list[tuple[int, int, int]] = []
    output_normals: list[np.ndarray] = []
    output_dspacing: list[float] = []
    output_theta: list[float] = []
    output_strength: list[float] = []
    for key in sorted(groups):
        pair = groups[key]
        negative_key = tuple(-value for value in key)
        signed_set = {item[0] for item in pair}
        if signed_set != {key, negative_key}:
            raise ValueError(f"axial reflector {key} does not include both signed indices")
        if sum(item[0] == key for item in pair) != sum(
            item[0] == negative_key for item in pair
        ):
            raise ValueError(f"axial reflector {key} has unbalanced signed duplicates")

        pair_normals = np.stack([item[1] for item in pair])
        pair_dspacing = np.asarray([item[2] for item in pair])
        pair_theta = np.asarray([item[3] for item in pair])
        pair_strength = np.asarray([item[4] for item in pair])
        if not np.allclose(pair_normals, pair_normals[0], rtol=0.0, atol=1e-9):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal normals")
        if not np.allclose(pair_dspacing, pair_dspacing[0], rtol=1e-9, atol=1e-11):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal d-spacings")
        if not np.allclose(pair_theta, pair_theta[0], rtol=1e-9, atol=1e-11):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal angles")
        if not np.allclose(pair_strength, pair_strength[0], rtol=1e-9, atol=1e-10):
            raise ValueError(f"axial reflector {key} has inconsistent antipodal strengths")

        normal = np.mean(pair_normals, axis=0)
        normal /= np.linalg.norm(normal)
        output_hkl.append(key)
        output_normals.append(normal)
        output_dspacing.append(float(np.mean(pair_dspacing)))
        output_theta.append(float(np.mean(pair_theta)))
        output_strength.append(float(np.mean(pair_strength)))

    output_strength_array = np.asarray(output_strength, dtype=np.float64)
    weights = (output_strength_array / float(np.max(strengths))) ** exponent
    owned_counts = dict(counts)
    if "axial" in owned_counts and owned_counts["axial"] != len(output_hkl):
        raise ValueError("direct reflector axial count does not match reflectors")
    owned_counts["axial"] = len(output_hkl)
    ledger = {
        "schema_version": 1,
        "units": {
            "normal_crystal": "dimensionless unit vector",
            "dspacing_angstrom": "angstrom",
            "bragg_half_width_rad": "radian",
            "structure_factor_magnitude": "absolute structure-factor magnitude",
            "normalized_weight": "dimensionless",
        },
        "formulas": {
            "axial_collapse": "exact hkl/-h-k-l pairs; first nonzero index positive",
            "normalized_weight": "(abs(F_hkl) / max(abs(F_hkl)))^weight_exponent",
        },
        "weight_exponent": exponent,
        "eligibility_min_weight": eligibility,
        "counts": owned_counts,
        "package_versions": {
            package: version(package)
            for package in ("diffpy-structure", "diffsims", "kikuchipy", "orix")
        },
        "simulation_count": 0,
        "orientation_dependency": "none",
    }
    return DirectReflectorEvidence(
        source_structure_id=source_structure_id,
        source_structure_sha256=source_structure_sha256,
        calculation_id=calculation_id,
        weighting_id=weighting_id,
        hkl=np.asarray(output_hkl, dtype=np.int32),
        normal_crystal=np.asarray(output_normals, dtype=np.float64),
        dspacing_angstrom=np.asarray(output_dspacing, dtype=np.float64),
        bragg_half_width_rad=np.asarray(output_theta, dtype=np.float64),
        structure_factor_magnitude=output_strength_array,
        normalized_weight=weights,
        ledger=ledger,
    )


__all__ = [
    "DirectReflectorEvidence",
    "DirectReflectorRecipe",
    "load_direct_reflector_recipe",
    "own_direct_reflector_evidence",
]

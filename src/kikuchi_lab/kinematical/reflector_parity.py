"""Strict direct-versus-simulator reflector parity reports."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

import numpy as np

from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id

from .reflector_evidence import DirectReflectorEvidence


_NORMAL_ATOL = 1e-12
_DSPACING_ATOL = 1e-12
_THETA_ATOL = 1e-12
_STRENGTH_ATOL = 1e-10
_WEIGHT_ATOL = 1e-12
_REQUIRED_COUNT_FIELDS = {
    "direct_enumerated",
    "direct_selected_signed",
    "direct_axial",
    "simulator_selected_signed",
    "simulator_axial",
}
_REQUIRED_PACKAGES = {"diffpy-structure", "diffsims", "kikuchipy", "orix"}
_REPORT_FIELDS = {
    "schema_version",
    "report_id",
    "run_id",
    "source_structure_id",
    "source_structure_sha256",
    "calculation_id",
    "weighting_id",
    "direct_evidence_id",
    "simulator_evidence_id",
    "passed",
    "provenance_match",
    "exact_hkl_match",
    "reflector_counts",
    "max_normal_abs_error",
    "max_dspacing_abs_error",
    "max_theta_abs_error",
    "max_strength_abs_error",
    "max_weight_abs_error",
    "tolerances",
    "package_versions",
    "simulation_count",
    "retry_count",
    "half_size",
    "hemisphere",
    "scaling",
    "master_shape",
    "master_array_sha256",
    "elapsed_seconds",
}


def _finite_nonnegative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"reflector parity {field} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"reflector parity {field} must be finite and nonnegative")
    return result


def _optional_residual(value: object, field: str) -> float | None:
    return None if value is None else _finite_nonnegative(value, field)


def _string_mapping(value: object, field: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) or not isinstance(item, str)
        for key, item in value.items()
    ):
        raise ValueError(f"reflector parity {field} must map text to text")
    return MappingProxyType(dict(value))


def _count_mapping(value: object) -> Mapping[str, int]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) or type(item) is not int or item < 0
        for key, item in value.items()
    ):
        raise ValueError(
            "reflector parity reflector_counts must map text to nonnegative integers"
        )
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class ReflectorParityReport:
    """Path-neutral evidence that one bounded diagnostic comparison passed."""

    source_structure_id: str
    source_structure_sha256: str
    calculation_id: str
    weighting_id: str
    direct_evidence_id: str
    simulator_evidence_id: str
    passed: bool
    provenance_match: bool
    exact_hkl_match: bool
    reflector_counts: Mapping[str, int]
    max_normal_abs_error: float | None
    max_dspacing_abs_error: float | None
    max_theta_abs_error: float | None
    max_strength_abs_error: float | None
    max_weight_abs_error: float | None
    package_versions: Mapping[str, str]
    simulation_count: int = 0
    retry_count: int = 0
    half_size: int | None = None
    hemisphere: str | None = None
    scaling: str | None = None
    master_shape: tuple[int, ...] = ()
    master_array_sha256: str | None = None
    elapsed_seconds: float = 0.0
    path: Path | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("reflector parity schema_version must be integer 1")
        for field in (
            "source_structure_id",
            "calculation_id",
            "weighting_id",
            "direct_evidence_id",
            "simulator_evidence_id",
        ):
            if not isinstance(getattr(self, field), str) or not getattr(self, field):
                raise ValueError(f"reflector parity {field} must be non-empty text")
        if (
            not isinstance(self.source_structure_sha256, str)
            or len(self.source_structure_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.source_structure_sha256)
        ):
            raise ValueError("reflector parity source_structure_sha256 must be lowercase SHA-256")
        for field in ("passed", "provenance_match", "exact_hkl_match"):
            if type(getattr(self, field)) is not bool:
                raise ValueError(f"reflector parity {field} must be boolean")
        object.__setattr__(self, "reflector_counts", _count_mapping(self.reflector_counts))
        for field in (
            "max_normal_abs_error",
            "max_dspacing_abs_error",
            "max_theta_abs_error",
            "max_strength_abs_error",
            "max_weight_abs_error",
        ):
            object.__setattr__(self, field, _optional_residual(getattr(self, field), field))
        object.__setattr__(self, "package_versions", _string_mapping(self.package_versions, "package_versions"))
        if type(self.simulation_count) is not int or self.simulation_count not in {0, 1}:
            raise ValueError("reflector parity simulation_count must be integer 0 or 1")
        if type(self.retry_count) is not int or self.retry_count != 0:
            raise ValueError("reflector parity retry_count must be integer 0")
        if self.simulation_count == 0:
            if any(
                value is not None
                for value in (
                    self.half_size,
                    self.hemisphere,
                    self.scaling,
                    self.master_array_sha256,
                )
            ) or self.master_shape:
                raise ValueError("reflector parity pre-master report cannot claim a simulation")
        else:
            if self.half_size != 32:
                raise ValueError("reflector parity half_size must be 32")
            if self.hemisphere != "both" or self.scaling != "square":
                raise ValueError("reflector parity master policy must be both/square")
            if tuple(self.master_shape) != (2, 65, 65):
                raise ValueError("reflector parity master_shape must be (2, 65, 65)")
            if (
                not isinstance(self.master_array_sha256, str)
                or len(self.master_array_sha256) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in self.master_array_sha256
                )
            ):
                raise ValueError("reflector parity master_array_sha256 must be lowercase SHA-256")
        object.__setattr__(
            self,
            "master_shape",
            tuple(int(dimension) for dimension in self.master_shape),
        )
        object.__setattr__(
            self,
            "elapsed_seconds",
            _finite_nonnegative(self.elapsed_seconds, "elapsed_seconds"),
        )
        if self.path is not None:
            object.__setattr__(self, "path", Path(self.path))

    @property
    def direct_reflector_count(self) -> int:
        return self.reflector_counts["direct_axial"]

    @property
    def simulator_reflector_count(self) -> int:
        return self.reflector_counts["simulator_axial"]

    @property
    def tolerances(self) -> dict[str, float]:
        return {
            "normal_abs": _NORMAL_ATOL,
            "dspacing_abs": _DSPACING_ATOL,
            "theta_abs": _THETA_ATOL,
            "strength_abs": _STRENGTH_ATOL,
            "weight_abs": _WEIGHT_ATOL,
        }

    def identity_dict(self) -> dict[str, object]:
        """Return content identity, excluding elapsed time and filesystem path."""
        return {
            "schema_version": self.schema_version,
            "source_structure_id": self.source_structure_id,
            "source_structure_sha256": self.source_structure_sha256,
            "calculation_id": self.calculation_id,
            "weighting_id": self.weighting_id,
            "direct_evidence_id": self.direct_evidence_id,
            "simulator_evidence_id": self.simulator_evidence_id,
            "passed": self.passed,
            "provenance_match": self.provenance_match,
            "exact_hkl_match": self.exact_hkl_match,
            "reflector_counts": plain_data(self.reflector_counts),
            "max_normal_abs_error": self.max_normal_abs_error,
            "max_dspacing_abs_error": self.max_dspacing_abs_error,
            "max_theta_abs_error": self.max_theta_abs_error,
            "max_strength_abs_error": self.max_strength_abs_error,
            "max_weight_abs_error": self.max_weight_abs_error,
            "tolerances": self.tolerances,
            "package_versions": plain_data(self.package_versions),
            "simulation_count": self.simulation_count,
            "retry_count": self.retry_count,
            "half_size": self.half_size,
            "hemisphere": self.hemisphere,
            "scaling": self.scaling,
            "master_shape": list(self.master_shape),
            "master_array_sha256": self.master_array_sha256,
        }

    @property
    def report_id(self) -> str:
        return stable_id("reflector-parity-report", self.identity_dict())

    @property
    def run_id(self) -> str:
        return stable_id("reflector-parity-run", {"report_id": self.report_id})

    def to_dict(self) -> dict[str, object]:
        return {
            **self.identity_dict(),
            "report_id": self.report_id,
            "run_id": self.run_id,
            "elapsed_seconds": self.elapsed_seconds,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_json(cls, payload: str) -> ReflectorParityReport:
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            raise ValueError("reflector parity worker response is not valid JSON") from None
        if not isinstance(value, dict) or set(value) != _REPORT_FIELDS:
            raise ValueError("reflector parity worker response fields differ from the schema")
        report_id = value.pop("report_id")
        run_id = value.pop("run_id")
        tolerances = value.pop("tolerances")
        report = cls(**value)
        if tolerances != report.tolerances:
            raise ValueError("reflector parity worker response tolerances differ")
        if report_id != report.report_id or run_id != report.run_id:
            raise ValueError("reflector parity worker response identity differs from its content")
        return report

    def with_master(self, master: object) -> ReflectorParityReport:
        array = np.ascontiguousarray(np.asarray(master, dtype=np.dtype("<f8")))
        if array.shape != (2, 65, 65) or not np.isfinite(array).all():
            raise ValueError("reflector parity master must be finite with shape (2, 65, 65)")
        return replace(
            self,
            simulation_count=1,
            half_size=32,
            hemisphere="both",
            scaling="square",
            master_shape=array.shape,
            master_array_sha256=hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        )

    def with_elapsed(self, elapsed_seconds: float) -> ReflectorParityReport:
        return replace(self, elapsed_seconds=elapsed_seconds)

    def with_path(self, path: str | Path) -> ReflectorParityReport:
        return replace(self, path=Path(path))

    def validate_for_publication(self) -> None:
        """Recompute whether this report is safe to publish as passing parity."""
        violations: list[str] = []
        if self.simulation_count != 1:
            violations.append("simulation_count must be 1")
        if self.retry_count != 0:
            violations.append("retry_count must be 0")
        if self.half_size != 32:
            violations.append("half_size must be 32")
        if self.hemisphere != "both":
            violations.append("hemisphere must be both")
        if self.scaling != "square":
            violations.append("scaling must be square")
        if self.master_shape != (2, 65, 65):
            violations.append("master_shape must be [2, 65, 65]")
        if self.master_array_sha256 is None:
            violations.append("master_array_sha256 is required")
        if not self.provenance_match:
            violations.append("provenance_match must be true")
        if not self.exact_hkl_match:
            violations.append("exact_hkl_match must be true")

        missing_counts = _REQUIRED_COUNT_FIELDS - set(self.reflector_counts)
        if missing_counts:
            violations.append(
                "missing reflector counts: " + ", ".join(sorted(missing_counts))
            )
        else:
            enumerated = self.reflector_counts["direct_enumerated"]
            direct_signed = self.reflector_counts["direct_selected_signed"]
            direct_axial = self.reflector_counts["direct_axial"]
            simulator_signed = self.reflector_counts["simulator_selected_signed"]
            simulator_axial = self.reflector_counts["simulator_axial"]
            if enumerated < direct_signed:
                violations.append("direct_enumerated must include all selected reflectors")
            if direct_signed <= 0 or direct_axial <= 0:
                violations.append("direct reflector counts must be positive")
            if direct_signed != simulator_signed:
                violations.append("selected signed reflector counts must match exactly")
            if direct_axial != simulator_axial:
                violations.append("axial reflector counts must match exactly")
            if direct_signed < 2 * direct_axial:
                violations.append("selected signed count must contain every axial pair")

        missing_packages = _REQUIRED_PACKAGES - set(self.package_versions)
        if missing_packages:
            violations.append(
                "missing package versions: " + ", ".join(sorted(missing_packages))
            )
        elif any(not self.package_versions[package] for package in _REQUIRED_PACKAGES):
            violations.append("required package versions must be non-empty")

        residual_limits = {
            "max_normal_abs_error": _NORMAL_ATOL,
            "max_dspacing_abs_error": _DSPACING_ATOL,
            "max_theta_abs_error": _THETA_ATOL,
            "max_strength_abs_error": _STRENGTH_ATOL,
            "max_weight_abs_error": _WEIGHT_ATOL,
        }
        for field, tolerance in residual_limits.items():
            residual = getattr(self, field)
            if residual is None:
                violations.append(f"{field} is required")
            elif not math.isfinite(residual) or residual > tolerance:
                violations.append(f"{field} exceeds {tolerance}")

        derived_passed = not violations
        if self.passed != derived_passed:
            violations.append("passed does not equal the recomputed result")
        if not derived_passed and self.passed is False:
            violations.append("recomputed parity conditions did not pass")
        if violations:
            raise ValueError(
                "reflector parity publication validation failed: "
                + "; ".join(violations)
            )


def _maximum_abs_error(first: np.ndarray, second: np.ndarray) -> float | None:
    if first.shape != second.shape:
        return None
    return float(np.max(np.abs(first - second)))


def _count(evidence: DirectReflectorEvidence, field: str, fallback: int) -> int:
    counts = evidence.ledger.get("counts", {})
    if isinstance(counts, Mapping):
        value = counts.get(field, fallback)
        if type(value) is int and value >= 0:
            return value
    return fallback


def compare_reflector_evidence(
    direct: DirectReflectorEvidence,
    simulator_owned: DirectReflectorEvidence,
) -> ReflectorParityReport:
    """Compare owned evidence using exact HKLs and fixed tight residual limits."""
    if not isinstance(direct, DirectReflectorEvidence) or not isinstance(
        simulator_owned, DirectReflectorEvidence
    ):
        raise TypeError("reflector parity inputs must be DirectReflectorEvidence")
    exact_hkl_match = np.array_equal(direct.hkl, simulator_owned.hkl)
    provenance_match = (
        direct.source_structure_id == simulator_owned.source_structure_id
        and direct.source_structure_sha256 == simulator_owned.source_structure_sha256
        and direct.calculation_id == simulator_owned.calculation_id
        and direct.weighting_id == simulator_owned.weighting_id
    )
    residuals = {
        "max_normal_abs_error": _maximum_abs_error(
            direct.normal_crystal, simulator_owned.normal_crystal
        ),
        "max_dspacing_abs_error": _maximum_abs_error(
            direct.dspacing_angstrom, simulator_owned.dspacing_angstrom
        ),
        "max_theta_abs_error": _maximum_abs_error(
            direct.bragg_half_width_rad, simulator_owned.bragg_half_width_rad
        ),
        "max_strength_abs_error": _maximum_abs_error(
            direct.structure_factor_magnitude,
            simulator_owned.structure_factor_magnitude,
        ),
        "max_weight_abs_error": _maximum_abs_error(
            direct.normalized_weight, simulator_owned.normalized_weight
        ),
    }
    limits = {
        "max_normal_abs_error": _NORMAL_ATOL,
        "max_dspacing_abs_error": _DSPACING_ATOL,
        "max_theta_abs_error": _THETA_ATOL,
        "max_strength_abs_error": _STRENGTH_ATOL,
        "max_weight_abs_error": _WEIGHT_ATOL,
    }
    passed = provenance_match and exact_hkl_match and all(
        residuals[field] is not None and residuals[field] <= tolerance
        for field, tolerance in limits.items()
    )
    direct_versions = direct.ledger.get("package_versions", {})
    simulator_versions = simulator_owned.ledger.get("package_versions", {})
    package_versions: Mapping[str, str] = {}
    if isinstance(direct_versions, Mapping) and direct_versions == simulator_versions:
        package_versions = {
            str(package): str(package_version)
            for package, package_version in direct_versions.items()
        }
    else:
        passed = False
    return ReflectorParityReport(
        source_structure_id=direct.source_structure_id,
        source_structure_sha256=direct.source_structure_sha256,
        calculation_id=direct.calculation_id,
        weighting_id=direct.weighting_id,
        direct_evidence_id=direct.evidence_id,
        simulator_evidence_id=simulator_owned.evidence_id,
        passed=passed,
        provenance_match=provenance_match,
        exact_hkl_match=exact_hkl_match,
        reflector_counts={
            "direct_enumerated": _count(direct, "enumerated", 0),
            "direct_selected_signed": _count(
                direct, "selected_signed", direct.hkl.shape[0] * 2
            ),
            "direct_axial": direct.hkl.shape[0],
            "simulator_selected_signed": _count(
                simulator_owned,
                "selected_signed",
                simulator_owned.hkl.shape[0] * 2,
            ),
            "simulator_axial": simulator_owned.hkl.shape[0],
        },
        package_versions=package_versions,
        **residuals,
    )


__all__ = ["ReflectorParityReport", "compare_reflector_evidence"]

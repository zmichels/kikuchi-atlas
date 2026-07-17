from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from kikuchi_lab.kinematical.reflector_evidence import DirectReflectorEvidence
from kikuchi_lab.kinematical.reflector_parity import compare_reflector_evidence


def _evidence() -> DirectReflectorEvidence:
    return DirectReflectorEvidence(
        source_structure_id="COD-test",
        source_structure_sha256="a" * 64,
        calculation_id="reflector-calculation-test",
        weighting_id="reflector-weighting-test",
        hkl=np.array([[0, 1, 0], [1, 0, 0]], dtype=np.int32),
        normal_crystal=np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]),
        dspacing_angstrom=np.array([3.0, 2.0]),
        bragg_half_width_rad=np.array([0.02, 0.01]),
        structure_factor_magnitude=np.array([5.0, 10.0]),
        normalized_weight=np.array([0.25, 1.0]),
        ledger={
            "simulation_count": 0,
            "counts": {"enumerated": 8, "selected_signed": 4, "axial": 2},
            "package_versions": {
                "diffpy-structure": "3.3.1",
                "diffsims": "0.7.0",
                "kikuchipy": "0.13.0",
                "orix": "0.14.1",
            },
        },
    )


def test_parity_comparator_requires_exact_hkls_and_tight_numeric_match() -> None:
    direct = _evidence()
    simulator_owned = _evidence()

    report = compare_reflector_evidence(direct, simulator_owned)

    assert report.passed
    assert report.exact_hkl_match
    assert report.direct_reflector_count == report.simulator_reflector_count == 2
    assert report.max_normal_abs_error <= 1e-12
    assert report.max_dspacing_abs_error <= 1e-12
    assert report.max_theta_abs_error <= 1e-12
    assert report.max_strength_abs_error <= 1e-10
    assert report.max_weight_abs_error <= 1e-12


def test_parity_comparator_rejects_reordered_hkls_even_when_channels_match() -> None:
    direct = _evidence()
    simulator_owned = DirectReflectorEvidence(
        **{
            **direct.identity_dict(),
            "hkl": direct.hkl[::-1],
            "normal_crystal": direct.normal_crystal[::-1],
            "dspacing_angstrom": direct.dspacing_angstrom[::-1],
            "bragg_half_width_rad": direct.bragg_half_width_rad[::-1],
            "structure_factor_magnitude": direct.structure_factor_magnitude[::-1],
            "normalized_weight": direct.normalized_weight[::-1],
        }
    )

    report = compare_reflector_evidence(direct, simulator_owned)

    assert not report.passed
    assert not report.exact_hkl_match


def test_parity_report_identity_excludes_elapsed_time() -> None:
    report = compare_reflector_evidence(_evidence(), _evidence()).with_master(
        np.arange(2 * 65 * 65, dtype=np.float64).reshape(2, 65, 65)
    )

    later = replace(report, elapsed_seconds=12.5)

    assert report.report_id == later.report_id
    assert report.identity_dict() == later.identity_dict()
    assert report.to_dict()["elapsed_seconds"] == 0.0
    assert later.to_dict()["elapsed_seconds"] == 12.5
    assert report.simulation_count == 1
    assert report.retry_count == 0
    assert report.half_size == 32
    assert report.master_shape == (2, 65, 65)
    assert len(report.master_array_sha256) == 64


def _passing_report():
    return compare_reflector_evidence(_evidence(), _evidence()).with_master(
        np.arange(2 * 65 * 65, dtype=np.float64).reshape(2, 65, 65)
    )


def test_publication_validation_accepts_derived_passing_science() -> None:
    _passing_report().validate_for_publication()


@pytest.mark.parametrize(
    "forge",
    [
        lambda report: replace(report, provenance_match=False, passed=True),
        lambda report: replace(report, exact_hkl_match=False, passed=True),
        lambda report: replace(
            report,
            reflector_counts={
                **report.reflector_counts,
                "simulator_selected_signed": 6,
            },
            passed=True,
        ),
        lambda report: replace(
            report,
            reflector_counts={
                key: value
                for key, value in report.reflector_counts.items()
                if key != "simulator_axial"
            },
            passed=True,
        ),
        lambda report: replace(
            report,
            package_versions={"kikuchipy": "0.13.0"},
            passed=True,
        ),
        lambda report: replace(report, max_normal_abs_error=None, passed=True),
        lambda report: replace(report, max_strength_abs_error=1.0, passed=True),
        lambda report: replace(report, passed=False),
    ],
)
def test_publication_validation_recomputes_passed_from_report_content(forge) -> None:
    forged = forge(_passing_report())

    with pytest.raises(ValueError, match="publication validation"):
        forged.validate_for_publication()

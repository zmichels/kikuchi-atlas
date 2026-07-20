from __future__ import annotations

import json
import os
import signal
import time
from dataclasses import replace
from pathlib import Path

import pytest

import kikuchi_lab.workflows.reflector_parity as parity_workflow
from kikuchi_lab.kinematical.reflector_parity import ReflectorParityReport
from kikuchi_lab.workflows.reflector_parity import (
    ReflectorParityTimeoutError,
    ReflectorParityWorkerError,
)


ROOT = Path(__file__).parents[2]
DESCENDANT_WORKER = "tests.fixtures.reflector_parity_descendant"


def _synthetic_report() -> ReflectorParityReport:
    return ReflectorParityReport(
        source_structure_id="COD-test",
        source_structure_sha256="a" * 64,
        calculation_id="reflector-calculation-test",
        weighting_id="reflector-weighting-test",
        direct_evidence_id="reflector-evidence-direct",
        simulator_evidence_id="reflector-evidence-simulator",
        passed=True,
        provenance_match=True,
        exact_hkl_match=True,
        reflector_counts={
            "direct_enumerated": 8,
            "direct_selected_signed": 4,
            "direct_axial": 2,
            "simulator_selected_signed": 4,
            "simulator_axial": 2,
        },
        max_normal_abs_error=0.0,
        max_dspacing_abs_error=0.0,
        max_theta_abs_error=0.0,
        max_strength_abs_error=0.0,
        max_weight_abs_error=0.0,
        package_versions={
            "diffpy-structure": "3.4.0",
            "diffsims": "0.7.0",
            "kikuchipy": "0.13.0",
            "orix": "0.14.3",
        },
        simulation_count=1,
        retry_count=0,
        half_size=32,
        hemisphere="both",
        scaling="square",
        master_shape=(2, 65, 65),
        master_array_sha256="b" * 64,
    )


def _descendant_pid_path(recipe_path: Path) -> Path:
    return recipe_path.with_suffix(".descendant.pid")


def _wait_for_descendant_pid(path: Path) -> int:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if path.is_file():
            return int(path.read_text(encoding="utf-8"))
        time.sleep(0.01)
    raise AssertionError(f"descendant PID was not recorded: {path}")


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _assert_descendant_stopped(path: Path) -> None:
    pid = _wait_for_descendant_pid(path)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and _pid_exists(pid):
        time.sleep(0.01)
    alive = _pid_exists(pid)
    try:
        assert not alive, f"worker descendant survived cleanup: PID {pid}"
    finally:
        if alive:
            os.kill(pid, signal.SIGKILL)


def test_parity_parent_terminates_worker_at_deadline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        parity_workflow,
        "_WORKER_MODULE",
        "tests.fixtures.reflector_parity_hang",
    )
    started = time.monotonic()
    with pytest.raises(ReflectorParityTimeoutError, match="0.05 seconds") as caught:
        parity_workflow.run_reflector_parity(
            recipe_path="recipes/reflectors/ice-ih-art-bands.yml",
            output_root=tmp_path,
            timeout_seconds=0.05,
        )
    assert time.monotonic() - started < 1.0
    assert caught.value.stdout == ""
    assert caught.value.stderr == ""
    assert not list(tmp_path.glob("reflector-parity-run-*"))


def test_parity_parent_retains_worker_streams_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        parity_workflow,
        "_WORKER_MODULE",
        "tests.fixtures.reflector_parity_missing",
    )

    with pytest.raises(ReflectorParityWorkerError, match="worker exited") as caught:
        parity_workflow.run_reflector_parity(
            recipe_path="recipes/reflectors/ice-ih-art-bands.yml",
            output_root=tmp_path,
            timeout_seconds=0.5,
        )

    assert caught.value.stdout == ""
    assert "reflector_parity_missing" in caught.value.stderr
    assert "reflector_parity_missing" in str(caught.value)
    assert not list(tmp_path.glob("reflector-parity-run-*"))


def test_timeout_cleanup_kills_signal_resistant_descendant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(parity_workflow, "_WORKER_MODULE", DESCENDANT_WORKER)
    recipe_path = tmp_path / "timeout.recipe"
    recipe_path.write_text("timeout", encoding="utf-8")

    try:
        with pytest.raises(ReflectorParityTimeoutError, match="0.5 seconds"):
            parity_workflow.run_reflector_parity(
                recipe_path=recipe_path,
                output_root=tmp_path / "output",
                timeout_seconds=0.5,
            )
    finally:
        _assert_descendant_stopped(_descendant_pid_path(recipe_path))


def test_worker_error_cleanup_kills_descendant_and_retains_streams(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(parity_workflow, "_WORKER_MODULE", DESCENDANT_WORKER)
    recipe_path = tmp_path / "worker-error.recipe"
    recipe_path.write_text("worker-error", encoding="utf-8")

    try:
        with pytest.raises(ReflectorParityWorkerError, match="status 7") as caught:
            parity_workflow.run_reflector_parity(
                recipe_path=recipe_path,
                output_root=tmp_path / "output",
                timeout_seconds=2.0,
            )

        assert "descendant worker stdout" in caught.value.stdout
        assert "descendant worker stderr" in caught.value.stderr
    finally:
        _assert_descendant_stopped(_descendant_pid_path(recipe_path))


@pytest.mark.parametrize(
    ("name", "payload", "message"),
    [
        ("missing-response.recipe", "missing", "without a response"),
        ("invalid-response.recipe", "invalid", "response failed validation"),
        (
            "forged-response.json",
            replace(
                _synthetic_report(),
                max_strength_abs_error=1.0,
                passed=True,
            ).to_json(),
            "publication validation",
        ),
        (
            "failed-response.json",
            replace(_synthetic_report(), passed=False).to_json(),
            "publication validation",
        ),
    ],
)
def test_response_failure_cleanup_kills_descendant_without_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    payload: str,
    message: str,
) -> None:
    monkeypatch.setattr(parity_workflow, "_WORKER_MODULE", DESCENDANT_WORKER)
    recipe_path = tmp_path / name
    recipe_path.write_text(payload, encoding="utf-8")
    output_root = tmp_path / "output"

    try:
        with pytest.raises(ReflectorParityWorkerError, match=message):
            parity_workflow.run_reflector_parity(
                recipe_path=recipe_path,
                output_root=output_root,
                timeout_seconds=2.0,
            )
    finally:
        _assert_descendant_stopped(_descendant_pid_path(recipe_path))
    assert not list(output_root.glob("reflector-parity-run-*"))


def test_communicate_exception_preserves_primary_error_and_triggers_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cleaned = []

    class BrokenProcess:
        pid = 123456789

        def communicate(self, timeout):
            raise OSError("pipe broke")

    monkeypatch.setattr(parity_workflow.subprocess, "Popen", lambda *args, **kwargs: BrokenProcess())
    monkeypatch.setattr(
        parity_workflow,
        "_terminate_then_kill",
        lambda process, *args, **kwargs: cleaned.append(process) or ("", ""),
    )

    with pytest.raises(OSError, match="pipe broke"):
        parity_workflow.run_reflector_parity(
            recipe_path=tmp_path / "unused.recipe",
            output_root=tmp_path / "output",
            timeout_seconds=1.0,
        )

    assert len(cleaned) == 1


def test_bounded_real_worker_publishes_one_passing_ice_report(tmp_path: Path) -> None:
    report = parity_workflow.run_reflector_parity(
        recipe_path=ROOT / "recipes/reflectors/ice-ih-art-bands.yml",
        output_root=tmp_path,
        timeout_seconds=90,
    )

    assert report.passed
    assert report.simulation_count == 1
    assert report.retry_count == 0
    assert report.half_size == 32
    assert report.master_shape == (2, 65, 65)
    assert report.elapsed_seconds <= 90
    assert report.path == tmp_path / report.run_id
    published = json.loads(
        (report.path / "reflector-parity-report.json").read_text(encoding="utf-8")
    )
    assert published == report.to_dict()
    assert published["report_id"] == report.report_id
    assert published["master_array_sha256"] == report.master_array_sha256

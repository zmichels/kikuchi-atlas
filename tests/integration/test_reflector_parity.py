from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import kikuchi_lab.workflows.reflector_parity as parity_workflow
from kikuchi_lab.workflows.reflector_parity import (
    ReflectorParityTimeoutError,
    ReflectorParityWorkerError,
)


ROOT = Path(__file__).parents[2]


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

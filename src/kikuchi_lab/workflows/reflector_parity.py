"""Killable one-smoke reflector parity workflow and worker entry point."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from kikuchi_lab.kinematical.reflector_parity import ReflectorParityReport


_WORKER_MODULE = "kikuchi_lab.workflows.reflector_parity"
_TERMINATE_GRACE_SECONDS = 0.25


class ReflectorParityWorkerError(RuntimeError):
    """Worker failure with captured diagnostic streams retained."""

    def __init__(self, message: str, *, stdout: str = "", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr
        details = [message]
        if stdout:
            details.append(f"worker stdout:\n{stdout.rstrip()}")
        if stderr:
            details.append(f"worker stderr:\n{stderr.rstrip()}")
        super().__init__("\n".join(details))


class ReflectorParityTimeoutError(ReflectorParityWorkerError):
    """Worker exceeded its one allowed hard deadline."""


def _worker(recipe_path: Path, response_path: Path) -> None:
    from kikuchipy.simulations import KikuchiPatternSimulator

    from kikuchi_lab.kinematical.kikuchipy_adapter import (
        _calculate_master_pattern_single_worker,
        _enumerate_reflectors,
        _phase_from_record,
        _select_reflectors,
        build_direct_reflector_evidence,
    )
    from kikuchi_lab.kinematical.reflector_evidence import (
        load_direct_reflector_recipe,
        own_direct_reflector_evidence,
    )
    from kikuchi_lab.kinematical.reflector_parity import compare_reflector_evidence
    from kikuchi_lab.sources.structure import load_structure_record

    recipe = load_direct_reflector_recipe(recipe_path)
    source = load_structure_record((recipe_path.parent / recipe.source_record).resolve())
    direct = build_direct_reflector_evidence(source, recipe)
    phase = _phase_from_record(source)
    selected = _select_reflectors(
        _enumerate_reflectors(phase, recipe),
        recipe.candidate_relative_factor,
        recipe.energy_kev,
    )
    simulator = KikuchiPatternSimulator(selected)
    master = _calculate_master_pattern_single_worker(
        simulator,
        half_size=32,
        hemisphere="both",
        scaling="square",
    )
    simulator_owned = own_direct_reflector_evidence(
        simulator.reflectors,
        source_structure_id=source.identifier,
        source_structure_sha256=source.sha256,
        calculation_id=recipe.calculation_id,
        weighting_id=recipe.weighting_id,
        weight_exponent=recipe.weight_exponent,
        eligibility_min_weight=recipe.eligibility_min_weight,
        counts={"selected_signed": simulator.reflectors.size},
    )
    report = compare_reflector_evidence(direct, simulator_owned).with_master(master.data)
    response_path.write_text(report.to_json(), encoding="utf-8")


def _validate_timeout(timeout_seconds: object) -> float:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise ValueError("reflector parity timeout_seconds must be a number")
    timeout = float(timeout_seconds)
    if not 0 < timeout <= 90:
        raise ValueError("reflector parity timeout_seconds must be in (0, 90]")
    return timeout


def _terminate_then_kill(
    process: subprocess.Popen[str],
) -> tuple[str, str]:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return process.communicate(timeout=_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.communicate()


def _publish_report(
    output_root: Path, report: ReflectorParityReport
) -> ReflectorParityReport:
    completed = output_root / report.run_id
    if completed.exists():
        raise FileExistsError(f"completed reflector parity report exists: {completed}")
    partial = output_root / f".{report.run_id}.partial-{uuid4().hex}"
    partial.mkdir()
    try:
        report_path = partial / "reflector-parity-report.json"
        with report_path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(report.to_json())
            handle.flush()
            os.fsync(handle.fileno())
        partial.rename(completed)
    except BaseException:
        if partial.exists():
            for child in partial.iterdir():
                child.unlink()
            partial.rmdir()
        raise
    return report.with_path(completed)


def run_reflector_parity(
    recipe_path: str | Path,
    output_root: str | Path,
    timeout_seconds: float = 90,
) -> ReflectorParityReport:
    """Run one master in a killable worker and publish only passing parity."""
    timeout = _validate_timeout(timeout_seconds)
    recipe_file = Path(recipe_path).resolve()
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with TemporaryDirectory(prefix="reflector-parity-run-", dir=root) as temporary:
        response_path = Path(temporary) / "worker-response.json"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                _WORKER_MODULE,
                "--worker",
                str(recipe_file),
                str(response_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stdout, stderr = _terminate_then_kill(process)
            raise ReflectorParityTimeoutError(
                f"reflector parity worker exceeded {timeout:g} seconds",
                stdout=stdout,
                stderr=stderr,
            ) from None
        if process.returncode != 0:
            raise ReflectorParityWorkerError(
                f"reflector parity worker exited with status {process.returncode}",
                stdout=stdout,
                stderr=stderr,
            )
        if not response_path.is_file():
            raise ReflectorParityWorkerError(
                "reflector parity worker exited without a response",
                stdout=stdout,
                stderr=stderr,
            )
        try:
            report = ReflectorParityReport.from_json(
                response_path.read_text(encoding="utf-8")
            ).with_elapsed(time.monotonic() - started)
        except (OSError, TypeError, ValueError) as error:
            raise ReflectorParityWorkerError(
                f"reflector parity worker response failed validation: {error}",
                stdout=stdout,
                stderr=stderr,
            ) from None
        if not report.passed:
            raise ReflectorParityWorkerError(
                "reflector parity comparison failed",
                stdout=stdout,
                stderr=stderr,
            )
    return _publish_report(root, report)


def _main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3 or arguments[0] != "--worker":
        print(
            "usage: python -m kikuchi_lab.workflows.reflector_parity "
            "--worker RECIPE_PATH RESPONSE_PATH",
            file=sys.stderr,
        )
        return 2
    _worker(Path(arguments[1]).resolve(), Path(arguments[2]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = [
    "ReflectorParityTimeoutError",
    "ReflectorParityWorkerError",
    "run_reflector_parity",
]

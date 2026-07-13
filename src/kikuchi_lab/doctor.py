"""Structured runtime diagnostics for the local Apple/WebGPU simulation stack."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import re
import tempfile
from pathlib import Path
from typing import Any


def _check(ok: bool, observed: Any, *, required: bool = True, details: Any = None) -> dict:
    result = {"ok": bool(ok), "required": required, "observed": observed}
    if details is not None:
        result["details"] = details
    return result


def _webgpu_check() -> dict:
    try:
        import wgpu

        adapters = wgpu.gpu.enumerate_adapters_sync()
        if not adapters:
            return _check(False, "no adapter", details={"error": "no WebGPU adapters found"})
        infos = [dict(adapter.info) for adapter in adapters]
        preferred = next(
            (info for info in infos if info.get("backend_type") == "Metal"), infos[0]
        )
        return _check(
            preferred.get("backend_type") == "Metal",
            preferred.get("device") or preferred.get("description") or "unknown",
            details=preferred,
        )
    except Exception as error:  # diagnostics must remain structured on import/driver failure
        return _check(False, type(error).__name__, details={"error": str(error)})


def _writability_check(output_root: Path) -> dict:
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output_root, prefix=".doctor-", delete=True):
            pass
        return _check(True, str(output_root))
    except OSError as error:
        return _check(False, str(output_root), details={"error": str(error)})


def _release(version_text: str | None) -> tuple[int, ...]:
    if version_text is None:
        return ()
    match = re.match(r"^(\d+(?:\.\d+)*)", version_text)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def _package_checks(packages: dict[str, str | None]) -> dict[str, dict]:
    requirements = {
        "ebsdsim": (packages["ebsdsim"] == "0.1.8", "==0.1.8"),
        "kikuchipy": (packages["kikuchipy"] == "0.13.0", "==0.13.0"),
        "numpy": ((2,) <= _release(packages["numpy"]) < (3,), ">=2,<3"),
        "wgpu": (_release(packages["wgpu"]) >= (0, 29), ">=0.29"),
    }
    return {
        f"package_{package}": _check(
            ok,
            packages[package],
            details={"requirement": requirement},
        )
        for package, (ok, requirement) in requirements.items()
    }


def collect_doctor_report(output_root: str | Path = "local") -> dict:
    """Collect required runtime facts without throwing for unavailable GPU support."""
    python_version = platform.python_version()
    machine = platform.machine()
    system = platform.system()
    packages = {}
    for package in ("ebsdsim", "kikuchipy", "numpy", "wgpu"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    checks = {
        "python_3_12": _check(
            platform.python_version_tuple()[:2] == ("3", "12"), python_version
        ),
        "arm64": _check(machine == "arm64", machine),
        "macos": _check(system == "Darwin", system),
        "webgpu_adapter": _webgpu_check(),
        "output_root_writable": _writability_check(Path(output_root).resolve()),
        **_package_checks(packages),
    }
    return {
        "schema_version": 1,
        "ok": all(value["ok"] for value in checks.values() if value["required"]),
        "platform": {
            "system": system,
            "release": platform.release(),
            "machine": machine,
            "python": python_version,
            "executable": os.path.realpath(os.sys.executable),
        },
        "packages": packages,
        "checks": checks,
    }

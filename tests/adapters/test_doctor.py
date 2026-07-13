from __future__ import annotations

import json
import importlib.metadata

from kikuchi_lab.cli.main import main
from kikuchi_lab.doctor import collect_doctor_report


def test_doctor_reports_native_python_packages_metal_and_writability(tmp_path):
    report = collect_doctor_report(tmp_path)

    assert report["schema_version"] == 1
    assert report["checks"]["python_3_12"]["ok"]
    assert report["checks"]["arm64"]["observed"] == "arm64"
    assert report["checks"]["output_root_writable"]["ok"]
    assert report["checks"]["webgpu_adapter"]["details"]["backend_type"] == "Metal"
    assert report["packages"]["ebsdsim"] == "0.1.8"
    assert report["checks"]["package_ebsdsim"]["ok"]
    assert report["checks"]["package_kikuchipy"]["ok"]
    assert report["checks"]["package_numpy"]["ok"]
    assert report["checks"]["package_wgpu"]["ok"]


def test_doctor_missing_required_package_contributes_to_failed_readiness(tmp_path, monkeypatch):
    real_version = importlib.metadata.version

    def version_or_missing(package):
        if package == "ebsdsim":
            raise importlib.metadata.PackageNotFoundError(package)
        return real_version(package)

    monkeypatch.setattr(importlib.metadata, "version", version_or_missing)
    report = collect_doctor_report(tmp_path)

    assert not report["checks"]["package_ebsdsim"]["ok"]
    assert report["checks"]["package_ebsdsim"]["required"]
    assert not report["ok"]


def test_doctor_cli_emits_valid_json_even_when_a_required_check_fails(tmp_path, capsys):
    status = main(["doctor", "--json", "--output-root", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert status == (0 if payload["ok"] else 1)
    assert set(payload["checks"]) >= {
        "python_3_12",
        "arm64",
        "macos",
        "webgpu_adapter",
        "output_root_writable",
    }

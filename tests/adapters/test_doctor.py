from __future__ import annotations

import json

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

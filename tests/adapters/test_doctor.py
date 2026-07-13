from __future__ import annotations

import json
from kikuchi_lab.cli.main import main
from kikuchi_lab.doctor import DoctorProbes, collect_doctor_report


READY = DoctorProbes(
    python_version="3.12.9",
    machine="arm64",
    system="Darwin",
    release="test-release",
    executable="/managed/python",
    packages={
        "ebsdsim": "0.1.8",
        "kikuchipy": "0.13.0",
        "numpy": "2.4.0",
        "wgpu": "0.31.1",
    },
    webgpu={
        "ok": True,
        "required": True,
        "observed": "Test GPU",
        "details": {"backend_type": "Metal"},
    },
)


def test_doctor_reports_injected_ready_environment(tmp_path):
    report = collect_doctor_report(tmp_path, probes=READY)

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


def test_doctor_missing_required_package_contributes_to_failed_readiness(tmp_path):
    probes = DoctorProbes(**{**READY.__dict__, "packages": {**READY.packages, "ebsdsim": None}})
    report = collect_doctor_report(tmp_path, probes=probes)

    assert not report["checks"]["package_ebsdsim"]["ok"]
    assert report["checks"]["package_ebsdsim"]["required"]
    assert not report["ok"]


def test_doctor_structures_wrong_platform_and_unavailable_gpu(tmp_path):
    probes = DoctorProbes(
        **{
            **READY.__dict__,
            "machine": "x86_64",
            "system": "Linux",
            "webgpu": {
                "ok": False,
                "required": True,
                "observed": "no adapter",
                "details": {"error": "unavailable"},
            },
        }
    )
    report = collect_doctor_report(tmp_path, probes=probes)
    assert not report["checks"]["arm64"]["ok"]
    assert not report["checks"]["macos"]["ok"]
    assert not report["checks"]["webgpu_adapter"]["ok"]
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

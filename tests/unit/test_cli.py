from kikuchi_lab.cli.main import main


def test_version_command_reports_package_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "kikuchi-lab 0.1.0"


def test_proof_command_reports_invalid_master_without_traceback(tmp_path, capsys):
    status = main(
        [
            "proof",
            "--recipe",
            "recipes/proof/forsterite-proof.yml",
            "--master-product",
            str(tmp_path / "missing.npz"),
            "--source",
            str(tmp_path / "missing.cif"),
            "--output",
            str(tmp_path / "runs"),
        ]
    )

    assert status == 1
    assert "proof failed" in capsys.readouterr().err

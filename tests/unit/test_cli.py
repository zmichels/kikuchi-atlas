import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kikuchi_lab.cli.main import main


ROOT = Path(__file__).parents[2]


def _proof_recipe_with_local_dependencies(tmp_path: Path) -> Path:
    proof = (ROOT / "recipes/proof/forsterite-proof.yml").read_text()
    (tmp_path / "forsterite-candidates.yml").write_text(
        (ROOT / "recipes/proof/forsterite-candidates.yml").read_text()
    )
    (tmp_path / "scientific-clean.yml").write_text(
        (ROOT / "recipes/proof/scientific-clean.yml").read_text()
    )
    path = tmp_path / "proof.yml"
    path.write_text(proof)
    return path


@pytest.fixture
def proof_cli_before_origin(monkeypatch):
    import kikuchi_lab.model
    import kikuchi_lab.workflows.proof

    monkeypatch.setattr(kikuchi_lab.model, "load_master_product", lambda _path: object())
    monkeypatch.setattr(
        kikuchi_lab.workflows.proof,
        "validate_master_for_proof",
        lambda _master, _contract: None,
    )


def _run_proof_cli(recipe: Path, tmp_path: Path) -> int:
    return main(
        [
            "proof",
            "--recipe",
            str(recipe),
            "--master-product",
            str(tmp_path / "master.npz"),
            "--source",
            str(tmp_path / "source.cif"),
            "--output",
            str(tmp_path / "runs"),
        ]
    )


def test_version_command_reports_package_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "kikuchi-lab 0.1.0"


def test_render_kinematical_cli_forwards_paths_and_prints_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed = {}

    def fake_render_kinematical(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            run_id="kinematical-run-0123456789abcdef",
            path=tmp_path / "kinematical-run-0123456789abcdef",
            recipe_id="recipe-0123456789abcdef",
            master_reflector_count=2546,
            figure_names=("etched-master-balanced.png", "etched-master-quiet.png"),
        )

    monkeypatch.setattr("kikuchi_lab.workflows.render_kinematical", fake_render_kinematical)

    status = main(
        [
            "render-kinematical",
            "--recipe",
            "recipes/kinematical/forsterite-etched-master.yml",
            "--output",
            str(tmp_path / "runs"),
        ]
    )

    assert status == 0
    assert observed == {
        "recipe_path": "recipes/kinematical/forsterite-etched-master.yml",
        "output_root": str(tmp_path / "runs"),
    }
    assert json.loads(capsys.readouterr().out) == {
        "figures": ["etched-master-balanced.png", "etched-master-quiet.png"],
        "master_reflector_count": 2546,
        "path": str(tmp_path / "kinematical-run-0123456789abcdef"),
        "recipe_id": "recipe-0123456789abcdef",
        "run_id": "kinematical-run-0123456789abcdef",
    }


@pytest.mark.parametrize("error", [ValueError("bad recipe"), OSError("disk full")])
def test_render_kinematical_cli_normalizes_errors_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def fail_render_kinematical(**_kwargs):
        raise error

    monkeypatch.setattr("kikuchi_lab.workflows.render_kinematical", fail_render_kinematical)

    status = main(
        [
            "render-kinematical",
            "--recipe",
            "recipe.yml",
            "--output",
            str(tmp_path / "runs"),
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == f"kinematical render failed: {error}\n"
    assert "Traceback" not in captured.err


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


def test_proof_command_normalizes_malformed_recipe_without_traceback(tmp_path, capsys):
    recipe = tmp_path / "malformed.yml"
    recipe.write_text("schema_version: [")

    status = main(
        [
            "proof",
            "--recipe",
            str(recipe),
            "--master-product",
            str(tmp_path / "missing.npz"),
            "--source",
            str(tmp_path / "missing.cif"),
            "--output",
            str(tmp_path / "runs"),
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert "proof failed: proof recipe YAML" in captured.err
    assert "Traceback" not in captured.err


def test_proof_command_normalizes_malformed_candidate_yaml_without_traceback(
    tmp_path, capsys, proof_cli_before_origin
):
    recipe = _proof_recipe_with_local_dependencies(tmp_path)
    (tmp_path / "forsterite-candidates.yml").write_text("candidates: [")

    status = _run_proof_cli(recipe, tmp_path)

    captured = capsys.readouterr()
    assert status == 1
    assert "proof failed: candidate_recipe" in captured.err
    assert "forsterite-candidates.yml" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "processing_payload",
    ["stages: [", "schema_version: 1\nname: clean\nintent: test\nstages: wrong\n"],
)
def test_proof_command_normalizes_invalid_processing_recipe_without_traceback(
    tmp_path, capsys, proof_cli_before_origin, processing_payload
):
    recipe = _proof_recipe_with_local_dependencies(tmp_path)
    (tmp_path / "scientific-clean.yml").write_text(processing_payload)

    status = _run_proof_cli(recipe, tmp_path)

    captured = capsys.readouterr()
    assert status == 1
    assert "proof failed: processing_recipe" in captured.err
    assert "scientific-clean.yml" in captured.err
    assert "Traceback" not in captured.err

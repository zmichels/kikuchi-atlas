import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kikuchi_lab.cli.main import main
from kikuchi_lab.relief import ReliefGlobeBuildResult


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


def test_habit_build_cli_routes_arguments_and_prints_json(monkeypatch, capsys):
    expected = SimpleNamespace(
        build_id="habit-build-abc123",
        path=Path("/tmp/habit-build-abc123"),
        stl=Path("/tmp/habit-build-abc123/quartz-habit.stl"),
        preview=Path("/tmp/habit-build-abc123/quartz-habit-preview.png"),
        validation=Path("/tmp/habit-build-abc123/mesh-validation.json"),
        parity=Path("/tmp/habit-build-abc123/mtex-parity.json"),
    )
    calls = []
    monkeypatch.setattr(
        "kikuchi_lab.habit.build_habit",
        lambda recipe, output, *, mtex_reference=None: calls.append(
            (recipe, output, mtex_reference)
        )
        or expected,
    )

    assert (
        main(
            [
                "habit",
                "build",
                "--recipe",
                "r.yml",
                "--mtex-reference",
                "mtex.json",
                "--output",
                "out",
            ]
        )
        == 0
    )
    assert calls == [("r.yml", "out", "mtex.json")]
    payload = json.loads(capsys.readouterr().out)
    assert payload["build_id"] == expected.build_id
    assert payload["parity"] == str(expected.parity)


def test_habit_build_cli_reports_domain_error_without_traceback(monkeypatch, capsys):
    def fail(*_args, **_kwargs):
        raise ValueError("maximum_dimension_mm must be positive")

    monkeypatch.setattr("kikuchi_lab.habit.build_habit", fail)
    assert main(["habit", "build", "--recipe", "bad.yml", "--output", "out"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "kikuchi-lab: habit build failed: maximum_dimension_mm must be positive\n"
    )
    assert "Traceback" not in captured.err


def test_relief_globe_build_cli_routes_paths_and_prints_json(monkeypatch, capsys, tmp_path):
    bundle = tmp_path / "relief-globe-build-abc"
    result = ReliefGlobeBuildResult(
        build_id=bundle.name,
        path=bundle,
        manifest=bundle / "relief-manifest.json",
        stl=bundle / "phase-intensity-relief-globe.stl",
        preview=bundle / "phase-intensity-relief-preview.png",
        field=bundle / "relief-field.npz",
        validation=bundle / "mesh-validation.json",
    )
    calls = []
    monkeypatch.setattr(
        "kikuchi_lab.relief.build_relief_globe",
        lambda master, recipe, output: calls.append((master, recipe, output)) or result,
    )
    assert main(["relief", "globe", "build", "--master-pattern", "master.npz",
                 "--recipe", "recipe.yml", "--output", "out"]) == 0
    assert calls == [("master.npz", "recipe.yml", "out")]
    assert json.loads(capsys.readouterr().out) == {
        "build_id": result.build_id,
        "field": str(result.field),
        "manifest": str(result.manifest),
        "path": str(result.path),
        "preview": str(result.preview),
        "stl": str(result.stl),
        "validation": str(result.validation),
    }


def test_relief_globe_build_cli_reports_domain_failure(monkeypatch, capsys):
    def fail(*_args):
        raise ValueError("source mismatch")

    monkeypatch.setattr("kikuchi_lab.relief.build_relief_globe", fail)
    assert main(["relief", "globe", "build", "--master-pattern", "master.npz",
                 "--recipe", "recipe.yml", "--output", "out"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "kikuchi-lab: relief globe build failed: source mismatch\n"
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

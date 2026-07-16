import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
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


def test_render_kinematical_depth_cli_forwards_paths_and_prints_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}

    def fake_render_kinematical_depth(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            run_id="near-depth-run-0123456789abcdef",
            path=tmp_path / "near-depth-run-0123456789abcdef",
            treatment_recipe_id="recipe-0123456789abcdef",
            base_recipe_id="recipe-fedcba9876543210",
            figure_names=(
                "etched-master-near-depth-stepped.png",
                "quiet-vs-near-depth-stepped.png",
            ),
        )

    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_kinematical_depth",
        fake_render_kinematical_depth,
        raising=False,
    )

    status = main(
        [
            "render-kinematical-depth",
            "--recipe",
            "recipes/presentation/ice-ih-near-depth-stepped.yml",
            "--output",
            str(tmp_path / "runs"),
            "--figure-size-px",
            "480",
        ]
    )

    assert status == 0
    assert observed == {
        "recipe_path": "recipes/presentation/ice-ih-near-depth-stepped.yml",
        "output_root": str(tmp_path / "runs"),
        "figure_size_px": 480,
    }
    assert json.loads(capsys.readouterr().out) == {
        "base_recipe_id": "recipe-fedcba9876543210",
        "figures": [
            "etched-master-near-depth-stepped.png",
            "quiet-vs-near-depth-stepped.png",
        ],
        "path": str(tmp_path / "near-depth-run-0123456789abcdef"),
        "run_id": "near-depth-run-0123456789abcdef",
        "treatment_recipe_id": "recipe-0123456789abcdef",
    }


def test_render_kinematical_depth_cli_normalizes_errors_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_render_kinematical_depth(**_kwargs):
        raise ValueError("bad depth recipe")

    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_kinematical_depth",
        fail_render_kinematical_depth,
        raising=False,
    )

    status = main(
        [
            "render-kinematical-depth",
            "--recipe",
            "depth.yml",
            "--output",
            str(tmp_path / "runs"),
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == "kinematical depth render failed: bad depth recipe\n"
    assert "Traceback" not in captured.err


def test_render_oriented_spherical_dispatches_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    called = {}
    smoke = SimpleNamespace(
        profile="smoke",
        run_id="smoke-run",
        path=tmp_path / "smoke",
        source_half_size=32,
        figure_names=("a.png",),
        manifest_sha256="a" * 64,
        elapsed_seconds=1.0,
    )
    review = SimpleNamespace(
        profile="review",
        run_id="review-run",
        path=tmp_path / "review",
        source_half_size=512,
        figure_names=("b.png",),
        manifest_sha256="b" * 64,
        elapsed_seconds=2.0,
    )
    fake_result = SimpleNamespace(smoke=smoke, review=review)
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_oriented_spherical_master",
        lambda **kwargs: called.update(kwargs) or fake_result,
    )

    status = main(
        [
            "render-oriented-spherical",
            "--recipe",
            "recipes/spherical/ice-ih-oriented-s2-proof.yml",
            "--output",
            str(tmp_path),
            "--profile",
            "review",
        ]
    )

    assert status == 0
    assert called == {
        "recipe_path": "recipes/spherical/ice-ih-oriented-s2-proof.yml",
        "output_root": str(tmp_path),
        "profile": "review",
    }
    expected = {
        "review": {
            "elapsed_seconds": 2.0,
            "figures": ["b.png"],
            "manifest_sha256": "b" * 64,
            "path": str(tmp_path / "review"),
            "profile": "review",
            "run_id": "review-run",
            "source_half_size": 512,
        },
        "smoke": {
            "elapsed_seconds": 1.0,
            "figures": ["a.png"],
            "manifest_sha256": "a" * 64,
            "path": str(tmp_path / "smoke"),
            "profile": "smoke",
            "run_id": "smoke-run",
            "source_half_size": 32,
        },
    }
    assert capsys.readouterr().out == json.dumps(expected, indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize(
    "error",
    [
        BundleExistsError("completed bundle exists"),
        PartialBundleError("partial bundle exists"),
        OSError("disk full"),
        ValueError("bad recipe"),
        RuntimeError("bounded failure"),
    ],
)
def test_render_oriented_spherical_normalizes_known_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_oriented_spherical_master",
        Mock(side_effect=error),
    )

    status = main(
        [
            "render-oriented-spherical",
            "--recipe",
            "x.yml",
            "--output",
            "out",
            "--profile",
            "smoke",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == f"oriented spherical render failed: {error}\n"
    assert "Traceback" not in captured.err


def test_workflows_exports_oriented_spherical_contract() -> None:
    import kikuchi_lab.workflows as workflows
    from kikuchi_lab.workflows.oriented_spherical import (
        OrientedSphericalRunResult,
        render_oriented_spherical_master,
    )

    assert workflows.OrientedSphericalRunResult is OrientedSphericalRunResult
    assert workflows.render_oriented_spherical_master is render_oriented_spherical_master


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

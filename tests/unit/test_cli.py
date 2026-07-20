import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.cli.main import main
from kikuchi_lab.relief import ReliefGlobeBuildResult
from kikuchi_lab.reflectors.bundle import ReflectorCatalogBuildResult


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


def test_reflector_catalog_build_cli_routes_paths_and_prints_json(monkeypatch, capsys, tmp_path):
    bundle = tmp_path / "reflector-catalog-build-abc"
    result = ReflectorCatalogBuildResult(
        run_id=bundle.name,
        path=bundle,
        catalog=bundle / "reflector-catalog.json",
        recipe=bundle / "catalog-recipe.json",
        ledger=bundle / "catalog-ledger.json",
        manifest=bundle / "manifest.json",
    )
    calls = []
    monkeypatch.setattr(
        "kikuchi_lab.workflows.reflector_catalog.build_reflector_catalog_bundle",
        lambda recipe, output: calls.append((recipe, output)) or result,
    )

    assert main(["reflectors", "build", "--recipe", "recipe.yml", "--output", "out"]) == 0
    assert calls == [("recipe.yml", "out")]
    assert json.loads(capsys.readouterr().out) == {
        "catalog": str(result.catalog),
        "ledger": str(result.ledger),
        "manifest": str(result.manifest),
        "path": str(result.path),
        "recipe": str(result.recipe),
        "run_id": result.run_id,
    }


def test_reflector_catalog_build_cli_reports_domain_failure(monkeypatch, capsys):
    def fail(*_args):
        raise ValueError("source mismatch")

    monkeypatch.setattr("kikuchi_lab.workflows.reflector_catalog.build_reflector_catalog_bundle", fail)
    assert main(["reflectors", "build", "--recipe", "bad.yml", "--output", "out"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "kikuchi-lab: reflector catalog build failed: source mismatch\n"
    assert "Traceback" not in captured.err


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


def test_build_ice_art_catalog_cli_forwards_paths_and_emits_sorted_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}
    result = SimpleNamespace(
        run_id="ice-art-catalog-run-0123456789abcdef",
        path=tmp_path / "ice-art-catalog-run-0123456789abcdef",
        catalog_id="art-band-catalog-fedcba9876543210",
        member_count=147,
        manifest_sha256="a" * 64,
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.build_ice_art_catalog",
        lambda **kwargs: observed.update(kwargs) or result,
        raising=False,
    )

    status = main(
        [
            "build-ice-art-catalog",
            "--recipe",
            "recipes/art/ice-ih-band-catalog.yml",
            "--output",
            "local/ice-art-catalog",
        ]
    )

    assert status == 0
    assert observed == {
        "recipe_path": "recipes/art/ice-ih-band-catalog.yml",
        "output_root": "local/ice-art-catalog",
    }
    expected = {
        "catalog_id": "art-band-catalog-fedcba9876543210",
        "manifest_sha256": "a" * 64,
        "member_count": 147,
        "path": str(result.path),
        "run_id": "ice-art-catalog-run-0123456789abcdef",
    }
    assert capsys.readouterr().out == json.dumps(expected, indent=2, sort_keys=True) + "\n"


def test_build_direct_art_catalog_cli_returns_content_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}
    result = SimpleNamespace(
        run_id="direct-art-catalog-run-0123456789abcdef",
        path=tmp_path / "direct-art-catalog-run-0123456789abcdef",
        catalog_id="art-band-catalog-fedcba9876543210",
        evidence_id="reflector-evidence-0123456789abcdef",
        member_count=147,
        eligible_member_count=23,
        simulation_count=0,
        manifest_sha256="c" * 64,
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.build_direct_art_catalog",
        lambda **kwargs: observed.update(kwargs) or result,
        raising=False,
    )

    status = main(
        [
            "build-direct-art-catalog",
            "--recipe",
            "recipes/reflectors/forsterite-art-bands.yml",
            "--output",
            str(tmp_path),
        ]
    )

    assert status == 0
    assert observed == {
        "recipe_path": "recipes/reflectors/forsterite-art-bands.yml",
        "output_root": str(tmp_path),
    }
    expected = {
        "catalog_id": result.catalog_id,
        "eligible_member_count": 23,
        "evidence_id": result.evidence_id,
        "manifest_sha256": "c" * 64,
        "member_count": 147,
        "path": str(result.path),
        "run_id": result.run_id,
        "simulation_count": 0,
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
def test_build_direct_art_catalog_cli_normalizes_known_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.build_direct_art_catalog",
        Mock(side_effect=error),
        raising=False,
    )

    status = main(
        [
            "build-direct-art-catalog",
            "--recipe",
            "recipe.yml",
            "--output",
            "out",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == f"direct art catalog build failed: {error}\n"
    assert "Traceback" not in captured.err


def test_validate_reflector_parity_cli_requires_90_and_emits_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}
    payload = {
        "schema_version": 1,
        "report_id": "reflector-parity-report-0123456789abcdef",
        "run_id": "reflector-parity-run-fedcba9876543210",
        "passed": True,
        "simulation_count": 1,
        "retry_count": 0,
        "half_size": 32,
        "master_shape": [2, 65, 65],
        "master_array_sha256": "a" * 64,
        "elapsed_seconds": 2.5,
    }
    result = SimpleNamespace(
        path=tmp_path / payload["run_id"],
        to_dict=lambda: dict(payload),
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.run_reflector_parity",
        lambda *args, **kwargs: observed.update(kwargs) or result,
        raising=False,
    )

    status = main(
        [
            "validate-reflector-parity",
            "--recipe",
            "recipes/reflectors/ice-ih-art-bands.yml",
            "--output",
            str(tmp_path),
            "--timeout-seconds",
            "90",
        ]
    )

    assert status == 0
    assert observed == {
        "recipe_path": "recipes/reflectors/ice-ih-art-bands.yml",
        "output_root": str(tmp_path),
        "timeout_seconds": 90,
    }
    assert json.loads(capsys.readouterr().out) == {
        **payload,
        "path": str(result.path),
    }


@pytest.mark.parametrize("timeout", ["true", "90.0", "0", "91", "89"])
def test_validate_reflector_parity_cli_rejects_noncanonical_timeout(
    timeout: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = Mock(side_effect=AssertionError("workflow must not run"))
    monkeypatch.setattr(
        "kikuchi_lab.workflows.run_reflector_parity", worker, raising=False
    )

    with pytest.raises(SystemExit, match="2"):
        main(
            [
                "validate-reflector-parity",
                "--recipe",
                "recipe.yml",
                "--output",
                "out",
                "--timeout-seconds",
                timeout,
            ]
        )

    worker.assert_not_called()


def test_validate_reflector_parity_cli_retains_failure_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.run_reflector_parity",
        Mock(side_effect=RuntimeError("worker stderr: bounded failure")),
        raising=False,
    )

    status = main(
        [
            "validate-reflector-parity",
            "--recipe",
            "recipe.yml",
            "--output",
            "out",
            "--timeout-seconds",
            "90",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == (
        "reflector parity validation failed: worker stderr: bounded failure\n"
    )
    assert "Traceback" not in captured.err


def test_render_phase_art_series_cli_emits_finite_work_and_exact_success_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}
    bundles = tuple(
        SimpleNamespace(run_id=f"phase-bundle-{index:02d}-0123456789abcdef")
        for index in range(9)
    )
    result = SimpleNamespace(
        series_id="phase-art-series-0123456789abcdef",
        path=tmp_path / "phase-art-series-0123456789abcdef",
        new_bundles=bundles,
        comparison_sheet=(
            tmp_path / "phase-art-series-0123456789abcdef" / "comparison.png"
        ),
        simulation_count=0,
        manifest_sha256="d" * 64,
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_phase_art_series",
        lambda **kwargs: observed.update(kwargs) or result,
        raising=False,
    )

    status = main(
        [
            "render-phase-art-series",
            "--recipe",
            "recipes/art/five-phase-hemisphere-series.yml",
            "--parity-root",
            "/tmp/parity",
            "--ice-standard-reference",
            "/tmp/ice-standard",
            "--output",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    assert observed == {
        "recipe_path": "recipes/art/five-phase-hemisphere-series.yml",
        "parity_root": "/tmp/parity",
        "ice_standard_reference": "/tmp/ice-standard",
        "output_root": str(tmp_path),
    }
    assert captured.err == (
        "phase-art-series finite-work phases=5 new_bundle_count=9 "
        "comparison_cells=10 simulation_count=0 "
        "orientation_bunge_deg=17,31,43\n"
    )
    assert json.loads(captured.out) == {
        "bundle_ids": [bundle.run_id for bundle in bundles],
        "comparison_sheet": str(result.comparison_sheet),
        "manifest_sha256": "d" * 64,
        "new_bundle_count": 9,
        "path": str(result.path),
        "series_id": result.series_id,
        "simulation_count": 0,
    }


def test_render_phase_art_series_cli_normalizes_preflight_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_phase_art_series",
        Mock(side_effect=ValueError("stale quartz parity")),
        raising=False,
    )

    status = main(
        [
            "render-phase-art-series",
            "--recipe",
            "series.yml",
            "--parity-root",
            "parity",
            "--ice-standard-reference",
            "ice-standard",
            "--output",
            "out",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == (
        "phase-art-series finite-work phases=5 new_bundle_count=9 "
        "comparison_cells=10 simulation_count=0 "
        "orientation_bunge_deg=17,31,43\n"
        "phase art series render failed: stale quartz parity\n"
    )
    assert "Traceback" not in captured.err


def test_render_phase_art_orientation_gallery_help_describes_gallery_inputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit, match="0"):
        main(["render-phase-art-orientation-gallery", "--help"])

    help_text = capsys.readouterr().out
    assert "fifteen-cell phase orientation gallery" in help_text
    assert "--recipe" in help_text
    assert "--parity-root" in help_text
    assert "--output" in help_text


def test_render_phase_art_orientation_gallery_cli_emits_finite_work_and_publication_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}
    result = SimpleNamespace(
        path=tmp_path / "phase-art-orientation-gallery-0123456789abcdef",
        cell_bundles=tuple(
            SimpleNamespace(run_id=f"gallery-cell-{index:02d}-0123456789abcdef")
            for index in range(15)
        ),
        comparison_id="orientation-gallery-sheet-0123456789abcdef",
        comparison_sheet=(
            tmp_path
            / "phase-art-orientation-gallery-0123456789abcdef"
            / "orientation-gallery-sheet-0123456789abcdef"
            / "comparison.png"
        ),
        ledger_path=(
            tmp_path
            / "phase-art-orientation-gallery-0123456789abcdef"
            / "orientation-gallery-sheet-0123456789abcdef"
            / "orientation-gallery-ledger.json"
        ),
        simulation_count=0,
        manifest_sha256="e" * 64,
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_phase_art_orientation_gallery",
        lambda **kwargs: observed.update(kwargs) or result,
        raising=False,
    )

    status = main(
        [
            "render-phase-art-orientation-gallery",
            "--recipe",
            "recipes/art/five-phase-standard-orientation-gallery.yml",
            "--parity-root",
            "/tmp/parity",
            "--output",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    assert observed == {
        "recipe_path": "recipes/art/five-phase-standard-orientation-gallery.yml",
        "parity_root": "/tmp/parity",
        "output_root": str(tmp_path),
    }
    assert captured.err == (
        "phase-art-orientation-gallery finite-work phases=5 orientations=3 cells=15 "
        "simulation_count=0\n"
    )
    assert json.loads(captured.out) == {
        "cell_count": 15,
        "comparison_id": result.comparison_id,
        "comparison_sheet": str(result.comparison_sheet),
        "ledger_path": str(result.ledger_path),
        "manifest_sha256": result.manifest_sha256,
        "path": str(result.path),
        "simulation_count": 0,
    }


def test_render_phase_art_orientation_gallery_cli_normalizes_preflight_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_phase_art_orientation_gallery",
        Mock(side_effect=ValueError("stale quartz parity")),
        raising=False,
    )

    status = main(
        [
            "render-phase-art-orientation-gallery",
            "--recipe",
            "gallery.yml",
            "--parity-root",
            "parity",
            "--output",
            "out",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == (
        "phase-art-orientation-gallery finite-work phases=5 orientations=3 cells=15 "
        "simulation_count=0\n"
        "phase art orientation gallery render failed: stale quartz parity\n"
    )
    assert "Traceback" not in captured.err


def test_render_ice_tattoo_cli_forwards_strict_inputs_and_emits_exact_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {}
    result = SimpleNamespace(
        run_id="ice-tattoo-run-0123456789abcdef",
        path=tmp_path / "ice-tattoo-run-0123456789abcdef",
        catalog_id="art-band-catalog-fedcba9876543210",
        selection_id="tattoo-selection-0123456789abcdef",
        geometry_id="tattoo-geometry-fedcba9876543210",
        treatment="primary",
        manifest_sha256="b" * 64,
    )
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_ice_tattoo",
        lambda **kwargs: observed.update(kwargs) or result,
        raising=False,
    )

    status = main(
        [
            "render-ice-tattoo",
            "--catalog",
            "/tmp/ice-art-catalog/art-band-catalog.json",
            "--recipe",
            "recipes/art/ice-ih-tattoo.yml",
            "--selection-manifest",
            "recipes/art/ice-ih-reviewed-selection-v2.yml",
            "--output",
            "/tmp/ice-tattoo",
            "--treatment",
            "primary",
        ]
    )

    assert status == 0
    assert observed == {
        "catalog_path": "/tmp/ice-art-catalog/art-band-catalog.json",
        "recipe_path": "recipes/art/ice-ih-tattoo.yml",
        "selection_manifest_path": "recipes/art/ice-ih-reviewed-selection-v2.yml",
        "output_root": "/tmp/ice-tattoo",
        "treatment": "primary",
    }
    assert json.loads(capsys.readouterr().out) == {
        "catalog_id": result.catalog_id,
        "geometry_id": result.geometry_id,
        "manifest_sha256": result.manifest_sha256,
        "path": str(result.path),
        "run_id": result.run_id,
        "selection_id": result.selection_id,
        "treatment": "primary",
    }


def test_render_ice_tattoo_cli_normalizes_graywash_gate_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "kikuchi_lab.workflows.render_ice_tattoo",
        Mock(side_effect=ValueError("graywash requires accepted primary geometry")),
        raising=False,
    )

    status = main(
        [
            "render-ice-tattoo",
            "--catalog",
            "catalog.json",
            "--recipe",
            "recipe.yml",
            "--output",
            "out",
            "--treatment",
            "graywash",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == (
        "ice tattoo render failed: graywash requires accepted primary geometry\n"
    )
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

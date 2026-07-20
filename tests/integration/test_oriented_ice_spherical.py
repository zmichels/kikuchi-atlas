from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.spherical_intensity.orientation import load_oriented_spherical_recipe
from kikuchi_lab.workflows import oriented_spherical as workflow


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/spherical/ice-ih-oriented-s2-proof.yml"

FIGURE_NAMES = {
    "identity-vs-oriented-upper.png",
    "oriented-lower.png",
    "oriented-sphere-front.png",
    "oriented-sphere-rear.png",
    "oriented-upper.png",
    "orientation-axes.png",
}
STAGES = ("simulation", "s2_mapping", "presentation", "figures", "publication")

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


def test_real_ice_smoke_builds_both_orientations_and_all_views(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    result = workflow.render_oriented_spherical_master(
        recipe_path=RECIPE,
        output_root=tmp_path,
        profile="smoke",
    )

    assert result.smoke is not None
    assert result.review is None
    assert result.smoke.path.is_dir()
    assert set(result.smoke.figure_names) == FIGURE_NAMES
    assert result.smoke.source_half_size == 32
    assert result.smoke.elapsed_seconds < 180

    stderr = capsys.readouterr().err
    stage_lines = [line for line in stderr.splitlines() if line.startswith("oriented-spherical ")]
    assert [line.split("stage=", 1)[1].split()[0] for line in stage_lines] == list(STAGES)
    assert all("profile=smoke" in line and "elapsed_seconds=" in line for line in stage_lines)


def test_review_runs_and_publishes_smoke_first(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, Path]] = []
    fake_result = object()

    def fake_run_profile(**kwargs):
        calls.append((kwargs["profile_name"], kwargs["output_root"]))
        return fake_result

    monkeypatch.setattr(workflow, "_run_profile", fake_run_profile)

    result = workflow.render_oriented_spherical_master(
        recipe_path=RECIPE,
        output_root=tmp_path,
        profile="review",
    )

    assert calls == [("smoke", tmp_path / "smoke"), ("review", tmp_path / "review")]
    assert result.smoke is fake_result
    assert result.review is fake_result


def test_invalid_profile_is_rejected_before_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        workflow,
        "_run_profile",
        lambda **kwargs: calls.append(kwargs["profile_name"]),
    )

    with pytest.raises(ValueError, match="oriented profile must be smoke or review"):
        workflow.render_oriented_spherical_master(
            recipe_path=RECIPE,
            output_root=tmp_path,
            profile="acceptance",  # type: ignore[arg-type]
        )

    assert calls == []


def test_deadline_reports_the_profile_that_exceeded_its_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow.time, "monotonic", lambda: 13.01)
    check = workflow._deadline(10.0, 3, "smoke")

    with pytest.raises(
        workflow.OrientedSphericalTimeoutError,
        match="oriented spherical smoke exceeded 3 seconds",
    ):
        check()


def test_materialized_source_is_both_hemisphere_identity_at_requested_bounds() -> None:
    oriented = load_oriented_spherical_recipe(RECIPE, profile="review")

    source_recipe, base, spherical_path, base_path = workflow._materialize_source_recipes(
        RECIPE,
        oriented,
    )

    assert spherical_path == (RECIPE.parent / oriented.source_spherical_recipe).resolve()
    assert base_path == (spherical_path.parent / source_recipe.source_kinematical_recipe).resolve()
    assert source_recipe.profile.name == "acceptance"
    assert source_recipe.profile.half_size == 512
    assert source_recipe.profile.timeout_seconds == 600
    assert base.hemisphere == "both"
    assert base.orientation.euler_bunge_deg == (0.0, 0.0, 0.0)
    assert base.half_size == 512
    assert base.figure_size_px == 2400


def test_materialized_source_rejects_single_hemisphere_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oriented = load_oriented_spherical_recipe(RECIPE, profile="smoke")
    spherical_path = (RECIPE.parent / oriented.source_spherical_recipe).resolve()
    source_recipe = workflow.load_spherical_intensity_recipe(spherical_path, profile="smoke")
    base_path = (spherical_path.parent / source_recipe.source_kinematical_recipe).resolve()
    base = replace(load_kinematical_recipe(base_path), hemisphere="upper")
    monkeypatch.setattr(workflow, "load_kinematical_recipe", lambda path: base)

    with pytest.raises(ValueError, match="oriented source master must contain both hemispheres"):
        workflow._materialize_source_recipes(RECIPE, oriented)

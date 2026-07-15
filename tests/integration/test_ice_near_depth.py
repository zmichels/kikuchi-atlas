from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kikuchi_lab.near_depth import load_near_depth_recipe
from kikuchi_lab.workflows.near_depth import render_kinematical_depth


ROOT = Path(__file__).parents[2]
TREATMENT_RECIPE = (
    ROOT / "recipes" / "presentation" / "ice-ih-near-depth-stepped.yml"
)
BASE_RECIPE = ROOT / "recipes" / "kinematical" / "ice-ih-oxygen-quiet-proof.yml"


def test_workflow_rejects_mismatched_base_recipe_before_simulation(
    tmp_path: Path,
) -> None:
    (tmp_path / "presentation").mkdir()
    (tmp_path / "kinematical").mkdir()
    (tmp_path / "kinematical" / "base.yml").write_text(
        BASE_RECIPE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    payload = yaml.safe_load(TREATMENT_RECIPE.read_text(encoding="utf-8"))
    payload["source_kinematical_recipe"] = "../kinematical/base.yml"
    payload["expected_kinematical_recipe_id"] = "recipe-wrong"
    treatment_path = tmp_path / "presentation" / "depth.yml"
    treatment_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="expected base recipe ID"):
        render_kinematical_depth(recipe_path=treatment_path, output_root=tmp_path / "runs")


def test_workflow_orchestrates_exact_overlap_render_and_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kikuchi_lab.workflows.near_depth as module

    treatment = load_near_depth_recipe(TREATMENT_RECIPE)
    simulation = SimpleNamespace(
        master_stereographic=SimpleNamespace(intensity=SimpleNamespace(shape=(2, 33, 33)))
    )
    context = SimpleNamespace(master_simulator=SimpleNamespace(reflectors="reflectors"))
    overlap = object()
    render = SimpleNamespace(figures={"depth.png": b"png"})
    observed: dict[str, object] = {}

    monkeypatch.setattr(module, "simulate_kinematical_arrays", lambda source, base: (simulation, context))
    monkeypatch.setattr(
        module,
        "compute_overlap_field",
        lambda reflectors, **kwargs: observed.update(
            {"reflectors": reflectors, "overlap_kwargs": kwargs}
        ) or overlap,
    )
    monkeypatch.setattr(
        module,
        "render_quiet_control",
        lambda context, simulation, base, *, figure_size_px: observed.update(
            {"quiet_size": figure_size_px}
        ) or b"quiet",
    )
    monkeypatch.setattr(
        module,
        "render_near_depth",
        lambda context, simulation, base, treatment, overlap, quiet, *, figure_size_px: (
            observed.update({"render_size": figure_size_px, "quiet": quiet}) or render
        ),
    )
    monkeypatch.setattr(
        module,
        "write_near_depth_bundle",
        lambda output, render, overlap, simulation, treatment, base, source: SimpleNamespace(
            run_id="near-depth-run-0123456789abcdef",
            path=Path(output) / "near-depth-run-0123456789abcdef",
            manifest_sha256="a" * 64,
        ),
    )

    result = render_kinematical_depth(
        recipe_path=TREATMENT_RECIPE,
        output_root=tmp_path / "runs",
        figure_size_px=480,
    )

    assert observed == {
        "reflectors": "reflectors",
        "overlap_kwargs": {
            "size": 33,
            "relative_factor": treatment.overlap_relative_factor,
            "weight_exponent": treatment.weight_exponent,
            "normalization_percentile": treatment.normalization_percentile,
        },
        "quiet_size": 480,
        "render_size": 480,
        "quiet": b"quiet",
    }
    assert result.run_id == "near-depth-run-0123456789abcdef"
    assert result.figure_names == ("depth.png",)
    assert result.treatment_recipe_id == treatment.recipe_id
    assert result.base_recipe_id == treatment.expected_kinematical_recipe_id

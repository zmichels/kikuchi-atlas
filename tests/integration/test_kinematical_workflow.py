from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from kikuchi_lab.workflows.kinematical import render_kinematical


ROOT = Path(__file__).parents[2]
SOURCE_ROOT = ROOT / "phases/forsterite"
RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"
FIGURES = (
    "etched-master-balanced.png",
    "etched-master-quiet.png",
    "kinematical-detector-overlay.png",
    "kinematical-spherical-bands.png",
    "kinematical-stereographic-bands.svg",
    "reflector-selection.png",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def small_recipe(tmp_path: Path) -> Path:
    source_directory = tmp_path / "source"
    source_directory.mkdir(parents=True)
    for name in ("source.yml", "COD-9000319.cif"):
        (source_directory / name).write_bytes((SOURCE_ROOT / name).read_bytes())

    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    payload["source_record"] = "source/source.yml"
    payload["master"]["half_size"] = 8
    payload["detector"]["shape"] = [24, 32]
    payload["figure_size_px"] = 128
    recipe_path = tmp_path / "kinematical.yml"
    recipe_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return recipe_path


@pytest.fixture(scope="module")
def reproduced_runs(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("kinematical-workflow")
    first_recipe = small_recipe(root / "first-input")
    relocated_recipe = small_recipe(root / "relocated-input")
    existing_final = root / "existing-final-run"
    existing_final.mkdir()
    final_manifest = existing_final / "manifest.json"
    final_manifest.write_text('{"schema_version":2,"sentinel":"final"}', encoding="utf-8")
    first = render_kinematical(recipe_path=first_recipe, output_root=root / "first-runs")
    second = render_kinematical(recipe_path=relocated_recipe, output_root=root / "second-runs")
    return first, second, final_manifest


def test_render_kinematical_materializes_the_standalone_workflow_result(
    reproduced_runs,
) -> None:
    first, _, final_manifest = reproduced_runs

    assert first.path.name == first.run_id
    assert first.recipe_id.startswith("recipe-")
    assert first.master_reflector_count > 0
    assert first.figure_names == FIGURES
    assert (first.path / "figures/etched-master-quiet.png").is_file()
    assert final_manifest.read_text(encoding="utf-8") == ('{"schema_version":2,"sentinel":"final"}')


def test_relocated_recipe_and_source_reproduce_identity_products_and_manifest(
    reproduced_runs,
) -> None:
    first, second, _ = reproduced_runs

    assert first.run_id == second.run_id
    first_manifest_path = first.path / "manifest.json"
    second_manifest_path = second.path / "manifest.json"
    assert first_manifest_path.read_bytes() == second_manifest_path.read_bytes()
    manifest = json.loads(first_manifest_path.read_text(encoding="utf-8"))
    for relative, record in manifest["files"].items():
        assert record["sha256"] == _sha256(first.path / relative)
        assert record["sha256"] == _sha256(second.path / relative)
    for name in (
        "kinematical-master-stereographic.npy",
        "kinematical-master-lambert.npy",
        "kinematical-detector.npy",
    ):
        np.testing.assert_array_equal(
            np.load(first.path / "products" / name),
            np.load(second.path / "products" / name),
        )

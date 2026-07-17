import json
import os
from pathlib import Path
import subprocess

import pytest

from kikuchi_lab.habit.crystallography import expand_habit_planes
from kikuchi_lab.habit.geometry import solve_convex_habit
from kikuchi_lab.habit.parity import compare_mtex_reference
from kikuchi_lab.habit.recipes import load_habit_recipe


ROOT = Path(__file__).parents[2]


def _quartz_polygon():
    recipe = load_habit_recipe(ROOT / "recipes/habits/quartz-mtex-example.yml")
    _, planes = expand_habit_planes(recipe)
    return solve_convex_habit(planes)


def _scientific_geometry_fields(path: Path) -> dict[str, object]:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    return {
        key: ledger[key]
        for key in ("schema", "mtex", "frame", "vertices", "faces")
    }


def test_quartz_python_geometry_passes_mtex_611_contract():
    report = compare_mtex_reference(
        _quartz_polygon(), ROOT / "reference/habits/quartz-mtex-6.1.1.json"
    )

    assert report.passed is True
    assert report.python_vertex_count == report.mtex_vertex_count == 32
    assert report.python_face_count == report.mtex_face_count == 18
    assert report.vertex_hausdorff <= 1e-7
    assert report.relative_volume_difference <= 1e-6
    assert report.maximum_face_normal_angle_rad <= 1e-7
    assert report.visible_family_labels == ("m", "r", "z")


def test_parity_names_vertex_hausdorff_when_ledger_vertex_is_perturbed(
    tmp_path: Path,
):
    source = ROOT / "reference/habits/quartz-mtex-6.1.1.json"
    ledger = json.loads(source.read_text(encoding="utf-8"))
    ledger["vertices"][0][0] += 1e-4
    perturbed = tmp_path / "perturbed.json"
    perturbed.write_text(json.dumps(ledger) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"MTEX parity failed: .*vertex_hausdorff"):
        compare_mtex_reference(_quartz_polygon(), perturbed)


@pytest.mark.mtex
def test_mtex_reference_regeneration_matches_committed_geometry(tmp_path: Path):
    mtex_root = os.environ.get("KIKUCHI_MTEX_ROOT")
    matlab_bin = os.environ.get("MATLAB_BIN")
    if not mtex_root or not matlab_bin:
        pytest.skip("KIKUCHI_MTEX_ROOT and MATLAB_BIN are required")
    generated = tmp_path / "quartz-mtex.json"
    command = (
        "addpath('scripts'); export_mtex_habit_reference("
        "'reference/habits/quartz-mtex-request.json',"
        f"'{generated.as_posix()}')"
    )
    subprocess.run(
        [matlab_bin, "-batch", command],
        cwd=ROOT,
        env={**os.environ, "KIKUCHI_MTEX_ROOT": mtex_root},
        check=True,
    )
    assert _scientific_geometry_fields(generated) == _scientific_geometry_fields(
        ROOT / "reference/habits/quartz-mtex-6.1.1.json"
    )

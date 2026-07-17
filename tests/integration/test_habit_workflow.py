import hashlib
import json
from pathlib import Path

import pytest
import trimesh

from kikuchi_lab.habit.workflow import build_habit


ROOT = Path(__file__).parents[2]


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_quartz_build_is_atomic_reproducible_and_complete(tmp_path: Path):
    recipe = ROOT / "recipes/habits/quartz-mtex-example.yml"
    first = build_habit(recipe, tmp_path / "first")
    second = build_habit(recipe, tmp_path / "second")

    assert first.build_id == second.build_id
    assert _tree_hashes(first.path) == _tree_hashes(second.path)
    assert {path.name for path in first.path.iterdir()} == {
        "quartz-habit.stl",
        "quartz-habit-preview.png",
        "habit-manifest.json",
        "mesh-validation.json",
    }
    manifest = json.loads(first.manifest.read_text(encoding="utf-8"))
    assert manifest["units"] == "millimetre"
    assert manifest["recipe_id"].startswith("habit-recipe-")
    assert manifest["visible_family_labels"] == ["m", "r", "z"]
    assert manifest["inactive_plane_count"] == 12
    assert manifest["phase"]["frame"] == "X||a*, Y||cross(c,a*), Z||c"
    assert manifest["phase_source"]["cif_sha256"] == (
        "10dd04655c03f6b152897a5e2d863e42892bd84561cb6dfc1febd86271e70b57"
    )
    assert manifest["orientation_matrix"] == [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    assert len(manifest["expanded_planes"]) == 30
    assert len(manifest["visible_polygons"]) == 18
    assert len(manifest["inactive_plane_ids"]) == 12
    assert len(manifest["triangle_to_polygon"]) == manifest["triangle_count"]
    assert manifest["validation_report"] == "mesh-validation.json"
    assert set(manifest["files"]) == {
        "mesh-validation.json",
        "quartz-habit-preview.png",
        "quartz-habit.stl",
    }
    for relative, record in manifest["files"].items():
        payload = (first.path / relative).read_bytes()
        assert record == {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    loaded = trimesh.load_mesh(first.stl, process=False)
    loaded.merge_vertices()
    assert loaded.is_volume and loaded.body_count == 1
    assert loaded.extents.max() == pytest.approx(60.0, abs=1e-8)


def test_failed_build_removes_partial_bundle(tmp_path: Path, monkeypatch):
    import kikuchi_lab.habit.workflow as workflow

    recipe = ROOT / "recipes/habits/quartz-mtex-example.yml"

    def fail_preview(*_args):
        raise RuntimeError("preview failed")

    monkeypatch.setattr(workflow, "write_habit_preview", fail_preview)
    with pytest.raises(RuntimeError, match="preview failed"):
        build_habit(recipe, tmp_path)

    assert list(tmp_path.glob("*.partial")) == []
    assert list(tmp_path.iterdir()) == []

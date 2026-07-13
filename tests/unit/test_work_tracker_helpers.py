from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


REPO_ROOT = Path(__file__).parents[2]


def _frontmatter(path: Path) -> dict:
    _, raw_frontmatter, _ = path.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(raw_frontmatter)


def test_new_work_item_updates_parent_and_child_links_symmetrically(tmp_path):
    work_root = tmp_path / "docs" / "work"
    shutil.copytree(REPO_ROOT / "docs" / "work", work_root)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/new_work_item.py",
            "Inspect a New Diagnostic",
            "--root",
            str(work_root),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    child_path = Path(result.stdout.strip())
    child = _frontmatter(child_path)
    parent = _frontmatter(work_root / "KIKU-F001.md")
    assert child["parent"] == "KIKU-F001"
    assert child["id"] in parent["children"]

    subprocess.run(
        [sys.executable, "scripts/validate_work_items.py", "--root", str(work_root)],
        cwd=REPO_ROOT,
        check=True,
    )


@pytest.mark.parametrize(
    "title",
    [
        "Inspect: detector geometry",
        "Inspect # indexed bands",
        'Inspect "quoted" evidence',
        "Inspect first line\nand second line",
    ],
)
def test_new_work_item_safely_serializes_yaml_titles(tmp_path, title):
    work_root = tmp_path / "docs" / "work"
    shutil.copytree(REPO_ROOT / "docs" / "work", work_root)

    result = subprocess.run(
        [sys.executable, "scripts/new_work_item.py", title, "--root", str(work_root)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    child_path = Path(result.stdout.strip())
    assert _frontmatter(child_path)["title"] == title
    subprocess.run(
        [sys.executable, "scripts/validate_work_items.py", "--root", str(work_root)],
        cwd=REPO_ROOT,
        check=True,
    )

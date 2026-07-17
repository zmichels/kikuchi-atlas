from __future__ import annotations

import os
import subprocess
import sys


def test_relief_imports_do_not_change_selected_matplotlib_backend():
    script = """
import matplotlib
matplotlib.use('svg', force=True)
before = matplotlib.get_backend()
import kikuchi_lab.relief
import kikuchi_lab.relief.recipes
import kikuchi_lab.relief.field
import kikuchi_lab.relief.topology
import kikuchi_lab.relief.mapping
import kikuchi_lab.relief.mesh
import kikuchi_lab.relief.workflow
after = matplotlib.get_backend()
assert before == after, (before, after)
"""
    environment = dict(os.environ)
    environment.pop("MPLBACKEND", None)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr

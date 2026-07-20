from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]
GALLERY_ROOT = Path("local/phase-general-direct-reflector-art/orientation-gallery")
PARITY_ROOT = Path("local/phase-general-direct-reflector-art/parity")


def test_retained_orientation_gallery_verifier_reports_the_stable_inventory() -> None:
    if not (ROOT / PARITY_ROOT).is_dir():
        pytest.skip("orientation-gallery parity reports are machine-local review artifacts")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_orientation_gallery.py",
            "--gallery-root",
            str(GALLERY_ROOT),
            "--parity-root",
            str(PARITY_ROOT),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "orientation-gallery-probe PASS "
        "root=local/phase-general-direct-reflector-art/orientation-gallery "
        "cells=15 artifacts_checked=137 parity_reports=5\n"
    )

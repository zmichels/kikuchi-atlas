from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


@pytest.mark.parametrize("phase_slug", ["ice-ih", "forsterite"])
def test_direct_catalog_workflow_reports_zero_simulations(
    phase_slug: str,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.workflows.direct_art_catalog import build_direct_art_catalog

    result = build_direct_art_catalog(
        recipe_path=ROOT / f"recipes/reflectors/{phase_slug}-art-bands.yml",
        output_root=tmp_path / phase_slug,
    )

    assert (result.path / "art-band-catalog.json").is_file()
    assert (result.path / "reflector-evidence.npz").is_file()
    assert result.catalog_id.startswith("art-band-catalog-")
    assert result.evidence_id.startswith("reflector-evidence-")
    assert result.member_count >= result.eligible_member_count >= 11
    assert result.simulation_count == 0
    manifest = json.loads((result.path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_identity"]["catalog_id"] == result.catalog_id
    assert manifest["run_identity"]["evidence_id"] == result.evidence_id
    stderr = capsys.readouterr().err
    assert "direct-art-catalog finite-work simulation_count=0" in stderr
    expected_name = {
        "ice-ih": "ice-Ih-oxygen-sublattice",
        "forsterite": "forsterite",
    }[phase_slug]
    assert f"phase={expected_name}" in stderr


def test_direct_catalog_workflow_exports_public_contract() -> None:
    import kikuchi_lab.workflows as workflows
    from kikuchi_lab.workflows.direct_art_catalog import (
        DirectArtCatalogResult,
        build_direct_art_catalog,
    )

    assert workflows.DirectArtCatalogResult is DirectArtCatalogResult
    assert workflows.build_direct_art_catalog is build_direct_art_catalog

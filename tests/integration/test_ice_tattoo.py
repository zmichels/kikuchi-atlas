from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]
CATALOG_RECIPE = ROOT / "recipes/art/ice-ih-band-catalog.yml"
TATTOO_RECIPE = ROOT / "recipes/art/ice-ih-tattoo.yml"
EXPECTED_MEMBERS = (
    "art-band-member-239b7cb5e485d442",
    "art-band-member-d38532aafcf1ed7f",
    "art-band-member-3cb4167967631dcc",
    "art-band-member-0a414c19f6ab8845",
    "art-band-member-b4647bcd2cbca9f6",
    "art-band-member-b67c65e3bc542c16",
    "art-band-member-263af8004ec3e279",
    "art-band-member-ef3609aba836233b",
    "art-band-member-4fdb2612d72a02c1",
    "art-band-member-2413565c4ba2c58d",
    "art-band-member-c38e4b2859f9646d",
)

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


def test_real_bounded_ice_catalog_publishes_primary_tattoo(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.workflows.ice_art_catalog import build_ice_art_catalog
    from kikuchi_lab.workflows.ice_tattoo import render_ice_tattoo

    catalog = build_ice_art_catalog(
        recipe_path=CATALOG_RECIPE,
        output_root=tmp_path / "catalog",
    )
    result = render_ice_tattoo(
        catalog_path=catalog.path / "art-band-catalog.json",
        recipe_path=TATTOO_RECIPE,
        output_root=tmp_path / "tattoo",
        treatment="primary",
    )

    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    geometry = json.loads((result.path / "path-geometry.json").read_text())
    selection = json.loads((result.path / "band-selection-ledger.json").read_text())
    diagnostic = json.loads((result.path / "stroke-gap-diagnostic.json").read_text())
    assert result.catalog_id == catalog.catalog_id
    assert result.geometry_id == geometry["geometry_id"]
    assert result.treatment == "primary"
    assert result.manifest_sha256 == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert manifest["run_identity"]["catalog_id"] == catalog.catalog_id
    assert tuple(path["member_id"] for path in selection["selected_paths"]) == (
        EXPECTED_MEMBERS
    )
    assert len(geometry["content"]["paths"]) == 11
    assert geometry["content"]["boundary"]["outer_diameter_mm"] == 132.0
    assert geometry["content"]["boundary"]["width_mm"] == 2.2
    assert [path["width_mm"] for path in geometry["content"]["paths"]] == [
        4.8,
        4.2,
        3.6,
        3.1,
        2.5,
        2.2,
        1.9,
        1.6,
        1.2,
        1.0,
        0.8,
    ]
    assert diagnostic["validation"]["status"] == "passed"
    assert diagnostic["validation"]["complete_hemisphere_boundary"] == "passed"
    stderr = capsys.readouterr().err
    assert "ice-art-catalog finite-work profile=smoke source_half_size=32" in stderr
    assert "profile=review" not in stderr


def test_graywash_hard_fails_before_output_until_primary_acceptance(
    tmp_path: Path,
) -> None:
    from kikuchi_lab.workflows.ice_tattoo import render_ice_tattoo

    output_root = tmp_path / "graywash"
    with pytest.raises(
        ValueError,
        match="^graywash requires accepted primary geometry$",
    ):
        render_ice_tattoo(
            catalog_path=tmp_path / "not-read.json",
            recipe_path=TATTOO_RECIPE,
            output_root=output_root,
            treatment="graywash",
        )

    assert not output_root.exists()

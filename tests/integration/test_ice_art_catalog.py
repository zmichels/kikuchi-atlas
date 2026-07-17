from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/art/ice-ih-band-catalog.yml"

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


def test_real_ice_catalog_uses_smoke_bounds_and_publishes_claims(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.catalog import load_art_band_catalog
    from kikuchi_lab.workflows.ice_art_catalog import build_ice_art_catalog

    result = build_ice_art_catalog(recipe_path=RECIPE, output_root=tmp_path)
    ledger = json.loads((result.path / "catalog-ledger.json").read_text(encoding="utf-8"))
    catalog = load_art_band_catalog(result.path / "art-band-catalog.json")

    assert result.path.is_dir()
    assert result.member_count > 0
    assert result.catalog_id == ledger["catalog"]["catalog_id"]
    assert set(ledger["catalog"]["globe_cohort_member_counts"]) == {
        "1",
        "2",
        "3",
        "4",
    }
    assert all(ledger["catalog"]["globe_cohort_member_counts"].values())
    assert ledger["claim_boundaries"]["product_class"] == "science_art"
    assert ledger["claim_boundaries"]["scientific_claim"] == "presentation_only"
    assert catalog.eligibility_min_weight == 0.08
    assert sum(member.tattoo_eligible for member in catalog.members) == 144

    stderr = capsys.readouterr().err
    assert "ice-art-catalog finite-work profile=smoke source_half_size=32" in stderr
    stage_lines = [
        line for line in stderr.splitlines() if line.startswith("ice-art-catalog stage=")
    ]
    assert [
        (line.split("stage=", 1)[1].split()[0], line.split("event=", 1)[1].split()[0])
        for line in stage_lines
    ] == [
        ("simulation", "start"),
        ("simulation", "finish"),
        ("presentation", "start"),
        ("presentation", "finish"),
        ("catalog", "start"),
        ("catalog", "finish"),
        ("publication", "start"),
        ("publication", "finish"),
    ]


def test_forged_presentation_recipe_id_is_rejected_before_simulation_or_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import kikuchi_lab.workflows.ice_art_catalog as workflow

    recipe_root = tmp_path / "recipes"
    for directory in ("art", "spherical", "kinematical", "presentation"):
        (recipe_root / directory).mkdir(parents=True, exist_ok=True)

    copies = {
        recipe_root / "art/catalog.yml": RECIPE,
        recipe_root / "spherical/oriented.yml": (
            ROOT / "recipes/spherical/ice-ih-oriented-s2-proof.yml"
        ),
        recipe_root / "spherical/source.yml": (
            ROOT / "recipes/spherical/ice-ih-s2-intensity.yml"
        ),
        recipe_root / "kinematical/base.yml": (
            ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
        ),
        recipe_root / "presentation/treatment.yml": (
            ROOT / "recipes/presentation/ice-ih-near-depth-stepped-field-led.yml"
        ),
    }
    for destination, source in copies.items():
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    catalog_payload = yaml.safe_load((recipe_root / "art/catalog.yml").read_text())
    catalog_payload["source_oriented_recipe"] = "../spherical/oriented.yml"
    (recipe_root / "art/catalog.yml").write_text(yaml.safe_dump(catalog_payload))
    oriented_payload = yaml.safe_load((recipe_root / "spherical/oriented.yml").read_text())
    oriented_payload["source_spherical_recipe"] = "source.yml"
    oriented_payload["presentation_recipe"] = "../presentation/treatment.yml"
    (recipe_root / "spherical/oriented.yml").write_text(yaml.safe_dump(oriented_payload))
    spherical_payload = yaml.safe_load((recipe_root / "spherical/source.yml").read_text())
    spherical_payload["source_kinematical_recipe"] = "../kinematical/base.yml"
    (recipe_root / "spherical/source.yml").write_text(yaml.safe_dump(spherical_payload))
    presentation_payload = yaml.safe_load(
        (recipe_root / "presentation/treatment.yml").read_text()
    )
    presentation_payload["expected_kinematical_recipe_id"] = "recipe-forged"
    (recipe_root / "presentation/treatment.yml").write_text(
        yaml.safe_dump(presentation_payload)
    )
    calls: list[object] = []
    monkeypatch.setattr(
        workflow,
        "simulate_kinematical_arrays",
        lambda *_args: calls.append(object()),
    )
    output_root = tmp_path / "runs"

    with pytest.raises(ValueError, match="presentation recipe.*tracked Ice base recipe"):
        workflow.build_ice_art_catalog(
            recipe_path=recipe_root / "art/catalog.yml",
            output_root=output_root,
        )

    assert calls == []
    assert not output_root.exists()

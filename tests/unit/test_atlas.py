from __future__ import annotations

from pathlib import Path

from kikuchi_lab.atlas import build_atlas, load_phase_registry


ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "docs/atlas/PHASE_REGISTRY.yml"
PRODUCTS = ROOT / "docs/products/ARTIFACT_CATALOG.yml"


def test_atlas_registry_has_exact_family_references_not_ambiguous_family_labels() -> None:
    phases = {phase.slug: phase for phase in load_phase_registry(REGISTRY)}

    assert set(phases) == {
        "forsterite",
        "ice-ih",
        "quartz",
        "zircon",
        "titanite",
        "diamond",
        "plagioclase-an52",
        "muscovite-2m1",
        "diopside",
    }
    assert phases["plagioclase-an52"].source_status == "candidate-reference"
    assert phases["plagioclase-an52"].candidate_reference["label"] == (
        "COD 8103560, intermediate plagioclase An52"
    )
    assert phases["muscovite-2m1"].candidate_reference["promotion_trigger"]
    assert phases["diopside"].family == "clinopyroxene"


def test_atlas_builds_browsable_index_and_phase_pages(tmp_path: Path) -> None:
    result = build_atlas(
        registry_path=REGISTRY,
        product_catalog_path=PRODUCTS,
        output_root=tmp_path / "site",
    )

    assert result.phase_count == 9
    assert result.product_count == 17
    assert result.index_path.is_file()
    index = result.index_path.read_text(encoding="utf-8")
    assert "Kikuchi Atlas" in index
    assert "Plagioclase (An52 reference)" in index
    assert "candidate-reference" in index
    assert (tmp_path / "site/phases/forsterite.html").is_file()
    forsterite = (tmp_path / "site/phases/forsterite.html").read_text(encoding="utf-8")
    assert forsterite.count('<article class="card">') == 6
    diopside = (tmp_path / "site/phases/diopside.html").read_text(encoding="utf-8")
    assert "COD 1000007, diopside at 1 atm" in diopside
    assert "No product published yet" in diopside

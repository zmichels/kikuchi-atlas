from __future__ import annotations

from pathlib import Path

from kikuchi_lab.atlas import build_atlas, load_phase_registry, load_product_registry


ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "docs/atlas/PHASE_REGISTRY.yml"
PRODUCTS = ROOT / "docs/atlas/PRODUCT_REGISTRY.yml"
ANCHORS = ROOT / "docs/products/ARTIFACT_CATALOG.yml"


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


def test_product_registry_models_individual_products_and_common_core_families() -> None:
    phases = load_phase_registry(REGISTRY)
    families, products = load_product_registry(PRODUCTS, phase_slugs={phase.slug for phase in phases})

    assert {family.identifier for family in families if family.coverage == "core"} == {
        "direct-reflector-template",
        "orientation-variation",
        "x-axis-motion",
        "reflector-ridge-globe",
    }
    assert "tattoo-template" not in {family.identifier for family in families}
    assert len(products) == 46
    assert all(product.is_available() for product in products)
    assert all("tattoo" not in product.identifier.lower() for product in products)
    assert all("tattoo" not in product.title.lower() for product in products)
    assert all("tattoo" not in family_id for product in products for family_id in product.family_ids)
    assert {
        product.identifier for product in products if product.hero
    } == {
        "forsterite-direct-standard",
        "ice-ih-direct-standard",
        "quartz-direct-standard",
        "zircon-direct-standard",
        "titanite-direct-standard",
        "diamond-x-axis-rotation",
    }


def test_atlas_builds_browsable_index_and_phase_pages(tmp_path: Path) -> None:
    result = build_atlas(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        anchor_catalog_path=ANCHORS,
        output_root=tmp_path / "site",
    )

    assert result.phase_count == 9
    assert result.product_count == 46
    assert result.index_path.is_file()
    index = result.index_path.read_text(encoding="utf-8")
    assert "Kikuchi Atlas" in index
    assert "Browse all 46 individual products" in index
    assert "Lead: Forsterite — standard hemisphere" in index
    assert "Plagioclase (An52 reference)" in index
    assert "candidate-reference" in index
    assert result.products_path.is_file()
    product_page = result.products_path.read_text(encoding="utf-8")
    assert 'id="product-search"' in product_page
    assert 'id="phase-filter"' in product_page
    assert 'id="family-filter"' in product_page
    assert product_page.count('class="card product-card"') == 46
    assert "tattoo" not in index.lower()
    assert "tattoo" not in product_page.lower()
    assert (tmp_path / "site/phases/forsterite.html").is_file()
    forsterite = (tmp_path / "site/phases/forsterite.html").read_text(encoding="utf-8")
    assert "Coverage table" in forsterite
    assert "open SVG" in forsterite
    assert "open MP4" in forsterite
    assert "open STL" in forsterite
    assert "Visual highlights" in forsterite
    assert forsterite.count('class="card highlight-card"') == 3
    assert "tattoo" not in forsterite.lower()
    assert "phases/phases/" not in forsterite
    assert forsterite.count('class="card product-card"') == 10
    assert "Visual product matrix" in forsterite
    assert "Coverage table" in forsterite
    assert forsterite.count('class="card matrix-card"') == 7
    assert forsterite.count('class="matrix-thumb"') >= 7
    assert 'data-family="direct-reflector-template"' in forsterite
    assert 'data-family="orientation-variation"' in forsterite
    for source_backed_phase in (
        "forsterite",
        "ice-ih",
        "quartz",
        "zircon",
        "titanite",
        "diamond",
    ):
        phase_html = (tmp_path / f"site/phases/{source_backed_phase}.html").read_text(encoding="utf-8")
        assert "Visual highlights" in phase_html
        assert 'class="card highlight-card"' in phase_html
        assert "tattoo" not in phase_html.lower()
    diopside = (tmp_path / "site/phases/diopside.html").read_text(encoding="utf-8")
    assert "COD 1000007, diopside at 1 atm" in diopside
    assert "blocked by source promotion" in diopside
    assert "Visual product matrix" in diopside
    assert diopside.count('class="card matrix-card"') == 7
    assert 'data-state="planned"' in diopside
    assert "No individual product published yet" in diopside

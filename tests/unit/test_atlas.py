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
    assert phases["plagioclase-an52"].source_status == "tracked-source"
    assert phases["plagioclase-an52"].source_record == "phases/plagioclase-an52/source.yml"
    assert phases["muscovite-2m1"].source_record == "phases/muscovite-2m1/source.yml"
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
    assert len(products) == 95
    assert all(product.is_available() for product in products)
    assert all("tattoo" not in product.identifier.lower() for product in products)
    assert all("tattoo" not in product.title.lower() for product in products)
    assert all("tattoo" not in family_id for product in products for family_id in product.family_ids)
    direct_reflector_products = [
        product
        for product in products
        if "direct-reflector-template" in product.family_ids
        and "orientation-variation" in product.family_ids
    ]
    assert all(product.preview_path is not None for product in direct_reflector_products)
    assert all(product.preview_path.suffix == ".png" for product in direct_reflector_products)
    assert {
        product.identifier for product in products if product.hero
    } == {
        "forsterite-direct-standard",
        "ice-ih-direct-standard",
        "quartz-direct-standard",
        "zircon-direct-standard",
        "titanite-direct-standard",
        "diamond-direct-standard",
        "plagioclase-an52-direct-standard",
        "muscovite-2m1-direct-standard",
        "diopside-direct-standard",
    }


def test_kinematical_extension_baseline_has_exact_nine_phase_coverage() -> None:
    phases = load_phase_registry(REGISTRY)
    _, products = load_product_registry(PRODUCTS, phase_slugs={phase.slug for phase in phases})

    expected = {
        "intensity-master": "kinematical-master",
        "depth-field-motion": "retained-near-depth-field",
        "intensity-relief-globe": "kinematical-intensity-relief",
    }
    for family_id, tier in expected.items():
        baseline = [
            product
            for product in products
            if product.family_ids == (family_id,) and product.tier == tier
        ]
        assert {product.phase_slugs for product in baseline} == {
            (phase.slug,) for phase in phases
        }
        assert all(product.is_available() for product in baseline)


def test_atlas_builds_browsable_index_and_phase_pages(tmp_path: Path) -> None:
    result = build_atlas(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        anchor_catalog_path=ANCHORS,
        output_root=tmp_path / "site",
    )

    assert result.phase_count == 9
    assert result.product_count == 95
    assert result.index_path.is_file()
    index = result.index_path.read_text(encoding="utf-8")
    assert "Kikuchi Atlas" in index
    assert "Browse by mineral or phase" in index
    assert "Browse by product type" in index
    assert 'class="phase-directory"' in index
    assert 'class="product-type-matrix"' in index
    phase_directory = index.split('<ul class="phase-directory">', 1)[1].split("</ul>", 1)[0]
    assert "<img" not in phase_directory
    assert "Plagioclase (An52 reference)" in index
    assert "candidate-reference" not in index
    assert 'href="phases/forsterite.html"' in index
    assert 'href="product-types/direct-reflector-orientation-set.html"' in index
    assert {path.stem for path in result.product_type_pages} == {
        "direct-reflector-orientation-set",
        "x-axis-motion",
        "reflector-ridge-globe",
        "intensity-master",
        "depth-field-motion",
        "intensity-relief-globe",
    }
    direct_type = tmp_path / "site/product-types/direct-reflector-orientation-set.html"
    assert direct_type.is_file()
    direct_type_html = direct_type.read_text(encoding="utf-8")
    assert "Direct-reflector orientation set" in direct_type_html
    assert "Available phases" in direct_type_html
    assert direct_type_html.count('class="card type-phase-card"') == 9
    globe_type = tmp_path / "site/product-types/reflector-ridge-globe.html"
    assert globe_type.is_file()
    assert globe_type.read_text(encoding="utf-8").count('class="card type-phase-card"') == 9
    assert result.products_path.is_file()
    product_page = result.products_path.read_text(encoding="utf-8")
    assert 'id="product-search"' in product_page
    assert 'id="phase-filter"' in product_page
    assert 'id="family-filter"' in product_page
    assert product_page.count('class="card product-card"') == 95
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
    assert forsterite.count('class="card product-card"') == 13
    assert "Visual product matrix" in forsterite
    assert "Coverage table" in forsterite
    assert forsterite.count('class="card matrix-card"') == 6
    assert forsterite.count('class="matrix-thumb"') >= 7
    assert forsterite.count('class="matrix-group"') == 2
    assert 'class="matrix-group" data-coverage="core"' in forsterite
    assert 'class="matrix-group" data-coverage="extension"' in forsterite
    assert 'data-family="direct-reflector-orientation-set"' in forsterite
    assert 'data-thumbnail-count="4"' in forsterite
    assert 'class="product-group" data-coverage="core"' in forsterite
    assert 'class="product-group" data-coverage="extension"' in forsterite
    assert '<div class="grid"><section class="product-group"' not in forsterite
    assert 'class="matrix-section" data-coverage="core"' in forsterite
    assert 'class="matrix-section" data-coverage="extension"' in forsterite
    assert forsterite.count('data-family="orientation-variation"') == 0
    assert '../product-types/direct-reflector-orientation-set.html' in forsterite
    for source_backed_phase in (
        "forsterite",
        "ice-ih",
        "quartz",
        "zircon",
        "titanite",
        "diamond",
        "plagioclase-an52",
        "muscovite-2m1",
        "diopside",
    ):
        phase_html = (tmp_path / f"site/phases/{source_backed_phase}.html").read_text(encoding="utf-8")
        assert "Visual highlights" in phase_html
        assert 'class="card highlight-card"' in phase_html
        assert "tattoo" not in phase_html.lower()
    diopside = (tmp_path / "site/phases/diopside.html").read_text(encoding="utf-8")
    assert "phases/diopside/source.yml" in diopside
    assert "blocked by source promotion" not in diopside
    assert "Visual product matrix" in diopside
    assert diopside.count('class="card matrix-card"') == 6
    assert diopside.count('class="matrix-group"') == 2
    assert 'data-state="available" data-thumbnail-count="4"' in diopside
    assert diopside.count('class="card product-card"') == 9
    diamond = (tmp_path / "site/phases/diamond.html").read_text(encoding="utf-8")
    assert diamond.count('class="card product-card"') == 9
    assert 'data-family="direct-reflector-orientation-set"' in diamond
    assert 'data-state="available" data-thumbnail-count="4"' in diamond

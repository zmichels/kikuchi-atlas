from __future__ import annotations

from dataclasses import replace
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
        "calcite",
        "enstatite",
        "pyrope",
    }
    assert phases["plagioclase-an52"].source_status == "tracked-source"
    assert phases["plagioclase-an52"].source_record == "phases/plagioclase-an52/source.yml"
    assert phases["muscovite-2m1"].source_record == "phases/muscovite-2m1/source.yml"
    assert phases["diopside"].family == "clinopyroxene"
    assert phases["calcite"].family == "carbonate"
    assert phases["enstatite"].family == "orthopyroxene"
    assert phases["pyrope"].family == "garnet"


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
    assert len(products) == 125
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
    wide_direct_products = [
        product
        for product in products
        if product.identifier.endswith("-direct-wide")
    ]
    assert {product.identifier for product in wide_direct_products} == {
        "forsterite-direct-wide",
        "ice-ih-direct-wide",
        "quartz-direct-wide",
        "zircon-direct-wide",
        "titanite-direct-wide",
    }
    assert all(product.preview_path is not None for product in wide_direct_products)
    assert all(product.preview_path.suffix == ".png" for product in wide_direct_products)
    assert all(product.preview_path.is_file() for product in wide_direct_products)
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
        "calcite-direct-standard",
        "enstatite-direct-standard",
        "pyrope-direct-standard",
    }


def test_all_products_resolve_only_to_canonical_packages() -> None:
    phases = load_phase_registry(REGISTRY)
    _, products = load_product_registry(
        PRODUCTS,
        phase_slugs={phase.slug for phase in phases},
    )

    assert len(products) == 125
    assert all(product.is_available() for product in products)
    assert all(
        "local/atlas/phases/" in path.relative_to(ROOT).as_posix()
        for product in products
        for path in product.required_paths()
        if path.is_relative_to(ROOT / "local")
    )
    assert {
        product.identifier
        for product in products
        if product.identifier.startswith("quartz-") and product.media_format == "mov"
    } == {
        "quartz-direct-reflector-artist-master-x-axis",
        "quartz-near-depth-artist-master-identity-60fps",
        "quartz-near-depth-artist-master-oblique-17-31-43-60fps",
    }
    assert all(
        product.web_path and product.web_path.suffix == ".mp4"
        for product in products
        if product.media_format == "mov"
    )


def test_product_availability_requires_package_manifest_and_declared_web_proxy(
    tmp_path: Path,
) -> None:
    phases = load_phase_registry(REGISTRY)
    _, products = load_product_registry(
        PRODUCTS,
        phase_slugs={phase.slug for phase in phases},
    )
    source = next(product for product in products if product.media_format == "mov")
    package = tmp_path / source.identifier
    package.mkdir()
    media = package / "media.mov"
    preview = package / "preview.png"
    web = package / "web.mp4"
    manifest = package / "product-package.yml"
    for path in (media, preview, web, manifest):
        path.write_bytes(b"fixture")
    product = replace(
        source,
        media_path=media,
        preview_path=preview,
        web_path=web,
        bundle_path=package,
        provenance_path=manifest,
    )

    assert product.is_available()
    web.unlink()
    assert not product.is_available()
    web.write_bytes(b"fixture")
    manifest.unlink()
    assert not product.is_available()


def test_kinematical_extension_baseline_has_exact_twelve_phase_coverage() -> None:
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

    assert result.phase_count == 12
    assert result.product_count == 125
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
    assert direct_type_html.count('class="card type-phase-card"') == 12
    globe_type = tmp_path / "site/product-types/reflector-ridge-globe.html"
    assert globe_type.is_file()
    assert globe_type.read_text(encoding="utf-8").count('class="card type-phase-card"') == 12
    assert result.products_path.is_file()
    product_page = result.products_path.read_text(encoding="utf-8")
    assert 'id="product-search"' in product_page
    assert 'id="phase-filter"' in product_page
    assert 'id="family-filter"' in product_page
    assert product_page.count('class="card product-card"') == 125
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
    quartz = (tmp_path / "site/phases/quartz.html").read_text(encoding="utf-8")
    assert quartz.count('class="card product-card"') == 13
    assert quartz.count('type="video/quicktime"') == 3
    assert quartz.index(">open MOV<") < quartz.index(">web copy<")
    assert "Each card opens its actual SVG, PNG, MP4, MOV, or STL first." in quartz
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
        "calcite",
        "enstatite",
        "pyrope",
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


def test_atlas_adds_full_resolution_action_only_for_explicit_product_url(
    tmp_path: Path,
) -> None:
    result = build_atlas(
        registry_path=REGISTRY,
        product_registry_path=PRODUCTS,
        anchor_catalog_path=ANCHORS,
        output_root=tmp_path / "site",
        product_urls={
            "quartz-direct-reflector-artist-master-x-axis": (
                "https://drive.google.com/drive/folders/verified-product-id"
            )
        },
    )

    quartz = (result.index_path.parent / "phases/quartz.html").read_text(encoding="utf-8")
    assert quartz.count(">open full-resolution package<") == 1
    assert "https://drive.google.com/drive/folders/verified-product-id" in quartz
    url_position = quartz.index(
        "https://drive.google.com/drive/folders/verified-product-id"
    )
    product_card = quartz[quartz.rfind("<article", 0, url_position) : quartz.index(
        "</article>", url_position
    )]
    assert product_card.index(">open MOV<") < product_card.index(">web copy<")
    assert product_card.index(">web copy<") < product_card.index(">bundle<")
    assert product_card.index(">bundle<") < product_card.index(">provenance<")
    assert product_card.index(">provenance<") < product_card.index(
        ">open full-resolution package<"
    )

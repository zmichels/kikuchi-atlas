"""Build a phase-first and product-first local Kikuchi Atlas.

The Atlas is a publication layer over checked-in phase records and a curated
product registry. It deliberately separates a product's visual family from
its scientific tier: a direct-reflector illustration or print mesh is never
silently promoted into an EBSD acquisition or dictionary claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import os
from pathlib import Path
from typing import Any

import yaml


_REGISTRY_FIELDS = {"schema_version", "title", "claim_boundary", "phases"}
_PHASE_FIELDS = {
    "slug",
    "display_name",
    "family",
    "formula",
    "crystal_system",
    "source_status",
    "source_record",
    "candidate_reference",
    "scope_note",
}
_CANDIDATE_FIELDS = {
    "label",
    "source_url",
    "cif_url",
    "license",
    "rationale",
    "promotion_trigger",
}
_PRODUCT_REGISTRY_FIELDS = {
    "schema_version",
    "title",
    "claim_boundary",
    "product_families",
    "products",
}
_PRODUCT_FAMILY_FIELDS = {"id", "label", "coverage", "description", "claim_boundary"}
_PRODUCT_FIELDS = {
    "id",
    "title",
    "phase_slugs",
    "families",
    "format",
    "media_path",
    "preview_path",
    "bundle_path",
    "provenance_path",
    "recipe",
    "entrypoint",
    "tier",
    "state",
    "caption",
    "orientation",
    "hero",
}
_SOURCE_STATUSES = {"tracked-source", "candidate-reference"}
_PRODUCT_STATES = {"local-published", "tracked-review-proof"}
_COVERAGE = {"core", "extension"}
_FORMATS = {"png", "svg", "mp4", "stl"}
_HIGHLIGHT_FAMILY_ORDER = (
    "direct-reflector-template",
    "intensity-master",
    "depth-field-motion",
    "x-axis-motion",
    "intensity-relief-globe",
    "reflector-ridge-globe",
)


@dataclass(frozen=True)
class AtlasPhase:
    """One honest atlas entry, whether source-ready or still an intake candidate."""

    slug: str
    display_name: str
    family: str
    formula: str
    crystal_system: str
    source_status: str
    source_record: str | None
    candidate_reference: dict[str, str] | None
    scope_note: str


@dataclass(frozen=True)
class ProductFamily:
    """A named slot in the common product matrix."""

    identifier: str
    label: str
    coverage: str
    description: str
    claim_boundary: str


@dataclass(frozen=True)
class AtlasProduct:
    """One individually browsable local product with many-to-many phase/type tags."""

    identifier: str
    title: str
    phase_slugs: tuple[str, ...]
    family_ids: tuple[str, ...]
    media_format: str
    media_path: Path
    preview_path: Path | None
    bundle_path: Path
    provenance_path: Path | None
    recipe: str
    entrypoint: str
    tier: str
    state: str
    caption: str
    orientation: str
    hero: bool

    def is_available(self) -> bool:
        return self.media_path.is_file()


@dataclass(frozen=True)
class AtlasBuildResult:
    """Paths emitted by one deterministic static atlas publication."""

    index_path: Path
    products_path: Path
    phase_pages: tuple[Path, ...]
    phase_count: int
    product_count: int


def _mapping(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} fields differ from the atlas schema")
    return value


def _mapping_with_optional(
    value: object, required: set[str], optional: set[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= set(value) or not set(value) <= required | optional:
        raise ValueError(f"{label} fields differ from the atlas schema")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _text_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    values = tuple(_text(item, label) for item in value)
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must not repeat values")
    return values


def _repository_path(root: Path, value: object, label: str, *, allow_none: bool = False) -> Path | None:
    if value is None and allow_none:
        return None
    relative = _text(value, label)
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} escapes the repository root")
    return path


def _phase_from_mapping(value: object, root: Path) -> AtlasPhase:
    raw = _mapping(value, _PHASE_FIELDS, "atlas phase")
    status = _text(raw["source_status"], "atlas phase source_status")
    if status not in _SOURCE_STATUSES:
        raise ValueError("atlas phase source_status is unsupported")
    source_record = raw["source_record"]
    candidate = raw["candidate_reference"]
    if status == "tracked-source":
        if not isinstance(source_record, str) or candidate is not None:
            raise ValueError("tracked-source atlas phase requires only source_record")
        source_path = _repository_path(root, source_record, "atlas source record")
        assert source_path is not None
        if not source_path.is_file():
            raise ValueError(f"atlas source record is missing: {source_record}")
        source_value = source_record
        candidate_value = None
    else:
        if source_record is not None:
            raise ValueError("candidate-reference atlas phase must not name source_record")
        candidate_raw = _mapping(candidate, _CANDIDATE_FIELDS, "candidate_reference")
        source_value = None
        candidate_value = {
            key: _text(candidate_raw[key], f"candidate_reference.{key}")
            for key in sorted(_CANDIDATE_FIELDS)
        }
    return AtlasPhase(
        slug=_text(raw["slug"], "atlas phase slug"),
        display_name=_text(raw["display_name"], "atlas phase display_name"),
        family=_text(raw["family"], "atlas phase family"),
        formula=_text(raw["formula"], "atlas phase formula"),
        crystal_system=_text(raw["crystal_system"], "atlas phase crystal_system"),
        source_status=status,
        source_record=source_value,
        candidate_reference=candidate_value,
        scope_note=_text(raw["scope_note"], "atlas phase scope_note"),
    )


def load_phase_registry(path: str | Path) -> tuple[AtlasPhase, ...]:
    """Load the tracked atlas registry and reject ambiguous phase identities."""
    registry_path = Path(path).resolve()
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError("atlas registry YAML is invalid") from error
    root = registry_path.parents[2]
    payload = _mapping(raw, _REGISTRY_FIELDS, "atlas registry")
    if payload["schema_version"] != 1:
        raise ValueError("unsupported atlas registry schema")
    _text(payload["title"], "atlas title")
    _text(payload["claim_boundary"], "atlas claim_boundary")
    raw_phases = payload["phases"]
    if not isinstance(raw_phases, list) or not raw_phases:
        raise ValueError("atlas registry phases must be a non-empty list")
    phases = tuple(_phase_from_mapping(item, root) for item in raw_phases)
    slugs = tuple(phase.slug for phase in phases)
    if len(set(slugs)) != len(slugs):
        raise ValueError("atlas phase slugs must be unique")
    return phases


def _family_from_mapping(value: object) -> ProductFamily:
    raw = _mapping(value, _PRODUCT_FAMILY_FIELDS, "atlas product family")
    coverage = _text(raw["coverage"], "atlas product family coverage")
    if coverage not in _COVERAGE:
        raise ValueError("atlas product family coverage is unsupported")
    return ProductFamily(
        identifier=_text(raw["id"], "atlas product family id"),
        label=_text(raw["label"], "atlas product family label"),
        coverage=coverage,
        description=_text(raw["description"], "atlas product family description"),
        claim_boundary=_text(raw["claim_boundary"], "atlas product family claim_boundary"),
    )


def _product_from_mapping(
    value: object,
    *,
    root: Path,
    phase_slugs: set[str],
    family_ids: set[str],
) -> AtlasProduct:
    raw = _mapping_with_optional(value, _PRODUCT_FIELDS - {"preview_path", "provenance_path", "orientation", "hero"}, {"preview_path", "provenance_path", "orientation", "hero"}, "atlas product")
    phases = _text_list(raw["phase_slugs"], "atlas product phase_slugs")
    unknown_phases = set(phases) - phase_slugs
    if unknown_phases:
        raise ValueError(f"atlas product refers to unregistered phases: {sorted(unknown_phases)!r}")
    families = _text_list(raw["families"], "atlas product families")
    unknown_families = set(families) - family_ids
    if unknown_families:
        raise ValueError(f"atlas product refers to unknown families: {sorted(unknown_families)!r}")
    media_format = _text(raw["format"], "atlas product format")
    if media_format not in _FORMATS:
        raise ValueError("atlas product format is unsupported")
    state = _text(raw["state"], "atlas product state")
    if state not in _PRODUCT_STATES:
        raise ValueError("atlas product state is unsupported")
    hero = raw.get("hero", False)
    if not isinstance(hero, bool):
        raise ValueError("atlas product hero must be boolean")
    recipe = _text(raw["recipe"], "atlas product recipe")
    recipe_path = _repository_path(root, recipe, "atlas product recipe")
    assert recipe_path is not None
    if not recipe_path.is_file():
        raise ValueError(f"atlas product recipe is missing: {recipe}")
    return AtlasProduct(
        identifier=_text(raw["id"], "atlas product id"),
        title=_text(raw["title"], "atlas product title"),
        phase_slugs=phases,
        family_ids=families,
        media_format=media_format,
        media_path=_repository_path(root, raw["media_path"], "atlas product media_path"),
        preview_path=_repository_path(root, raw.get("preview_path"), "atlas product preview_path", allow_none=True),
        bundle_path=_repository_path(root, raw["bundle_path"], "atlas product bundle_path"),
        provenance_path=_repository_path(
            root, raw.get("provenance_path"), "atlas product provenance_path", allow_none=True
        ),
        recipe=recipe,
        entrypoint=_text(raw["entrypoint"], "atlas product entrypoint"),
        tier=_text(raw["tier"], "atlas product tier"),
        state=state,
        caption=_text(raw["caption"], "atlas product caption"),
        orientation=_text(raw.get("orientation", "not specified"), "atlas product orientation"),
        hero=hero,
    )


def load_product_registry(
    path: str | Path, *, phase_slugs: set[str]
) -> tuple[tuple[ProductFamily, ...], tuple[AtlasProduct, ...]]:
    """Load the curated individual-product registry and validate its relations."""
    registry_path = Path(path).resolve()
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError("atlas product registry YAML is invalid") from error
    root = registry_path.parents[2]
    payload = _mapping(raw, _PRODUCT_REGISTRY_FIELDS, "atlas product registry")
    if payload["schema_version"] != 1:
        raise ValueError("unsupported atlas product registry schema")
    _text(payload["title"], "atlas product registry title")
    _text(payload["claim_boundary"], "atlas product registry claim_boundary")
    raw_families = payload["product_families"]
    raw_products = payload["products"]
    if not isinstance(raw_families, list) or not raw_families:
        raise ValueError("atlas product_families must be a non-empty list")
    if not isinstance(raw_products, list) or not raw_products:
        raise ValueError("atlas products must be a non-empty list")
    families = tuple(_family_from_mapping(item) for item in raw_families)
    family_ids = {family.identifier for family in families}
    if len(family_ids) != len(families):
        raise ValueError("atlas product family ids must be unique")
    products = tuple(
        _product_from_mapping(item, root=root, phase_slugs=phase_slugs, family_ids=family_ids)
        for item in raw_products
    )
    product_ids = {product.identifier for product in products}
    if len(product_ids) != len(products):
        raise ValueError("atlas product ids must be unique")
    return families, products


def _validate_anchor_catalog(path: Path, phase_slugs: set[str]) -> None:
    """Keep the older publication-anchor catalog tied to the same phase universe."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError("artifact catalog YAML is invalid") from error
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("unsupported artifact catalog schema")
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise ValueError("artifact catalog entries must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("artifact catalog entry must be a mapping")
        value = entry.get("phase")
        phases = [value] if isinstance(value, str) else value
        if not isinstance(phases, list) or not all(isinstance(slug, str) for slug in phases):
            raise ValueError("artifact catalog phase must be text or a list of text")
        unknown = set(phases) - phase_slugs
        if unknown:
            raise ValueError(f"artifact catalog refers to unregistered phases: {sorted(unknown)!r}")


def _relative_href(page: Path, target: Path) -> str:
    return os.path.relpath(target, start=page.parent).replace(os.sep, "/")


def _page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{escape(title)}</title><style>
:root {{ color-scheme: dark; font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background: #0d1217; color: #edf2f6; }}
body {{ max-width: 1280px; margin: 0 auto; padding: 2.2rem 1.5rem 4rem; background: radial-gradient(circle at 20% -10%, #243749, #0d1217 48rem); }} a {{ color: #a9d7ff; }}
nav {{ display: flex; flex-wrap: wrap; gap: .7rem 1.2rem; margin-bottom: 2rem; font-size: .93rem; }} h1 {{ font-size: clamp(2rem, 4vw, 3.4rem); margin: 0 0 .35rem; letter-spacing: -.045em; }} h2 {{ margin-top: 2.4rem; }} h3 {{ margin: .1rem 0 .5rem; font-size: 1.08rem; }}
.lede {{ max-width: 70rem; color: #c2ccd4; font-size: 1.08rem; line-height: 1.55; }} .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 1.05rem; }} .visual-highlights {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 1.05rem; }}
.card {{ overflow: hidden; border: 1px solid #2e3d48; border-radius: 16px; background: rgba(17,25,32,.88); box-shadow: 0 18px 40px rgba(0,0,0,.18); }} .card img, .card video, .placeholder {{ display: block; aspect-ratio: 1/.72; width: 100%; object-fit: cover; background: linear-gradient(135deg,#26343f,#111a20); }}
.placeholder {{ display: grid; place-items: center; color: #8798a5; font-size: .86rem; letter-spacing: .04em; text-transform: uppercase; }} .pad {{ padding: 1rem 1.05rem 1.1rem; }} .highlight-card .pad {{ min-height: 7.4rem; }} .highlight-card a.visual-link {{ display: block; color: inherit; }} .kicker {{ margin: 0 0 .45rem; color: #8fa7b8; font-size: .75rem; letter-spacing: .09em; text-transform: uppercase; }}
.title {{ margin: 0; font-size: 1.3rem; }} .meta {{ margin: .7rem 0 0; color: #b9c4cb; line-height: 1.45; font-size: .91rem; }} .badge, .tag {{ display: inline-block; margin: .65rem .25rem 0 0; padding: .22rem .5rem; border: 1px solid #4f697b; border-radius: 999px; color: #cce7fa; font-size: .75rem; }}
.candidate {{ border-color: #755f3d; }} .candidate .badge {{ border-color: #977a46; color: #f0d290; }} .product {{ padding: 1rem 1.05rem 1.1rem; }} .product strong {{ display: block; }} .product small {{ color: #95a7b4; }} .callout {{ margin-top: 2rem; padding: 1rem 1.1rem; border-left: 3px solid #6fa7d1; background: rgba(31,51,67,.5); line-height: 1.5; }} code {{ color: #d8e6ef; }}
.actions {{ display: flex; flex-wrap: wrap; gap: .65rem; margin-top: .85rem; }} .actions a {{ padding: .35rem .58rem; border: 1px solid #405b6d; border-radius: .45rem; text-decoration: none; }} .matrix {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }} .matrix th, .matrix td {{ border-bottom: 1px solid #2e3d48; padding: .7rem; text-align: left; vertical-align: top; }} .matrix th {{ color: #b9c4cb; font-size: .79rem; text-transform: uppercase; letter-spacing: .06em; }}
.coverage {{ color: #b9c4cb; }} .status-live {{ color: #b9e5ca; }} .status-plan {{ color: #e5c98a; }} .filters {{ display: grid; grid-template-columns: minmax(220px, 2fr) repeat(2, minmax(160px, 1fr)); gap: .75rem; margin: 1.5rem 0; }} .filters input, .filters select {{ padding: .62rem .7rem; border: 1px solid #465b6b; border-radius: .45rem; background: #101a21; color: #edf2f6; font: inherit; }} .hidden {{ display: none; }} .muted {{ color: #95a7b4; }}
@media (max-width: 620px) {{ body {{ padding: 1.5rem 1rem 3rem; }} .filters {{ grid-template-columns: 1fr; }} .matrix {{ font-size: .9rem; }} }}
</style></head><body>{body}</body></html>"""


def _navigation(page: Path, output_root: Path) -> str:
    index = output_root / "index.html"
    products = output_root / "products.html"
    return (
        f'<nav><a href="{escape(_relative_href(page, index))}">Kikuchi Atlas</a>'
        f'<a href="{escape(_relative_href(page, products))}">Browse all products</a></nav>'
    )


def _product_visual(product: AtlasProduct, page: Path) -> str:
    media_available = product.is_available()
    preview = product.preview_path if product.preview_path and product.preview_path.is_file() else None
    if product.media_format == "mp4" and media_available:
        poster = f' poster="{escape(_relative_href(page, preview))}"' if preview else ""
        return (
            f'<video controls preload="metadata"{poster}>'
            f'<source src="{escape(_relative_href(page, product.media_path))}" type="video/mp4"></video>'
        )
    display_path = preview or (product.media_path if media_available else None)
    if display_path is not None and display_path.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg"}:
        return f'<img src="{escape(_relative_href(page, display_path))}" alt="{escape(product.title)}">'
    noun = "STL mesh" if product.media_format == "stl" else "Local product unavailable"
    return f'<div class="placeholder">{noun}</div>'


def _highlight_visual(product: AtlasProduct, page: Path) -> str:
    """Return a lightweight still visual for a phase-page highlight card."""
    preview = product.preview_path if product.preview_path and product.preview_path.is_file() else None
    display_path = preview or (product.media_path if product.is_available() else None)
    if display_path is not None and display_path.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg"}:
        return f'<img src="{escape(_relative_href(page, display_path))}" alt="{escape(product.title)}">'
    return f'<div class="placeholder">{escape(product.media_format.upper())} preview unavailable</div>'


def _phase_highlights(products: tuple[AtlasProduct, ...]) -> tuple[AtlasProduct, ...]:
    """Choose up to three distinct, available visuals with a stable family order."""
    available = tuple(product for product in products if product.is_available())
    chosen: list[AtlasProduct] = []
    for family_id in _HIGHLIGHT_FAMILY_ORDER:
        candidates = [product for product in available if family_id in product.family_ids]
        candidates.sort(key=lambda product: (not product.hero, product.identifier))
        if candidates and candidates[0] not in chosen:
            chosen.append(candidates[0])
        if len(chosen) == 3:
            return tuple(chosen)
    for product in available:
        if product not in chosen:
            chosen.append(product)
        if len(chosen) == 3:
            break
    return tuple(chosen)


def _visual_highlights_html(products: tuple[AtlasProduct, ...], page: Path) -> str:
    highlights = _phase_highlights(products)
    if not highlights:
        return ""
    cards = "".join(
        f'<article class="card highlight-card"><a class="visual-link" '
        f'href="{escape(_relative_href(page, product.media_path))}">{_highlight_visual(product, page)}</a>'
        f'<div class="pad"><p class="kicker">{escape(product.media_format)} · '
        f'{escape(product.tier)}</p><h3>{escape(product.title)}</h3>'
        f'<p class="meta">{escape(product.caption)}</p></div></article>'
        for product in highlights
    )
    return (
        '<h2>Visual highlights</h2><p class="lede">A small, phase-specific visual cross-section: '
        'open any image to inspect its actual local product.</p>'
        f'<div class="visual-highlights">{cards}</div>'
    )


def _product_html(
    product: AtlasProduct,
    page: Path,
    output_root: Path,
    phase_by_slug: dict[str, AtlasPhase],
) -> str:
    availability = "available locally" if product.is_available() else "not present in this checkout"
    phase_tags = "".join(
        f'<a class="tag" href="{escape(_relative_href(page, output_root / "phases" / f"{slug}.html"))}">'
        f'{escape(phase_by_slug[slug].display_name)}</a>'
        for slug in product.phase_slugs
    )
    family_tags = "".join(f'<span class="tag">{escape(family_id)}</span>' for family_id in product.family_ids)
    actions = [
        f'<a href="{escape(_relative_href(page, product.media_path))}">open {escape(product.media_format.upper())}</a>',
        f'<a href="{escape(_relative_href(page, product.bundle_path))}">bundle</a>',
    ]
    if product.provenance_path is not None:
        actions.append(
            f'<a href="{escape(_relative_href(page, product.provenance_path))}">provenance</a>'
        )
    search = " ".join(
        (
            product.title,
            product.caption,
            product.orientation,
            product.tier,
            product.media_format,
            " ".join(product.family_ids),
            " ".join(phase_by_slug[slug].display_name for slug in product.phase_slugs),
        )
    ).lower()
    return (
        f'<article class="card product-card" data-phases="{" ".join(product.phase_slugs)}" '
        f'data-families="{" ".join(product.family_ids)}" data-format="{escape(product.media_format)}" '
        f'data-search="{escape(search)}">{_product_visual(product, page)}<div class="product">'
        f'<p class="kicker">{escape(product.media_format)} · {escape(product.tier)}</p>'
        f'<h3>{escape(product.title)}</h3><p class="meta">{escape(product.caption)}</p>'
        f'<p class="muted">Orientation: {escape(product.orientation)}<br>{availability}</p>'
        f'{phase_tags}{family_tags}<div class="actions">{"".join(actions)}</div></div></article>'
    )


def _source_block(phase: AtlasPhase) -> str:
    if phase.source_status == "tracked-source":
        return f'<p><strong>Tracked source:</strong> <code>{escape(phase.source_record or "")}</code></p>'
    assert phase.candidate_reference is not None
    candidate = phase.candidate_reference
    return (
        f'<p><strong>Candidate reference:</strong> {escape(candidate["label"])}<br>'
        f'<a href="{escape(candidate["source_url"])}">record</a> · '
        f'<a href="{escape(candidate["cif_url"])}">CIF</a> · {escape(candidate["license"])}.</p>'
        f'<p><strong>Promotion trigger:</strong> {escape(candidate["promotion_trigger"])}</p>'
    )


def _matrix_html(
    phase: AtlasPhase, families: tuple[ProductFamily, ...], products: tuple[AtlasProduct, ...]
) -> str:
    rows: list[str] = []
    for family in families:
        members = [product for product in products if phase.slug in product.phase_slugs and family.identifier in product.family_ids]
        if members:
            available = sum(product.is_available() for product in members)
            status = f'<span class="status-live">{available}/{len(members)} individual products available</span>'
        elif phase.source_status == "candidate-reference":
            status = '<span class="status-plan">blocked by source promotion</span>'
        else:
            status = '<span class="status-plan">planned for this phase</span>'
        rows.append(
            f'<tr><td><strong>{escape(family.label)}</strong><br><span class="muted">{escape(family.coverage)}</span></td>'
            f'<td>{escape(family.description)}</td><td>{status}</td></tr>'
        )
    return (
        '<table class="matrix"><thead><tr><th>Product family</th><th>What it is</th><th>Coverage</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _phase_page_html(
    phase: AtlasPhase,
    *,
    products: tuple[AtlasProduct, ...],
    families: tuple[ProductFamily, ...],
    page: Path,
    output_root: Path,
    phase_by_slug: dict[str, AtlasPhase],
) -> str:
    related = tuple(product for product in products if phase.slug in product.phase_slugs)
    product_html = "".join(
        _product_html(product, page, output_root, phase_by_slug) for product in related
    )
    if not product_html:
        product_html = '<div class="placeholder">No individual product published yet</div>'
    return _page_shell(
        f"Kikuchi Atlas — {phase.display_name}",
        f'''{_navigation(page, output_root)}<h1>{escape(phase.display_name)}</h1>
<p class="lede">{escape(phase.family)} · {escape(phase.formula)} · {escape(phase.crystal_system)}</p>
<div class="callout"><strong>Atlas scope:</strong> {escape(phase.scope_note)}</div>{_source_block(phase)}
{_visual_highlights_html(related, page)}
<h2>Common product matrix</h2><p class="lede">Every phase is measured against the same named product families. A blank slot is a transparent production state, not a different kind of plot.</p>
{_matrix_html(phase, families, products)}
<h2>Individual products</h2><p class="lede">Each card opens its actual SVG, PNG, MP4, or STL first. The bundle and provenance record are secondary links for reproduction and audit.</p><div class="grid">{product_html}</div>''',
    )


def _products_page_html(
    *,
    products: tuple[AtlasProduct, ...],
    families: tuple[ProductFamily, ...],
    phases: tuple[AtlasPhase, ...],
    page: Path,
    output_root: Path,
) -> str:
    phase_by_slug = {phase.slug: phase for phase in phases}
    options = "".join(
        f'<option value="{escape(phase.slug)}">{escape(phase.display_name)}</option>' for phase in phases
    )
    family_options = "".join(
        f'<option value="{escape(family.identifier)}">{escape(family.label)}</option>' for family in families
    )
    cards = "".join(_product_html(product, page, output_root, phase_by_slug) for product in products)
    return _page_shell(
        "Kikuchi Atlas — products",
        f'''{_navigation(page, output_root)}<h1>Browse individual products</h1>
<p class="lede">Filter the curated local release set by phase, product family, medium, or any text in its title and caption. Products may belong to several families and phases; each relation remains visible on its card.</p>
<div class="filters"><input id="product-search" type="search" placeholder="Search products, orientation, tier…"><select id="phase-filter"><option value="">All phases</option>{options}</select><select id="family-filter"><option value="">All product families</option>{family_options}</select><select id="format-filter"><option value="">All media</option><option value="png">PNG</option><option value="svg">SVG</option><option value="mp4">MP4</option><option value="stl">STL</option></select></div>
<p id="result-count" class="muted"></p><div id="product-grid" class="grid">{cards}</div>
<script>
const controls = ['product-search','phase-filter','family-filter','format-filter'].map(id => document.getElementById(id));
const cards = [...document.querySelectorAll('.product-card')]; const count = document.getElementById('result-count');
function filterProducts() {{ const [search, phase, family, format] = controls.map(control => control.value.trim().toLowerCase()); let visible = 0;
  cards.forEach(card => {{ const matches = (!search || card.dataset.search.includes(search)) && (!phase || card.dataset.phases.split(' ').includes(phase)) && (!family || card.dataset.families.split(' ').includes(family)) && (!format || card.dataset.format === format); card.classList.toggle('hidden', !matches); if (matches) visible += 1; }}); count.textContent = `${{visible}} individually browsable products`; }}
controls.forEach(control => control.addEventListener('input', filterProducts)); filterProducts();
</script>''',
    )


def _phase_card(
    phase: AtlasPhase,
    *,
    products: tuple[AtlasProduct, ...],
    output_root: Path,
) -> str:
    page = output_root / "index.html"
    phase_page = output_root / "phases" / f"{phase.slug}.html"
    related = [product for product in products if phase.slug in product.phase_slugs]
    heroes = [product for product in related if product.hero]
    preview_product = heroes[0] if heroes else next((product for product in related if product.is_available()), None)
    if preview_product is not None:
        preview = preview_product.preview_path if preview_product.preview_path and preview_product.preview_path.is_file() else preview_product.media_path
        if preview.is_file() and preview.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg"}:
            visual = f'<img src="{escape(_relative_href(page, preview))}" alt="{escape(preview_product.title)}">'
        else:
            visual = '<div class="placeholder">Local product media</div>'
        lead_note = f'Lead: {preview_product.title}'
    else:
        visual = '<div class="placeholder">Source intake</div>'
        lead_note = "No product published yet"
    candidate_class = " candidate" if phase.source_status == "candidate-reference" else ""
    return (
        f'<article class="card{candidate_class}">{visual}<div class="pad"><p class="kicker">'
        f'{escape(phase.family)} · {escape(phase.crystal_system)}</p><h2 class="title">'
        f'<a href="{escape(_relative_href(page, phase_page))}">{escape(phase.display_name)}</a></h2>'
        f'<p class="meta">{escape(phase.formula)}<br>{escape(lead_note)}</p>'
        f'<span class="badge">{escape(phase.source_status)}</span></div></article>'
    )


def build_atlas(
    *,
    registry_path: str | Path,
    product_registry_path: str | Path,
    anchor_catalog_path: str | Path,
    output_root: str | Path,
) -> AtlasBuildResult:
    """Render a relational local atlas while leaving generated media in ``local/``."""
    registry = Path(registry_path).resolve()
    phases = load_phase_registry(registry)
    phase_slugs = {phase.slug for phase in phases}
    families, products = load_product_registry(product_registry_path, phase_slugs=phase_slugs)
    _validate_anchor_catalog(Path(anchor_catalog_path).resolve(), phase_slugs)
    output = Path(output_root).resolve()
    phase_directory = output / "phases"
    phase_directory.mkdir(parents=True, exist_ok=True)
    phase_by_slug = {phase.slug: phase for phase in phases}
    phase_pages: list[Path] = []
    for phase in phases:
        page = phase_directory / f"{phase.slug}.html"
        page.write_text(
            _phase_page_html(
                phase,
                products=products,
                families=families,
                page=page,
                output_root=output,
                phase_by_slug=phase_by_slug,
            ),
            encoding="utf-8",
        )
        phase_pages.append(page)
    products_page = output / "products.html"
    products_page.write_text(
        _products_page_html(
            products=products, families=families, phases=phases, page=products_page, output_root=output
        ),
        encoding="utf-8",
    )
    index = output / "index.html"
    cards = "".join(_phase_card(phase, products=products, output_root=output) for phase in phases)
    index.write_text(
        _page_shell(
            "Kikuchi Atlas",
            f'''{_navigation(index, output)}<h1>Kikuchi Atlas</h1>
<p class="lede">A local, provenance-first library of individual Kikuchi visualizations, motion studies, and printable products. Browse phase-first or product-first; every card preserves its visual family and scientific tier.</p>
<p><a href="products.html">Browse all {len(products)} individual products →</a></p><div class="grid">{cards}</div>
<div class="callout"><strong>Current scope:</strong> {len(phases)} phase entries and {len(products)} curated individual products across {len(families)} named product families. The phase-card leads deliberately use comparable direct-reflector hemisphere templates when available, rather than mixing an intensity master with an idealized band plot. Candidate references remain visible for planning but cannot be represented as rendered or dictionary-ready until their source and simulation contracts are accepted.</div>''',
        ),
        encoding="utf-8",
    )
    return AtlasBuildResult(index, products_page, tuple(phase_pages), len(phases), len(products))


__all__ = [
    "AtlasBuildResult",
    "AtlasPhase",
    "AtlasProduct",
    "ProductFamily",
    "build_atlas",
    "load_phase_registry",
    "load_product_registry",
]

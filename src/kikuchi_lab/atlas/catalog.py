"""Build a browsable phase atlas from tracked source and product records.

The atlas is intentionally a publication layer over project-owned phase and
product contracts. It must not turn a direct-reflector illustration or a print
mesh into an indexing claim merely by placing it beside a master image.
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
_SOURCE_STATUSES = {"tracked-source", "candidate-reference"}


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
class AtlasProduct:
    """A published local product associated with one atlas phase."""

    phase_slug: str
    identifier: str
    tier: str
    artifact_path: Path
    files: tuple[str, ...]
    state: str

    def preview_path(self) -> Path | None:
        if "preview.png" in self.files:
            return self.artifact_path / "preview.png"
        return None


@dataclass(frozen=True)
class AtlasBuildResult:
    """Paths emitted by one deterministic static atlas publication."""

    index_path: Path
    phase_pages: tuple[Path, ...]
    phase_count: int
    product_count: int


def _mapping(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} fields differ from the atlas schema")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


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
        source_path = (root / source_record).resolve()
        if not source_path.is_relative_to(root):
            raise ValueError("atlas source record escapes the repository root")
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


def _load_products(path: Path, root: Path, phase_slugs: set[str]) -> tuple[AtlasProduct, ...]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError("artifact catalog YAML is invalid") from error
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("unsupported artifact catalog schema")
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise ValueError("artifact catalog entries must be a list")
    products: list[AtlasProduct] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("artifact catalog entry must be a mapping")
        phases = entry.get("phase")
        slugs = [phases] if isinstance(phases, str) else phases
        if not isinstance(slugs, list) or not all(isinstance(slug, str) for slug in slugs):
            raise ValueError("artifact catalog phase must be text or a list of text")
        unknown = set(slugs) - phase_slugs
        if unknown:
            raise ValueError(f"artifact catalog refers to unregistered phases: {sorted(unknown)!r}")
        artifact = entry.get("artifact_path")
        files = entry.get("files")
        if not isinstance(artifact, str) or not isinstance(files, list):
            raise ValueError("artifact catalog entry is missing artifact_path or files")
        for slug in slugs:
            products.append(
                AtlasProduct(
                    phase_slug=slug,
                    identifier=_text(entry.get("id"), "artifact catalog id"),
                    tier=_text(entry.get("tier"), "artifact catalog tier"),
                    artifact_path=(root / artifact).resolve(),
                    files=tuple(_text(item, "artifact catalog file") for item in files),
                    state=_text(entry.get("state"), "artifact catalog state"),
                )
            )
    return tuple(products)


def _relative_href(page: Path, target: Path) -> str:
    return os.path.relpath(target, start=page.parent).replace(os.sep, "/")


def _page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{escape(title)}</title><style>
:root {{ color-scheme: dark; font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background: #0d1217; color: #edf2f6; }}
body {{ max-width: 1200px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; background: radial-gradient(circle at 20% -10%, #243749, #0d1217 48rem); }} a {{ color: #a9d7ff; }}
h1 {{ font-size: clamp(2rem, 4vw, 3.4rem); margin: 0 0 .35rem; letter-spacing: -.045em; }} h2 {{ margin-top: 2.4rem; }}
.lede {{ max-width: 65rem; color: #c2ccd4; font-size: 1.08rem; line-height: 1.55; }} .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.05rem; }}
.card {{ overflow: hidden; border: 1px solid #2e3d48; border-radius: 16px; background: rgba(17,25,32,.88); box-shadow: 0 18px 40px rgba(0,0,0,.18); }} .card img, .placeholder {{ display: block; aspect-ratio: 1/.72; width: 100%; object-fit: cover; background: linear-gradient(135deg,#26343f,#111a20); }}
.placeholder {{ display: grid; place-items: center; color: #8798a5; font-size: .86rem; letter-spacing: .04em; text-transform: uppercase; }} .pad {{ padding: 1rem 1.05rem 1.1rem; }} .kicker {{ margin: 0 0 .45rem; color: #8fa7b8; font-size: .75rem; letter-spacing: .09em; text-transform: uppercase; }}
.title {{ margin: 0; font-size: 1.3rem; }} .meta {{ margin: .7rem 0 0; color: #b9c4cb; line-height: 1.45; font-size: .91rem; }} .badge {{ display: inline-block; margin-top: .8rem; padding: .22rem .5rem; border: 1px solid #4f697b; border-radius: 999px; color: #cce7fa; font-size: .75rem; }}
.candidate {{ border-color: #755f3d; }} .candidate .badge {{ border-color: #977a46; color: #f0d290; }} .product {{ border-top: 1px solid #2e3d48; padding: .8rem 1.05rem; }} .product strong {{ display: block; }} .product small {{ color: #95a7b4; }} .callout {{ margin-top: 2rem; padding: 1rem 1.1rem; border-left: 3px solid #6fa7d1; background: rgba(31,51,67,.5); line-height: 1.5; }} code {{ color: #d8e6ef; }}
</style></head><body>{body}</body></html>"""


def _product_html(product: AtlasProduct, page: Path) -> str:
    media = product.preview_path()
    if media is not None and media.is_file():
        visual = f'<img src="{escape(_relative_href(page, media))}" alt="{escape(product.identifier)} preview">'
    else:
        visual = '<div class="placeholder">Local product bundle</div>'
    availability = "present" if product.artifact_path.is_dir() else "not present in this checkout"
    return (
        f'<article class="card">{visual}<div class="product"><strong>{escape(product.identifier)}</strong>'
        f'<small>{escape(product.tier)} · {escape(product.state)} · {availability}</small><br>'
        f'<a href="{escape(_relative_href(page, product.artifact_path))}">open local bundle</a></div></article>'
    )


def _phase_page_html(phase: AtlasPhase, products: tuple[AtlasProduct, ...], page: Path) -> str:
    if phase.source_status == "tracked-source":
        source_block = f'<p><strong>Tracked source:</strong> <code>{escape(phase.source_record or "")}</code></p>'
    else:
        assert phase.candidate_reference is not None
        candidate = phase.candidate_reference
        source_block = (
            f'<p><strong>Candidate reference:</strong> {escape(candidate["label"])}<br>'
            f'<a href="{escape(candidate["source_url"])}">record</a> · <a href="{escape(candidate["cif_url"])}">CIF</a> · {escape(candidate["license"])}.</p>'
            f'<p><strong>Promotion trigger:</strong> {escape(candidate["promotion_trigger"])}</p>'
        )
    product_html = "".join(_product_html(product, page) for product in products)
    if not product_html:
        product_html = '<div class="placeholder">No product published yet</div>'
    return _page_shell(
        f"Kikuchi Atlas — {phase.display_name}",
        f'''<p><a href="../index.html">← Kikuchi Atlas</a></p><h1>{escape(phase.display_name)}</h1>
<p class="lede">{escape(phase.family)} · {escape(phase.formula)} · {escape(phase.crystal_system)}</p>
<div class="callout"><strong>Atlas scope:</strong> {escape(phase.scope_note)}</div>{source_block}<h2>Local products</h2><div class="grid">{product_html}</div>''',
    )


def build_atlas(
    *, registry_path: str | Path, product_catalog_path: str | Path, output_root: str | Path
) -> AtlasBuildResult:
    """Render static pages while leaving generated pixels and meshes in ``local/``."""
    registry = Path(registry_path).resolve()
    phases = load_phase_registry(registry)
    root = registry.parents[2]
    products = _load_products(
        Path(product_catalog_path).resolve(), root, {phase.slug for phase in phases}
    )
    output = Path(output_root).resolve()
    phase_directory = output / "phases"
    phase_directory.mkdir(parents=True, exist_ok=True)
    phase_pages: list[Path] = []
    cards: list[str] = []
    for phase in phases:
        associated = tuple(product for product in products if product.phase_slug == phase.slug)
        page = phase_directory / f"{phase.slug}.html"
        page.write_text(_phase_page_html(phase, associated, page), encoding="utf-8")
        phase_pages.append(page)
        preview = associated[0].preview_path() if associated else None
        if preview is not None and preview.is_file():
            visual = f'<img src="{escape(_relative_href(output / "index.html", preview))}" alt="{escape(phase.display_name)} preview">'
        else:
            visual = '<div class="placeholder">Source intake</div>'
        candidate_class = " candidate" if phase.source_status == "candidate-reference" else ""
        cards.append(
            f'<article class="card{candidate_class}">{visual}<div class="pad"><p class="kicker">{escape(phase.family)} · {escape(phase.crystal_system)}</p>'
            f'<h2 class="title"><a href="{escape(_relative_href(output / "index.html", page))}">{escape(phase.display_name)}</a></h2>'
            f'<p class="meta">{escape(phase.formula)}<br>{escape(phase.scope_note)}</p><span class="badge">{escape(phase.source_status)}</span></div></article>'
        )
    index = output / "index.html"
    index.write_text(
        _page_shell(
            "Kikuchi Atlas",
            f'''<h1>Kikuchi Atlas</h1><p class="lede">A local, provenance-first library of Kikuchi visualizations and print products. Each product retains its own scientific tier; appearance alone does not upgrade its claim.</p>
<div class="grid">{"".join(cards)}</div><div class="callout"><strong>Atlas v0:</strong> {len(phases)} phase entries, {len(products)} cataloged product associations. Candidate references are visible early, but cannot be represented as rendered or dictionary-ready until their source and simulation contracts are accepted.</div>''',
        ),
        encoding="utf-8",
    )
    return AtlasBuildResult(index, tuple(phase_pages), len(phases), len(products))


__all__ = ["AtlasBuildResult", "AtlasPhase", "build_atlas", "load_phase_registry"]

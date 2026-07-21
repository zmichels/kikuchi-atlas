"""Build a deployable public Kikuchi Atlas without publishing it.

The local Atlas deliberately points at ignored ``local/`` products because it
is a review and provenance workspace.  This module creates a separate static
gallery that contains only web-safe display assets and a companion archival
inventory/staging area for the heavier scientific and printable artifacts.

No hosting account, DOI, or URL is assumed here.  The output is safe to hand
to a static host once its review and release metadata are approved.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import shutil
from typing import Iterable

from .catalog import AtlasProduct, build_atlas, load_phase_registry, load_product_registry


_WEB_SUFFIXES = {".png", ".svg", ".jpg", ".jpeg", ".mp4"}
_DEFAULT_MAX_WEB_ASSET_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class PublicAtlasBuildResult:
    """Locations and compact accounting from a local public-release build."""

    output_root: Path
    site_root: Path
    archive_root: Path
    inventory_path: Path
    web_assets: tuple[Path, ...]
    archive_assets: tuple[Path, ...]

    @property
    def web_asset_count(self) -> int:
        return len(self.web_assets)

    @property
    def archival_asset_count(self) -> int:
        return len(self.archive_assets)

    @property
    def web_asset_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.web_assets)

    @property
    def archival_asset_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.archive_assets)


def _relative_href(page: Path, target: Path) -> str:
    return os.path.relpath(target, start=page.parent).replace(os.sep, "/")


def _digest(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _copy_asset(path: Path, destination_root: Path, cache: dict[Path, Path]) -> Path:
    """Copy ``path`` content-addressably once and return its destination."""
    existing = cache.get(path)
    if existing is not None:
        return existing
    digest = _digest(path)
    destination = destination_root / digest[:16] / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    cache[path] = destination
    return destination


def _web_safe(path: Path, *, max_web_asset_bytes: int) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in _WEB_SUFFIXES
        and path.stat().st_size <= max_web_asset_bytes
    )


def _archive_sources(product: AtlasProduct) -> tuple[Path, ...]:
    return tuple(
        path
        for path in (product.media_path, product.preview_path, product.provenance_path)
        if path is not None and path.is_file()
    )


def _supplemental_archive_sources(product: AtlasProduct) -> tuple[tuple[str, Path], ...]:
    """Select compact scientific fields that are essential to parity products.

    Full run directories often include redundant frames or intermediate arrays.
    The canonical kinematical field and the relief-driving field are the compact
    source artifacts that must travel with their rendered extension products.
    """
    sources: list[tuple[str, Path]] = []
    if "intensity-master" in product.family_ids:
        master = product.bundle_path / "products" / "canonical-kinematical-master.npz"
        if master.is_file():
            sources.append(("canonical-kinematical-master", master))
    if "intensity-relief-globe" in product.family_ids:
        relief_field = product.bundle_path / "relief-field.npz"
        if relief_field.is_file():
            sources.append(("relief-field", relief_field))
    return tuple(sources)


def _product_inventory(
    product: AtlasProduct,
    *,
    root: Path,
    site_root: Path,
    archive_root: Path,
    web_paths: dict[Path, Path],
    archive_paths: dict[Path, Path],
    stage_archive: bool,
) -> dict[str, object]:
    def web_entry(path: Path | None) -> str | None:
        target = web_paths.get(path) if path is not None else None
        return target.relative_to(site_root).as_posix() if target is not None else None

    def archive_entry(path: Path | None) -> tuple[str | None, str | None]:
        if path is None or not path.is_file():
            return None, None
        digest = _digest(path)
        target = archive_paths.get(path)
        staged_path = target.relative_to(archive_root).as_posix() if target is not None else None
        return staged_path, digest

    media_archive_path, media_sha256 = archive_entry(product.media_path)
    preview_archive_path, preview_sha256 = archive_entry(product.preview_path)
    provenance_archive_path, provenance_sha256 = archive_entry(product.provenance_path)
    supplemental = []
    for role, source in _supplemental_archive_sources(product):
        staged_path, digest = archive_entry(source)
        supplemental.append({"role": role, "path": staged_path, "sha256": digest})
    return {
        "id": product.identifier,
        "title": product.title,
        "phase_slugs": list(product.phase_slugs),
        "family_ids": list(product.family_ids),
        "format": product.media_format,
        "tier": product.tier,
        "state": product.state,
        "caption": product.caption,
        "orientation": product.orientation,
        "recipe": product.recipe,
        "entrypoint": product.entrypoint,
        "web": {
            "media_path": web_entry(product.media_path),
            "preview_path": web_entry(product.preview_path),
            "maximum_asset_bytes": _DEFAULT_MAX_WEB_ASSET_BYTES,
        },
        "archive": {
            "status": "staged" if stage_archive else "inventory-only",
            "media_path": media_archive_path,
            "media_sha256": media_sha256,
            "preview_path": preview_archive_path,
            "preview_sha256": preview_sha256,
            "provenance_path": provenance_archive_path,
            "provenance_sha256": provenance_sha256,
            "supplemental": supplemental,
            "bundle_note": (
                "Bundle directories are intentionally not copied wholesale; canonical master and "
                "relief fields are selected above when present. Use the recipe and release "
                "manifest to reconstruct any remaining intermediate products."
            ),
            "source_media_path": product.media_path.relative_to(root).as_posix(),
        },
    }


def _release_inventory_html(inventory: dict[str, object]) -> str:
    products = inventory["products"]
    assert isinstance(products, list)
    rows = "".join(
        "<tr>"
        f"<td><code>{escape(str(product['id']))}</code></td>"
        f"<td>{escape(str(product['title']))}</td>"
        f"<td>{escape(', '.join(product['phase_slugs']))}</td>"
        f"<td>{escape(str(product['format']))}</td>"
        f"<td>{'web asset included' if product['web']['media_path'] else 'preview or archive only'}</td>"
        f"<td>{escape(str(product['archive']['status']))}</td>"
        "</tr>"
        for product in products
    )
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Kikuchi Atlas — release inventory</title><style>
:root {{ color-scheme: dark; font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background:#0d1217; color:#edf2f6; }}
body {{ max-width: 1280px; margin:0 auto; padding:2.2rem 1.5rem 4rem; }} a {{ color:#a9d7ff; }} .lede {{ max-width: 62rem; color:#c2ccd4; line-height:1.55; }}
table {{ width:100%; border-collapse:collapse; margin-top:1.5rem; }} th,td {{ border-bottom:1px solid #2e3d48; padding:.65rem; text-align:left; vertical-align:top; }} th {{ color:#b9c4cb; font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; }} code {{ color:#d8e6ef; }}
</style></head><body><nav><a href=\"index.html\">Kikuchi Atlas</a> · <a href=\"release-inventory.json\">machine-readable inventory</a></nav>
<h1>Release inventory</h1><p class=\"lede\">This is a pre-publication inventory of the Atlas release surface. The web gallery contains only browser-safe display assets. The companion archive staging area retains the selected original media and provenance files; full run directories remain recipe-reconstructible until a reviewed Zenodo payload is chosen.</p>
<p class=\"lede\"><strong>Claim boundary:</strong> {escape(str(inventory['claim_boundary']))}</p>
<table><thead><tr><th>ID</th><th>Product</th><th>Phase</th><th>Format</th><th>Web</th><th>Archive</th></tr></thead><tbody>{rows}</tbody></table>
</body></html>"""


def _write_archive_readme(archive_root: Path, inventory: dict[str, object]) -> None:
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_root.joinpath("README.md").write_text(
        "# Kikuchi Atlas archival-release staging\n\n"
        "This directory is generated locally for a later Zenodo or equivalent archival release. "
        "It contains selected product media, previews, provenance records, source registries, "
        "and recipes listed in `../release-inventory.json`. It deliberately does not copy every "
        "ignored run directory or intermediate frame: those are regenerated from the tracked code "
        "and listed recipes.\n\n"
        "Before publication, review licenses for each structural source, select a release version, "
        "add authors/citation metadata, and publish the generated checksums with the archive.\n\n"
        f"Claim boundary: {inventory['claim_boundary']}\n",
        encoding="utf-8",
    )


def _copy_tracked_release_context(
    *,
    root: Path,
    archive_root: Path,
    registry_path: Path,
    product_registry_path: Path,
    anchor_catalog_path: Path,
    products: Iterable[AtlasProduct],
    phase_source_records: Iterable[Path],
) -> None:
    """Copy the small tracked context that explains staged binary artifacts."""
    tracked_paths = [registry_path, product_registry_path, anchor_catalog_path, *phase_source_records]
    tracked_paths.extend(root / product.recipe for product in products)
    for source in tracked_paths:
        relative = source.relative_to(root)
        destination = archive_root / "tracked-context" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _rewrite_site_links(
    *,
    site_root: Path,
    web_paths: dict[Path, Path],
    all_local_paths: set[Path],
) -> None:
    """Replace local workspace links with web assets or the release inventory."""
    for page in sorted(site_root.rglob("*.html")):
        replacements: dict[str, str] = {}
        inventory_href = _relative_href(page, site_root / "release-inventory.html")
        for source in all_local_paths:
            old_href = _relative_href(page, source)
            target = web_paths.get(source)
            replacements[old_href] = _relative_href(page, target) if target else inventory_href
        html = page.read_text(encoding="utf-8")
        for old_href in sorted(replacements, key=len, reverse=True):
            html = html.replace(old_href, replacements[old_href])
        nav_link = f'<a href="{escape(inventory_href)}">Release inventory</a>'
        html = html.replace("</nav>", f"{nav_link}</nav>")
        if "local/" in html:
            raise ValueError(f"public Atlas page retains a local artifact link: {page}")
        page.write_text(html, encoding="utf-8")


def _reset_generated_output(output: Path) -> None:
    """Clear only the deterministic paths owned by a previous public build."""
    output.mkdir(parents=True, exist_ok=True)
    for name in ("site", "archive", "release-inventory.json"):
        path = output / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def build_public_atlas(
    *,
    registry_path: str | Path,
    product_registry_path: str | Path,
    anchor_catalog_path: str | Path,
    output_root: str | Path,
    stage_archive: bool = False,
    max_web_asset_bytes: int = _DEFAULT_MAX_WEB_ASSET_BYTES,
) -> PublicAtlasBuildResult:
    """Build a self-contained web gallery and optional local archival staging area.

    The public gallery accepts only image/SVG/MP4 files below the provider-safe
    asset ceiling. STL and higher-resolution scientific payloads are retained
    in the inventory and, when requested, copied to ``archive/`` for separate
    DOI-oriented publication rather than embedded in the website.
    """
    if max_web_asset_bytes <= 0:
        raise ValueError("max_web_asset_bytes must be positive")
    registry = Path(registry_path).resolve()
    product_registry = Path(product_registry_path).resolve()
    anchors = Path(anchor_catalog_path).resolve()
    root = registry.parents[2]
    phases = load_phase_registry(registry)
    _, products = load_product_registry(product_registry, phase_slugs={phase.slug for phase in phases})

    output = Path(output_root).resolve()
    _reset_generated_output(output)
    site_root = output / "site"
    archive_root = output / "archive"
    web_asset_root = site_root / "assets"
    archive_asset_root = archive_root / "artifacts"
    build_atlas(
        registry_path=registry,
        product_registry_path=product_registry,
        anchor_catalog_path=anchors,
        output_root=site_root,
    )

    web_paths: dict[Path, Path] = {}
    archive_paths: dict[Path, Path] = {}
    all_local_paths: set[Path] = set()
    for product in products:
        all_local_paths.update(
            path
            for path in (product.media_path, product.preview_path, product.bundle_path, product.provenance_path)
            if path is not None
        )
        for source in (product.media_path, product.preview_path):
            if source is not None and _web_safe(source, max_web_asset_bytes=max_web_asset_bytes):
                _copy_asset(source, web_asset_root, web_paths)
        if stage_archive:
            for source in _archive_sources(product):
                _copy_asset(source, archive_asset_root, archive_paths)
            for _, source in _supplemental_archive_sources(product):
                _copy_asset(source, archive_asset_root, archive_paths)

    inventory = {
        "schema_version": 1,
        "title": "Kikuchi Atlas public-release inventory",
        "claim_boundary": (
            "Gallery products are modeled visualizations and printable geometry; they are not "
            "acquired EBSD patterns or a validated dictionary-indexing dataset unless an explicit "
            "release says otherwise."
        ),
        "archive_staged": stage_archive,
        "web_asset_limit_bytes": max_web_asset_bytes,
        "products": [
            _product_inventory(
                product,
                root=root,
                site_root=site_root,
                archive_root=archive_root,
                web_paths=web_paths,
                archive_paths=archive_paths,
                stage_archive=stage_archive,
            )
            for product in products
        ],
    }
    inventory_path = output / "release-inventory.json"
    output.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (site_root / "release-inventory.html").write_text(
        _release_inventory_html(inventory), encoding="utf-8"
    )
    _rewrite_site_links(site_root=site_root, web_paths=web_paths, all_local_paths=all_local_paths)

    archive_assets: tuple[Path, ...] = tuple(sorted(archive_paths.values()))
    if stage_archive:
        phase_source_records = tuple(root / (phase.source_record or "") for phase in phases)
        _copy_tracked_release_context(
            root=root,
            archive_root=archive_root,
            registry_path=registry,
            product_registry_path=product_registry,
            anchor_catalog_path=anchors,
            products=products,
            phase_source_records=phase_source_records,
        )
        _write_archive_readme(archive_root, inventory)
        checksums = "".join(
            f"{_digest(path)}  {path.relative_to(archive_root).as_posix()}\n" for path in archive_assets
        )
        (archive_root / "checksums.sha256").write_text(checksums, encoding="utf-8")

    return PublicAtlasBuildResult(
        output_root=output,
        site_root=site_root,
        archive_root=archive_root,
        inventory_path=inventory_path,
        web_assets=tuple(sorted(web_paths.values())),
        archive_assets=archive_assets,
    )


__all__ = ["PublicAtlasBuildResult", "build_public_atlas"]

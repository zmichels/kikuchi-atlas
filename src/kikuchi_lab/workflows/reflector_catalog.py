"""Atomic publication workflow for phase-neutral reflector catalogs."""

from __future__ import annotations

import shutil
from pathlib import Path

from kikuchi_lab.reflectors import build_reflector_catalog, load_reflector_recipe
from kikuchi_lab.reflectors.bundle import (
    REFLECTOR_CATALOG_MANIFEST_SCHEMA,
    ReflectorCatalogBuildResult,
    catalog_ledger,
    catalog_payload,
    file_record,
    recipe_payload,
    run_id,
    run_identity,
)
from kikuchi_lab.relief.workflow import _fsync_tree, _publish_staging, _write_json
from kikuchi_lab.sources.structure import load_structure_record


_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _require_fresh_destinations(partial: Path, completed: Path) -> None:
    """Name catalog publication collisions while using the shared publish mechanics."""
    if completed.exists():
        raise FileExistsError(f"completed reflector catalog already exists: {completed}")
    if partial.exists():
        raise FileExistsError(f"partial reflector catalog already exists: {partial}")


def _result(run: str, completed: Path) -> ReflectorCatalogBuildResult:
    return ReflectorCatalogBuildResult(
        run_id=run,
        path=completed,
        catalog=completed / "reflector-catalog.json",
        recipe=completed / "catalog-recipe.json",
        ledger=completed / "catalog-ledger.json",
        manifest=completed / "manifest.json",
    )


def build_reflector_catalog_bundle(
    recipe_path: str | Path, output_root: str | Path
) -> ReflectorCatalogBuildResult:
    """Build a content-addressed, no-clobber reflector catalog bundle."""
    recipe = load_reflector_recipe(recipe_path)
    source = load_structure_record(_PROJECT_ROOT / recipe.source_record)
    catalog = build_reflector_catalog(source, recipe)
    run = run_id(catalog, recipe)
    root = Path(output_root).resolve()
    partial = root / f"{run}.partial"
    completed = root / run
    result = _result(run, completed)

    root.mkdir(parents=True, exist_ok=True)
    _require_fresh_destinations(partial, completed)
    partial.mkdir()
    try:
        _write_json(partial / "reflector-catalog.json", catalog_payload(catalog))
        _write_json(partial / "catalog-recipe.json", recipe_payload(recipe))
        _write_json(partial / "catalog-ledger.json", catalog_ledger(catalog, recipe, source))
        files = {
            path.name: file_record(path)
            for path in sorted(partial.iterdir(), key=lambda item: item.name)
            if path.is_file()
        }
        _write_json(
            partial / "manifest.json",
            {
                "schema": REFLECTOR_CATALOG_MANIFEST_SCHEMA,
                "run_id": run,
                "run_identity": run_identity(catalog, recipe),
                "catalog_id": catalog.catalog_id,
                "recipe_id": recipe.recipe_id,
                "catalog": "reflector-catalog.json",
                "recipe": "catalog-recipe.json",
                "ledger": "catalog-ledger.json",
                "files": files,
            },
        )
        expected = {
            "reflector-catalog.json",
            "catalog-recipe.json",
            "catalog-ledger.json",
            "manifest.json",
        }
        if {path.name for path in partial.iterdir()} != expected:
            raise RuntimeError("staged reflector catalog has an invalid export inventory")
        _fsync_tree(partial)
        _publish_staging(partial, completed, root)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return result

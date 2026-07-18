"""Plain-JSON payloads for immutable reflector-catalog bundles."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.reflectors.contracts import ReflectorCatalog
from kikuchi_lab.reflectors.recipe import ReflectorRecipe
from kikuchi_lab.sources.structure import StructureRecord


REFLECTOR_CATALOG_BUNDLE_SCHEMA = "kikuchi.reflector-catalog-bundle/v1"
REFLECTOR_CATALOG_MANIFEST_SCHEMA = "kikuchi.reflector-catalog-manifest/v1"
REFLECTOR_CATALOG_JSON_SERIALIZATION_CONTRACT = "json/sorted-indent-2-utf8-newline/v1"


@dataclass(frozen=True)
class ReflectorCatalogBuildResult:
    """Locations of one immutable published reflector-catalog bundle."""

    run_id: str
    path: Path
    catalog: Path
    recipe: Path
    ledger: Path
    manifest: Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a byte-for-byte durable payload."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    """Return the portable inventory record for one published JSON file."""
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}


def recipe_payload(recipe: ReflectorRecipe) -> dict[str, object]:
    """Materialize the path-independent recovered recipe snapshot."""
    return {"recipe_id": recipe.recipe_id, **asdict(recipe)}


def catalog_payload(catalog: ReflectorCatalog) -> dict[str, object]:
    """Convert contracts into a JSON-only public catalog, without upstream objects."""
    return {
        "catalog_id": catalog.catalog_id,
        "source_structure_id": catalog.source_structure_id,
        "source_structure_sha256": catalog.source_structure_sha256,
        "energy_kev": catalog.energy_kev,
        "reflection_recipe_id": catalog.reflection_recipe_id,
        "selection": plain_data(catalog.selection),
        "members": [
            {
                "member_id": member.member_id,
                "hkl": list(member.hkl),
                "normal_crystal": member.normal_crystal.tolist(),
                "dspacing_angstrom": member.dspacing_angstrom,
                "bragg_half_width_rad": member.bragg_half_width_rad,
                "structure_factor_abs": member.structure_factor_abs,
                "normalized_weight": member.normalized_weight,
                "eligible": member.eligible,
                "cohort": member.cohort,
            }
            for member in catalog.members
        ],
    }


def catalog_ledger(
    catalog: ReflectorCatalog, recipe: ReflectorRecipe, source: StructureRecord
) -> dict[str, object]:
    """Summarize the recovered selection policy and scientific claim boundary."""
    eligible = [member for member in catalog.members if member.eligible]
    blocks: list[float] = []
    for member in eligible:
        if not blocks or member.normalized_weight != blocks[-1]:
            blocks.append(member.normalized_weight)
    cohorts = {
        str(cohort): sum(member.cohort == cohort for member in eligible)
        for cohort in range(1, recipe.cohort_count + 1)
    }
    return {
        "schema": "kikuchi.reflector-catalog-ledger/v1",
        "catalog_id": catalog.catalog_id,
        "recipe_id": recipe.recipe_id,
        "source": {
            "structure_id": source.identifier,
            "checksum_sha256": source.sha256,
            "record": recipe.source_record,
        },
        "counts": {
            "total": len(catalog.members),
            "eligible": len(eligible),
            "eligible_weight_blocks": len(blocks),
        },
        "cohorts": cohorts,
        "threshold": recipe.eligibility_min_weight,
        "tie_policy": recipe.tie_policy,
        "public_package_versions": plain_data(catalog.selection["package_versions"]),
        "claim_boundary": (
            "This catalog characterizes only the COD-1572233 oxygen sublattice "
            "derivative: hydrogen sites are intentionally omitted. It makes no claim "
            "about proton ordering or the complete molecular ice-Ih structure."
        ),
    }


def run_identity(catalog: ReflectorCatalog, recipe: ReflectorRecipe) -> dict[str, Any]:
    """Return only path-neutral inputs to the immutable publication identity."""
    return {
        "bundle_schema": REFLECTOR_CATALOG_BUNDLE_SCHEMA,
        "json_serialization": REFLECTOR_CATALOG_JSON_SERIALIZATION_CONTRACT,
        "catalog_id": catalog.catalog_id,
        "recipe_id": recipe.recipe_id,
        "source_checksum_sha256": catalog.source_structure_sha256,
    }


def run_id(catalog: ReflectorCatalog, recipe: ReflectorRecipe) -> str:
    """Derive a stable run identifier from scientific content, never local paths."""
    return stable_id("reflector-catalog-build", run_identity(catalog, recipe))

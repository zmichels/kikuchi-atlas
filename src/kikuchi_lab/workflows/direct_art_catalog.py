"""Zero-master direct-reflector catalog workflow."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.contracts import ArtBandCatalog
from kikuchi_lab.art_products.direct_catalog_bundle import (
    DirectArtCatalogBundleResult,
    write_direct_art_catalog_bundle,
)
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    build_direct_reflector_evidence,
)
from kikuchi_lab.kinematical.reflector_evidence import (
    DirectReflectorEvidence,
    load_direct_reflector_recipe,
)
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


@dataclass(frozen=True)
class DirectArtCatalogResult:
    """Published content identities and finite-work counts."""

    run_id: str
    path: Path
    catalog_id: str
    evidence_id: str
    member_count: int
    eligible_member_count: int
    simulation_count: int
    manifest_sha256: str
    elapsed_seconds: float

    @classmethod
    def from_bundle(
        cls,
        bundle: DirectArtCatalogBundleResult,
        catalog: ArtBandCatalog,
        evidence: DirectReflectorEvidence,
        started: float,
    ) -> DirectArtCatalogResult:
        return cls(
            run_id=bundle.run_id,
            path=bundle.path,
            catalog_id=catalog.catalog_id,
            evidence_id=evidence.evidence_id,
            member_count=len(catalog.members),
            eligible_member_count=sum(member.tattoo_eligible for member in catalog.members),
            simulation_count=int(evidence.ledger["simulation_count"]),
            manifest_sha256=bundle.manifest_sha256,
            elapsed_seconds=time.monotonic() - started,
        )


def build_direct_art_catalog(
    *, recipe_path: str | Path, output_root: str | Path
) -> DirectArtCatalogResult:
    """Calculate direct reflector evidence and publish its art catalog."""
    started = time.monotonic()
    recipe_file = Path(recipe_path).resolve()
    recipe = load_direct_reflector_recipe(recipe_file)
    source_path = (recipe_file.parent / recipe.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)
    print(
        "direct-art-catalog finite-work simulation_count=0 "
        f"phase={source.name} min_dspacing_angstrom={recipe.min_dspacing_angstrom}",
        file=sys.stderr,
        flush=True,
    )
    evidence = build_direct_reflector_evidence(source, recipe)
    catalog = build_art_band_catalog_from_evidence(evidence)
    bundle = write_direct_art_catalog_bundle(
        output_root,
        source=source,
        recipe=recipe,
        evidence=evidence,
        catalog=catalog,
    )
    return DirectArtCatalogResult.from_bundle(bundle, catalog, evidence, started)


__all__ = ["DirectArtCatalogResult", "build_direct_art_catalog"]

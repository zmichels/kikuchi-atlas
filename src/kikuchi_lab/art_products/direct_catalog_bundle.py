"""Preflighted atomic publication of zero-master direct art catalogs."""

from __future__ import annotations

import errno
import hashlib
import io
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
    _write_bytes,
    _write_json,
)
from kikuchi_lab.kinematical.reflector_evidence import (
    DirectReflectorEvidence,
    DirectReflectorRecipe,
)
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id
from kikuchi_lab.sources.structure import StructureRecord, verify_structure

from .catalog import build_art_band_catalog_from_evidence
from .contracts import ArtBandCatalog


_SCIENTIFIC_CLAIM = (
    "Scientific claim: presentation-only science art derived from "
    "orientation-independent reflector evidence. No master-pattern simulation "
    "was calculated for this catalog. Band weights are normalized structure-factor "
    "rankings, not detector intensity or literal physical relief.\n"
)
_NPZ_DTYPES = {
    "bragg_half_width_rad": np.dtype("<f8"),
    "dspacing_angstrom": np.dtype("<f8"),
    "hkl": np.dtype("<i4"),
    "normal_crystal": np.dtype("<f8"),
    "normalized_weight": np.dtype("<f8"),
    "structure_factor_magnitude": np.dtype("<f8"),
}


@dataclass(frozen=True)
class DirectArtCatalogBundleResult:
    """Identity and path of one immutable direct-catalog bundle."""

    run_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class _ValidatedPayload:
    run_identity: dict[str, object]
    catalog_snapshot: dict[str, object]
    recipe_snapshot: dict[str, object]
    evidence_ledger: dict[str, object]
    catalog_ledger: dict[str, object]
    evidence: DirectReflectorEvidence


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_recipe_ids(recipe: DirectReflectorRecipe) -> None:
    expected_calculation_id = stable_id(
        "reflector-calculation",
        {
            "energy_kev": recipe.energy_kev,
            "min_dspacing_angstrom": recipe.min_dspacing_angstrom,
            "scattering_params": recipe.scattering_params,
            "candidate_relative_factor": recipe.candidate_relative_factor,
        },
    )
    expected_weighting_id = stable_id(
        "reflector-weighting",
        {
            "weight_exponent": recipe.weight_exponent,
            "eligibility_min_weight": recipe.eligibility_min_weight,
        },
    )
    if recipe.calculation_id != expected_calculation_id:
        raise ValueError("direct recipe calculation_id does not match its content")
    if recipe.weighting_id != expected_weighting_id:
        raise ValueError("direct recipe weighting_id does not match its content")


def _validate_evidence_order(evidence: DirectReflectorEvidence) -> None:
    hkls = [tuple(int(index) for index in row) for row in evidence.hkl]
    if hkls != sorted(hkls):
        raise ValueError("direct reflector evidence HKLs are not canonically sorted")
    for key, dtype in _NPZ_DTYPES.items():
        if np.asarray(getattr(evidence, key)).dtype != dtype:
            raise ValueError(f"direct reflector evidence {key} dtype must be {dtype.str}")


def _validated_payload(
    *,
    source: StructureRecord,
    recipe: DirectReflectorRecipe,
    evidence: DirectReflectorEvidence,
    catalog: ArtBandCatalog,
) -> _ValidatedPayload:
    expected_types = (
        (source, StructureRecord, "source"),
        (recipe, DirectReflectorRecipe, "recipe"),
        (evidence, DirectReflectorEvidence, "evidence"),
        (catalog, ArtBandCatalog, "catalog"),
    )
    for value, expected, name in expected_types:
        if not isinstance(value, expected):
            raise TypeError(f"{name} must be a {expected.__name__}")

    _validate_recipe_ids(recipe)
    if evidence.source_structure_id != source.identifier:
        raise ValueError("evidence source structure ID does not match the supplied source")
    if evidence.source_structure_sha256 != source.sha256:
        raise ValueError("evidence source structure SHA does not match the supplied source")
    if evidence.calculation_id != recipe.calculation_id:
        raise ValueError("evidence calculation ID does not match the supplied recipe")
    if evidence.weighting_id != recipe.weighting_id:
        raise ValueError("evidence weighting ID does not match the supplied recipe")
    if evidence.ledger.get("simulation_count") != 0:
        raise ValueError("direct reflector evidence simulation_count must be 0")
    expected_evidence_id = stable_id("reflector-evidence", evidence.identity_dict())
    if evidence.evidence_id != expected_evidence_id:
        raise ValueError("evidence_id does not match evidence content")
    _validate_evidence_order(evidence)

    expected_catalog_id = stable_id("art-band-catalog", catalog.to_dict())
    if catalog.catalog_id != expected_catalog_id:
        raise ValueError("catalog_id does not match catalog content")
    for index, member in enumerate(catalog.members):
        expected_member_id = stable_id("art-band-member", member.intrinsic_dict())
        if member.member_id != expected_member_id:
            raise ValueError(f"catalog member {index} member_id does not match its content")
    eligible_member_count = sum(member.tattoo_eligible for member in catalog.members)
    if eligible_member_count < 11:
        raise ValueError("direct catalog requires at least 11 tattoo-eligible members")
    expected_catalog = build_art_band_catalog_from_evidence(evidence)
    if canonical_json(catalog.to_dict()) != canonical_json(expected_catalog.to_dict()):
        raise ValueError("catalog content does not match the supplied reflector evidence")
    if catalog.catalog_id != expected_catalog.catalog_id:
        raise ValueError("catalog ID does not match the supplied reflector evidence")

    verify_structure(source)
    recipe_snapshot = {
        "calculation_id": recipe.calculation_id,
        "content": recipe.to_dict(),
        "weighting_id": recipe.weighting_id,
    }
    evidence_ledger = {
        "schema_version": 1,
        "evidence_id": evidence.evidence_id,
        "source_structure_id": source.identifier,
        "source_structure_sha256": source.sha256,
        "calculation_id": recipe.calculation_id,
        "weighting_id": recipe.weighting_id,
        "ledger": plain_data(evidence.ledger),
    }
    catalog_ledger = {
        "schema_version": 1,
        "catalog_id": catalog.catalog_id,
        "evidence_id": evidence.evidence_id,
        "source_structure_id": source.identifier,
        "source_structure_sha256": source.sha256,
        "calculation_id": recipe.calculation_id,
        "weighting_id": recipe.weighting_id,
        "member_count": len(catalog.members),
        "eligible_member_count": eligible_member_count,
        "simulation_count": 0,
        "scientific_claim": "presentation_only",
        "orientation_dependency": "none",
    }
    run_identity = {
        "schema_version": 1,
        "source_structure_id": source.identifier,
        "source_structure_sha256": source.sha256,
        "calculation_id": recipe.calculation_id,
        "weighting_id": recipe.weighting_id,
        "evidence_id": evidence.evidence_id,
        "catalog_id": catalog.catalog_id,
        "evidence_ledger_id": stable_id("reflector-evidence-ledger", evidence_ledger),
        "catalog_ledger_id": stable_id("catalog-ledger", catalog_ledger),
    }
    return _ValidatedPayload(
        run_identity=run_identity,
        catalog_snapshot={"catalog_id": catalog.catalog_id, "content": catalog.to_dict()},
        recipe_snapshot=recipe_snapshot,
        evidence_ledger=evidence_ledger,
        catalog_ledger=catalog_ledger,
        evidence=evidence,
    )


def _write_evidence_npz(path: Path, evidence: DirectReflectorEvidence) -> None:
    arrays = {
        key: np.asarray(getattr(evidence, key), dtype=dtype, order="C")
        for key, dtype in _NPZ_DTYPES.items()
    }
    with path.open("wb") as handle:
        with zipfile.ZipFile(handle, mode="w") as archive:
            for key in sorted(arrays):
                payload = io.BytesIO()
                np.lib.format.write_array(payload, arrays[key], allow_pickle=False)
                info = zipfile.ZipInfo(
                    f"{key}.npy",
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o600 << 16
                archive.writestr(info, payload.getvalue())
        handle.flush()
        os.fsync(handle.fileno())


def _write_contents(root: Path, payload: _ValidatedPayload) -> dict[str, dict[str, object]]:
    _write_json(root / "art-band-catalog.json", payload.catalog_snapshot)
    _write_json(root / "direct-reflector-recipe.json", payload.recipe_snapshot)
    _write_evidence_npz(root / "reflector-evidence.npz", payload.evidence)
    _write_json(root / "reflector-evidence-ledger.json", payload.evidence_ledger)
    _write_json(root / "catalog-ledger.json", payload.catalog_ledger)
    _write_bytes(root / "scientific-claim.txt", _SCIENTIFIC_CLAIM.encode("utf-8"))
    return {
        str(path.relative_to(root)): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_direct_art_catalog_bundle(
    output_root: str | Path,
    source: StructureRecord,
    recipe: DirectReflectorRecipe,
    evidence: DirectReflectorEvidence,
    catalog: ArtBandCatalog,
) -> DirectArtCatalogBundleResult:
    """Validate all identities, then atomically publish one direct catalog."""
    payload = _validated_payload(
        source=source,
        recipe=recipe,
        evidence=evidence,
        catalog=catalog,
    )
    run_id = stable_id("direct-art-catalog-run", payload.run_identity)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    ownership = root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}") from None
        raise PartialBundleError(f"same-run publication already in progress: {ownership}") from None

    try:
        _fsync_directory(root)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        existing_partials = sorted(root.glob(f".{run_id}.partial-*"))
        if existing_partials:
            raise PartialBundleError(f"partial bundle already exists: {existing_partials[0]}")
        partial = root / f".{run_id}.partial-{uuid4().hex}"
        try:
            partial.mkdir()
        except FileExistsError:
            raise PartialBundleError(f"partial bundle already exists: {partial}") from None

        files = _write_contents(partial, payload)
        manifest_path = partial / "manifest.json"
        _write_json(
            manifest_path,
            {
                "schema_version": 1,
                "run_id": run_id,
                "run_identity": payload.run_identity,
                "files": files,
            },
        )
        manifest_sha256 = _sha256(manifest_path)
        _fsync_directory_tree(partial)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        try:
            _promote_directory_no_replace(partial, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise BundleExistsError(f"completed bundle already exists: {completed}") from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return DirectArtCatalogBundleResult(
            run_id=run_id,
            path=completed,
            manifest_sha256=manifest_sha256,
        )
    finally:
        ownership.rmdir()
        _fsync_directory(root)


__all__ = [
    "DirectArtCatalogBundleResult",
    "write_direct_art_catalog_bundle",
]

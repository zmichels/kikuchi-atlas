"""Preflighted atomic publication of one shared Ice art-band catalog."""

from __future__ import annotations

import errno
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
    _write_bytes,
    _write_json,
)
from kikuchi_lab.kinematical.contracts import KinematicalRecipe
from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.near_depth.contracts import NearDepthTreatmentRecipe
from kikuchi_lab.sources.structure import StructureRecord, verify_structure
from kikuchi_lab.spherical_intensity.contracts import SphericalIntensityRecipe
from kikuchi_lab.spherical_intensity.orientation import OrientedSphericalRecipe

from .catalog import _assign_cohorts
from .contracts import ArtBandCatalog


_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_CLAIM_BOUNDARIES = {
    "product_class": "science_art",
    "scientific_claim": "presentation_only",
    "globe_height": (
        "designed tier encoding; not a physical mineral surface or direct "
        "electron-density scale"
    ),
    "tattoo_stroke_width": (
        "graphic rank encoding; not literal Bragg width, detector intensity, "
        "or medical tattooing prescription"
    ),
}


@dataclass(frozen=True)
class IceArtCatalogRecipe:
    """Strict version-1 policy for the shared Ice science-art catalog."""

    schema_version: int
    name: str
    source_oriented_recipe: str
    eligibility_min_weight: float
    globe_cohort_count: int
    tie_policy: str
    ranking: str
    scientific_claim: str
    product_class: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("catalog recipe schema_version must be integer 1")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("catalog recipe name must be non-empty text")
        source_path = self.source_oriented_recipe
        if (
            not isinstance(source_path, str)
            or not source_path.strip()
            or Path(source_path).is_absolute()
            or _WINDOWS_ABSOLUTE_PATH.match(source_path)
            or source_path.startswith("\\\\")
        ):
            raise ValueError("catalog recipe source_oriented_recipe must be a relative path")
        if (
            isinstance(self.eligibility_min_weight, bool)
            or not isinstance(self.eligibility_min_weight, (int, float))
            or not math.isfinite(self.eligibility_min_weight)
            or float(self.eligibility_min_weight) != 0.08
        ):
            raise ValueError("catalog recipe eligibility_min_weight must be exactly 0.08")
        if type(self.globe_cohort_count) is not int or self.globe_cohort_count != 4:
            raise ValueError("catalog recipe globe_cohort_count must be integer 4")
        expected = {
            "tie_policy": "keep_equal_weights_together",
            "ranking": "normalized_structure_factor_weight",
            "scientific_claim": "presentation_only",
            "product_class": "science_art",
        }
        for field, value in expected.items():
            if getattr(self, field) != value:
                raise ValueError(f"catalog recipe {field} must be {value}")
        object.__setattr__(self, "eligibility_min_weight", 0.08)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_oriented_recipe": self.source_oriented_recipe,
            "eligibility_min_weight": self.eligibility_min_weight,
            "globe_cohort_count": self.globe_cohort_count,
            "tie_policy": self.tie_policy,
            "ranking": self.ranking,
            "scientific_claim": self.scientific_claim,
            "product_class": self.product_class,
        }

    @property
    def recipe_id(self) -> str:
        payload = self.to_dict()
        del payload["source_oriented_recipe"]
        return stable_id("recipe", payload)


@dataclass(frozen=True)
class ArtCatalogBundleResult:
    """Published identity and location for one immutable catalog bundle."""

    run_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class _ValidatedPayload:
    run_identity: dict[str, object]
    catalog_snapshot: dict[str, object]
    catalog_recipe: dict[str, object]
    catalog_ledger: dict[str, object]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_catalog_members(catalog: ArtBandCatalog) -> dict[str, int]:
    ordering = [
        (-member.normalized_weight, member.hkl, member.member_id)
        for member in catalog.members
    ]
    if ordering != sorted(ordering):
        raise ValueError("catalog member ordering is not canonical")
    threshold = catalog.eligibility_min_weight
    eligible_members = []
    cohort_counts = {cohort: 0 for cohort in (1, 2, 3, 4)}
    for index, member in enumerate(catalog.members):
        expected_member_id = stable_id("art-band-member", member.intrinsic_dict())
        if member.member_id != expected_member_id:
            raise ValueError(f"catalog member {index} member_id does not match its content")
        eligible = member.normalized_weight >= threshold
        if member.globe_eligible is not eligible or member.tattoo_eligible is not eligible:
            raise ValueError("catalog member eligibility does not match the catalog threshold")
        if eligible:
            if member.globe_cohort not in cohort_counts:
                raise ValueError("eligible catalog member lacks a globe cohort")
            cohort_counts[member.globe_cohort] += 1
            eligible_members.append(member)
        elif member.globe_cohort is not None:
            raise ValueError("ineligible catalog member must not have a globe cohort")
    if any(count == 0 for count in cohort_counts.values()):
        raise ValueError("catalog requires four nonempty globe cohorts")
    expected_cohorts = _assign_cohorts(eligible_members)
    if any(
        member.globe_cohort != expected_cohorts[member.member_id]
        for member in eligible_members
    ):
        raise ValueError(
            "catalog globe cohort assignment does not match deterministic catalog policy"
        )
    return {str(cohort): count for cohort, count in cohort_counts.items()}


def _validated_payload(
    *,
    catalog: ArtBandCatalog,
    catalog_recipe: IceArtCatalogRecipe,
    oriented_recipe: OrientedSphericalRecipe,
    spherical_recipe: SphericalIntensityRecipe,
    source_recipe: KinematicalRecipe,
    presentation_recipe: NearDepthTreatmentRecipe,
    source: StructureRecord,
) -> _ValidatedPayload:
    expected_types = (
        (catalog, ArtBandCatalog, "catalog"),
        (catalog_recipe, IceArtCatalogRecipe, "catalog_recipe"),
        (oriented_recipe, OrientedSphericalRecipe, "oriented_recipe"),
        (spherical_recipe, SphericalIntensityRecipe, "spherical_recipe"),
        (source_recipe, KinematicalRecipe, "source_recipe"),
        (presentation_recipe, NearDepthTreatmentRecipe, "presentation_recipe"),
        (source, StructureRecord, "source"),
    )
    for value, expected, name in expected_types:
        if not isinstance(value, expected):
            raise TypeError(f"{name} must be a {expected.__name__}")

    expected_catalog_id = stable_id("art-band-catalog", catalog.to_dict())
    if catalog.catalog_id != expected_catalog_id:
        raise ValueError("catalog_id does not match catalog content")
    if catalog.source_structure_id != source.identifier:
        raise ValueError("catalog source structure ID does not match the supplied source")
    if catalog.source_structure_sha256 != source.sha256:
        raise ValueError("catalog source structure SHA does not match the supplied source")
    if catalog.source_recipe_id != source_recipe.recipe_id:
        raise ValueError("catalog source recipe ID does not match the supplied source recipe")
    if catalog.presentation_recipe_id != presentation_recipe.recipe_id:
        raise ValueError(
            "catalog presentation recipe ID does not match the supplied presentation recipe"
        )
    if presentation_recipe.expected_kinematical_recipe_id != source_recipe.recipe_id:
        raise ValueError("presentation recipe does not identify the supplied source recipe")
    if catalog.eligibility_min_weight != catalog_recipe.eligibility_min_weight:
        raise ValueError("catalog threshold does not match the catalog recipe")
    if oriented_recipe.profile.name != "smoke" or spherical_recipe.profile.name != "smoke":
        raise ValueError("catalog publication requires the bounded smoke recipes")
    if oriented_recipe.profile.source_half_size != spherical_recipe.profile.half_size:
        raise ValueError("oriented and spherical smoke bounds do not match")
    if source_recipe.hemisphere != "both":
        raise ValueError("catalog source recipe must contain both hemispheres")
    if source_recipe.orientation.euler_bunge_deg != (0.0, 0.0, 0.0):
        raise ValueError("catalog source recipe must use the identity orientation")
    verify_structure(source)
    cohort_counts = _validate_catalog_members(catalog)

    catalog_recipe_payload = plain_data(catalog_recipe.to_dict())
    if not isinstance(catalog_recipe_payload, dict):
        raise TypeError("catalog recipe snapshot must be a mapping")
    catalog_snapshot = {
        "catalog_id": catalog.catalog_id,
        "content": catalog.to_dict(),
    }
    catalog_ledger = {
        "schema_version": 1,
        "source": {
            "structure_id": source.identifier,
            "structure_sha256": source.sha256,
        },
        "recipe_ids": {
            "catalog_recipe_id": catalog_recipe.recipe_id,
            "oriented_recipe_id": oriented_recipe.recipe_id,
            "spherical_recipe_id": spherical_recipe.recipe_id,
            "source_recipe_id": source_recipe.recipe_id,
            "presentation_recipe_id": presentation_recipe.recipe_id,
        },
        "catalog": {
            "catalog_id": catalog.catalog_id,
            "member_count": len(catalog.members),
            "globe_eligible_member_count": sum(
                member.globe_eligible for member in catalog.members
            ),
            "tattoo_eligible_member_count": sum(
                member.tattoo_eligible for member in catalog.members
            ),
            "globe_cohort_member_counts": cohort_counts,
        },
        "policies": {
            "eligibility_min_weight": catalog_recipe.eligibility_min_weight,
            "globe_cohort_count": catalog_recipe.globe_cohort_count,
            "tie_policy": catalog_recipe.tie_policy,
            "ranking": catalog_recipe.ranking,
        },
        "claim_boundaries": _CLAIM_BOUNDARIES,
    }
    run_identity = {
        "schema_version": 1,
        "source_structure_id": source.identifier,
        "source_structure_sha256": source.sha256,
        "catalog_recipe_id": catalog_recipe.recipe_id,
        "oriented_recipe_id": oriented_recipe.recipe_id,
        "spherical_recipe_id": spherical_recipe.recipe_id,
        "source_recipe_id": source_recipe.recipe_id,
        "presentation_recipe_id": presentation_recipe.recipe_id,
        "catalog_id": catalog.catalog_id,
        "catalog_ledger_id": stable_id("catalog-ledger", catalog_ledger),
    }
    return _ValidatedPayload(
        run_identity=run_identity,
        catalog_snapshot=catalog_snapshot,
        catalog_recipe=catalog_recipe_payload,
        catalog_ledger=catalog_ledger,
    )


def _pretty_json_bytes(value: object) -> bytes:
    return (json.dumps(plain_data(value), indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _write_contents(root: Path, payload: _ValidatedPayload) -> dict[str, dict[str, object]]:
    _write_bytes(
        root / "art-band-catalog.json",
        _pretty_json_bytes(payload.catalog_snapshot),
    )
    _write_bytes(
        root / "catalog-recipe.json",
        _pretty_json_bytes(payload.catalog_recipe),
    )
    _write_json(root / "catalog-ledger.json", payload.catalog_ledger)
    return {
        str(path.relative_to(root)): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_art_catalog_bundle(
    output_root: str | Path,
    *,
    catalog: ArtBandCatalog,
    catalog_recipe: IceArtCatalogRecipe,
    oriented_recipe: OrientedSphericalRecipe,
    spherical_recipe: SphericalIntensityRecipe,
    source_recipe: KinematicalRecipe,
    presentation_recipe: NearDepthTreatmentRecipe,
    source: StructureRecord,
) -> ArtCatalogBundleResult:
    """Validate then atomically publish one path-neutral catalog bundle."""
    payload = _validated_payload(
        catalog=catalog,
        catalog_recipe=catalog_recipe,
        oriented_recipe=oriented_recipe,
        spherical_recipe=spherical_recipe,
        source_recipe=source_recipe,
        presentation_recipe=presentation_recipe,
        source=source,
    )
    run_id = stable_id("ice-art-catalog-run", payload.run_identity)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    ownership = root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}") from None
        raise PartialBundleError(
            f"same-run publication already in progress: {ownership}"
        ) from None

    try:
        _fsync_directory(root)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        existing_partials = sorted(root.glob(f".{run_id}.partial-*"))
        if existing_partials:
            raise PartialBundleError(
                f"partial bundle already exists: {existing_partials[0]}"
            )
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
                raise BundleExistsError(
                    f"completed bundle already exists: {completed}"
                ) from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return ArtCatalogBundleResult(
            run_id=run_id,
            path=completed,
            manifest_sha256=manifest_sha256,
        )
    finally:
        ownership.rmdir()
        _fsync_directory(root)


__all__ = [
    "ArtCatalogBundleResult",
    "IceArtCatalogRecipe",
    "write_art_catalog_bundle",
]

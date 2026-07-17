"""Versioned HKL manifests that rebind reviewed art to corrected evidence."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from kikuchi_lab.art_products.contracts import ArtBandCatalog, TattooTier
from kikuchi_lab.art_products.tattoo_selection import (
    HemisphereSelectionRecipe,
    SelectedTattooPath,
    TattooCandidate,
    TattooSelection,
    _center_trace,
    _midpoint_sector,
)
from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


_MANIFEST_FIELDS = {
    "schema_version",
    "name",
    "phase_slug",
    "source_structure_id",
    "source_structure_sha256",
    "orientation_id",
    "legacy_catalog_id",
    "legacy_selection_id",
    "policy",
    "paths",
}
_PATH_FIELDS = {"hkl", "tier", "width_mm", "legacy_member_id"}
_POLICY = "reviewed_hkl_rebind_under_corrected_physics"
_TIERS: tuple[TattooTier, ...] = ("dominant", "secondary", "fine")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PHASE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"frozen selection {field} must be non-empty text")
    return value


def _exact_mapping(value: object, fields: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"frozen selection {label} fields differ from the schema")
    return value


def _canonical_hkl(value: object) -> tuple[int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(type(component) is not int for component in value)
    ):
        raise ValueError("frozen selection HKL must contain three integers")
    hkl = tuple(value)
    nonzero = next((component for component in hkl if component != 0), None)
    if nonzero is None:
        raise ValueError("frozen selection HKL must be nonzero")
    if nonzero < 0:
        raise ValueError(
            "frozen selection HKL must use the canonical first-nonzero-positive sign"
        )
    return hkl


def _positive_width(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("frozen selection width_mm must be a number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError("frozen selection width_mm must be positive and finite")
    return result


@dataclass(frozen=True)
class FrozenTattooPath:
    """One reviewed axial plane and its deliberately preserved visual role."""

    hkl: tuple[int, int, int]
    tier: TattooTier
    width_mm: float
    legacy_member_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.hkl, tuple):
            raise ValueError("frozen selection HKL must be an immutable tuple")
        object.__setattr__(self, "hkl", _canonical_hkl(list(self.hkl)))
        if self.tier not in _TIERS:
            raise ValueError("frozen selection tier must be dominant, secondary, or fine")
        object.__setattr__(self, "width_mm", _positive_width(self.width_mm))
        object.__setattr__(
            self,
            "legacy_member_id",
            _text(self.legacy_member_id, "legacy_member_id"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "hkl": list(self.hkl),
            "tier": self.tier,
            "width_mm": self.width_mm,
            "legacy_member_id": self.legacy_member_id,
        }


@dataclass(frozen=True)
class FrozenTattooSelection:
    """Auditable migration contract from reviewed HKLs to corrected evidence."""

    schema_version: int
    name: str
    phase_slug: str
    source_structure_id: str
    source_structure_sha256: str
    orientation_id: str
    legacy_catalog_id: str
    legacy_selection_id: str
    policy: str
    paths: tuple[FrozenTattooPath, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("frozen selection schema_version must be integer 1")
        for field in (
            "name",
            "source_structure_id",
            "orientation_id",
            "legacy_catalog_id",
            "legacy_selection_id",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        phase_slug = _text(self.phase_slug, "phase_slug")
        if _PHASE_SLUG.fullmatch(phase_slug) is None:
            raise ValueError("frozen selection phase_slug is invalid")
        if not isinstance(self.source_structure_sha256, str) or _SHA256.fullmatch(
            self.source_structure_sha256
        ) is None:
            raise ValueError("frozen selection source_structure_sha256 must be SHA-256")
        if self.policy != _POLICY:
            raise ValueError(f"frozen selection policy must be exactly {_POLICY}")
        paths = tuple(self.paths)
        if len(paths) != 11 or any(not isinstance(path, FrozenTattooPath) for path in paths):
            raise ValueError("frozen selection must contain exactly 11 paths")
        if len({path.hkl for path in paths}) != len(paths):
            raise ValueError("frozen selection HKLs must be unique")
        if len({path.legacy_member_id for path in paths}) != len(paths):
            raise ValueError("frozen selection legacy member IDs must be unique")
        object.__setattr__(self, "paths", paths)

    @property
    def ordered_hkls(self) -> tuple[tuple[int, int, int], ...]:
        return tuple(path.hkl for path in self.paths)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "phase_slug": self.phase_slug,
            "source_structure_id": self.source_structure_id,
            "source_structure_sha256": self.source_structure_sha256,
            "orientation_id": self.orientation_id,
            "legacy_catalog_id": self.legacy_catalog_id,
            "legacy_selection_id": self.legacy_selection_id,
            "policy": self.policy,
            "paths": [path.to_dict() for path in self.paths],
        }

    @property
    def manifest_id(self) -> str:
        return stable_id("frozen-tattoo-selection", self.to_dict())


def load_frozen_tattoo_selection(path: str | Path) -> FrozenTattooSelection:
    """Load and strictly validate one reviewed-HKL migration manifest."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("frozen selection YAML is invalid") from None
    root = _exact_mapping(payload, _MANIFEST_FIELDS, "manifest")
    raw_paths = root["paths"]
    if not isinstance(raw_paths, list):
        raise ValueError("frozen selection paths must be a list")
    paths: list[FrozenTattooPath] = []
    for raw_path in raw_paths:
        item = _exact_mapping(raw_path, _PATH_FIELDS, "path")
        paths.append(
            FrozenTattooPath(
                hkl=_canonical_hkl(item["hkl"]),
                tier=item["tier"],
                width_mm=item["width_mm"],
                legacy_member_id=item["legacy_member_id"],
            )
        )
    return FrozenTattooSelection(
        schema_version=root["schema_version"],
        name=root["name"],
        phase_slug=root["phase_slug"],
        source_structure_id=root["source_structure_id"],
        source_structure_sha256=root["source_structure_sha256"],
        orientation_id=root["orientation_id"],
        legacy_catalog_id=root["legacy_catalog_id"],
        legacy_selection_id=root["legacy_selection_id"],
        policy=root["policy"],
        paths=tuple(paths),
    )


def bind_frozen_tattoo_selection(
    catalog: ArtBandCatalog,
    recipe: HemisphereSelectionRecipe,
    manifest: FrozenTattooSelection,
) -> TattooSelection:
    """Rebind reviewed HKLs to a corrected catalog without automatic reselection."""
    if not isinstance(catalog, ArtBandCatalog):
        raise TypeError("catalog must be an ArtBandCatalog")
    if not isinstance(recipe, HemisphereSelectionRecipe):
        raise TypeError("recipe must satisfy HemisphereSelectionRecipe")
    if not isinstance(manifest, FrozenTattooSelection):
        raise TypeError("manifest must be a FrozenTattooSelection")
    if (
        catalog.source_structure_id != manifest.source_structure_id
        or catalog.source_structure_sha256 != manifest.source_structure_sha256
    ):
        raise ValueError("corrected catalog does not match the frozen selection source")
    if recipe.orientation.orientation_id != manifest.orientation_id:
        raise ValueError("tattoo recipe orientation does not match the frozen selection")

    expected_assignments = tuple(
        (tier, width)
        for tier in _TIERS
        for width in recipe.stroke_widths_mm[tier]
    )
    assignments = tuple((path.tier, path.width_mm) for path in manifest.paths)
    if assignments != expected_assignments:
        raise ValueError("frozen selection tier/width order differs from the tattoo recipe")

    by_hkl = {member.hkl: member for member in catalog.members}
    rebound = []
    for path in manifest.paths:
        member = by_hkl.get(path.hkl)
        if member is None or not member.tattoo_eligible:
            raise ValueError(f"reviewed HKL {path.hkl} must remain present and eligible")
        rebound.append((path, member))

    rotation = orientation_matrix(recipe.orientation)
    max_half_width = max(member.bragg_half_width_rad for _, member in rebound)
    candidates: list[TattooCandidate] = []
    selected_paths: list[SelectedTattooPath] = []
    rebindings: list[dict[str, object]] = []
    for path, member in rebound:
        normal_sample = rotation @ member.normal_crystal
        circle, trace = _center_trace(normal_sample, recipe.great_circle_samples)
        candidate = TattooCandidate(
            member_id=member.member_id,
            hkl=member.hkl,
            normalized_weight=member.normalized_weight,
            bragg_half_width_rad=member.bragg_half_width_rad,
            normal_crystal=member.normal_crystal,
            normal_sample=normal_sample,
            great_circle_sample=circle,
            center_trace=trace,
            midpoint_sector=_midpoint_sector(trace, recipe.coverage_sectors),
        )
        components = {
            "strength": member.normalized_weight,
            "angular_width": member.bragg_half_width_rad / max_half_width,
            "nonredundancy": 1.0,
            "coverage": 0.0,
            "zone_relationship": 0.0,
        }
        total = sum(recipe.score_weights[name] * value for name, value in components.items())
        candidates.append(candidate)
        selected_paths.append(
            SelectedTattooPath(
                member_id=member.member_id,
                tier=path.tier,
                width_mm=path.width_mm,
                normal_sample=normal_sample,
                center_trace=trace,
                score_components=components,
                total_score=total,
                selection_reason="reviewed canonical HKL rebound to corrected evidence",
            )
        )
        rebindings.append(
            {
                "hkl": list(path.hkl),
                "legacy_member_id": path.legacy_member_id,
                "corrected_member_id": member.member_id,
                "normalized_weight": member.normalized_weight,
                "tattoo_eligible": member.tattoo_eligible,
            }
        )

    ledger = {
        "schema_version": 1,
        "selection_mode": manifest.policy,
        "frozen_manifest_id": manifest.manifest_id,
        "legacy_catalog_id": manifest.legacy_catalog_id,
        "legacy_selection_id": manifest.legacy_selection_id,
        "corrected_catalog_id": catalog.catalog_id,
        "orientation_id": recipe.orientation.orientation_id,
        "ordered_hkls": [list(hkl) for hkl in manifest.ordered_hkls],
        "rebindings": rebindings,
        "automatic_reselection": False,
    }
    return TattooSelection(
        catalog_id=catalog.catalog_id,
        recipe_id=recipe.recipe_id,
        orientation_id=recipe.orientation.orientation_id,
        candidates=tuple(candidates),
        selected_paths=tuple(selected_paths),
        ledger=ledger,
    )


__all__ = [
    "FrozenTattooPath",
    "FrozenTattooSelection",
    "bind_frozen_tattoo_selection",
    "load_frozen_tattoo_selection",
]

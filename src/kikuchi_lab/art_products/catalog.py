"""Tie-aware ranking and strict snapshots for shared science-art bands."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import replace
from itertools import combinations
from pathlib import Path

import numpy as np

from kikuchi_lab.art_products.contracts import ArtBandCatalog, ArtBandMember
from kikuchi_lab.kinematical import DirectReflectorEvidence
from kikuchi_lab.spherical_intensity.presentation import PresentationSource


_CATALOG_KEYS = {
    "schema_version",
    "source_structure_id",
    "source_structure_sha256",
    "source_recipe_id",
    "presentation_recipe_id",
    "eligibility_min_weight",
    "members",
}
_MEMBER_KEYS = {
    "hkl",
    "normal_crystal",
    "bragg_half_width_rad",
    "structure_factor_magnitude",
    "normalized_weight",
    "member_id",
    "globe_cohort",
    "globe_eligible",
    "tattoo_eligible",
    "acceptance_state",
    "acceptance_reason",
}


def _require_exact_keys(
    value: object,
    expected: set[str],
    context: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{context} keys must be exactly {sorted(expected)}")
    return value


def _assign_cohorts(eligible: list[ArtBandMember]) -> dict[str, int]:
    blocks: list[list[ArtBandMember]] = []
    for member in eligible:
        if not blocks or member.normalized_weight != blocks[-1][0].normalized_weight:
            blocks.append([])
        blocks[-1].append(member)
    if len(blocks) < 4:
        raise ValueError("catalog requires at least four unique eligible weight blocks")

    cumulative = [0]
    for block in blocks:
        cumulative.append(cumulative[-1] + len(block))
    total = len(eligible)
    targets = (0.25 * total, 0.50 * total, 0.75 * total)
    boundaries = min(
        combinations(range(1, len(blocks)), 3),
        key=lambda candidate: (
            sum(
                (cumulative[boundary] - target) ** 2
                for boundary, target in zip(candidate, targets, strict=True)
            ),
            candidate,
        ),
    )

    result: dict[str, int] = {}
    for block_index, block in enumerate(blocks):
        if block_index < boundaries[0]:
            cohort = 4
        elif block_index < boundaries[1]:
            cohort = 3
        elif block_index < boundaries[2]:
            cohort = 2
        else:
            cohort = 1
        result.update((member.member_id, cohort) for member in block)
    return result


def _build_art_band_catalog_arrays(
    *,
    hkls: np.ndarray,
    normals: np.ndarray,
    half_widths: np.ndarray,
    strengths: np.ndarray,
    weights: np.ndarray,
    source_structure_id: str,
    source_structure_sha256: str,
    source_recipe_id: str,
    presentation_recipe_id: str,
    eligibility_min_weight: float,
) -> ArtBandCatalog:
    if (
        isinstance(eligibility_min_weight, bool)
        or not isinstance(eligibility_min_weight, (int, float))
        or not math.isfinite(eligibility_min_weight)
        or not 0 < eligibility_min_weight <= 1
    ):
        raise ValueError("eligibility_min_weight must be positive, finite, and at most 1")
    threshold = float(eligibility_min_weight)

    hkls = np.asarray(hkls)
    normals = np.asarray(normals)
    half_widths = np.asarray(half_widths)
    strengths = np.asarray(strengths)
    weights = np.asarray(weights)
    count = hkls.shape[0] if hkls.ndim else 0
    if (
        hkls.shape != (count, 3)
        or normals.shape != (count, 3)
        or half_widths.shape != (count,)
        or strengths.shape != (count,)
    ):
        raise ValueError("source axial band channels have inconsistent shapes")
    if weights.shape != (count,):
        raise ValueError("source band weight length must match axial band count")
    if not all(
        np.isfinite(channel).all()
        for channel in (normals, half_widths, strengths, weights)
    ):
        raise ValueError("source band evidence must be finite")

    hkl_values = [tuple(int(index) for index in hkl) for hkl in hkls]
    if len(set(hkl_values)) != count:
        raise ValueError("source axial bands contain duplicate HKL values")

    members = [
        ArtBandMember(
            hkl=hkl,
            normal_crystal=normal,
            bragg_half_width_rad=float(half_width),
            structure_factor_magnitude=float(strength),
            normalized_weight=float(weight),
            globe_cohort=None,
            globe_eligible=bool(weight >= threshold),
            tattoo_eligible=bool(weight >= threshold),
            acceptance_state="unreviewed",
            acceptance_reason="automatic catalog candidate",
        )
        for hkl, normal, half_width, strength, weight in zip(
            hkl_values,
            normals,
            half_widths,
            strengths,
            weights,
            strict=True,
        )
    ]
    members.sort(
        key=lambda member: (
            -member.normalized_weight,
            member.hkl,
            member.member_id,
        )
    )
    cohort_by_member = _assign_cohorts(
        [member for member in members if member.globe_eligible]
    )
    members = [
        replace(member, globe_cohort=cohort_by_member.get(member.member_id))
        for member in members
    ]

    return ArtBandCatalog(
        schema_version=1,
        source_structure_id=source_structure_id,
        source_structure_sha256=source_structure_sha256,
        source_recipe_id=source_recipe_id,
        presentation_recipe_id=presentation_recipe_id,
        eligibility_min_weight=threshold,
        members=tuple(members),
    )


def build_art_band_catalog(
    source: PresentationSource,
    source_structure_id: str,
    source_structure_sha256: str,
    source_recipe_id: str,
    presentation_recipe_id: str,
    eligibility_min_weight: float,
) -> ArtBandCatalog:
    """Rank every presentation band and assign four tie-preserving cohorts."""
    axial = source.axial_bands
    return _build_art_band_catalog_arrays(
        hkls=axial.hkl,
        normals=axial.normals,
        half_widths=axial.theta_radian,
        strengths=axial.structure_factor_abs,
        weights=source.band_weights,
        source_structure_id=source_structure_id,
        source_structure_sha256=source_structure_sha256,
        source_recipe_id=source_recipe_id,
        presentation_recipe_id=presentation_recipe_id,
        eligibility_min_weight=eligibility_min_weight,
    )


def build_art_band_catalog_from_evidence(
    evidence: DirectReflectorEvidence,
) -> ArtBandCatalog:
    """Build a science-art catalog directly from owned reflector evidence."""
    return _build_art_band_catalog_arrays(
        hkls=evidence.hkl,
        normals=evidence.normal_crystal,
        half_widths=evidence.bragg_half_width_rad,
        strengths=evidence.structure_factor_magnitude,
        weights=evidence.normalized_weight,
        source_structure_id=evidence.source_structure_id,
        source_structure_sha256=evidence.source_structure_sha256,
        source_recipe_id=evidence.calculation_id,
        presentation_recipe_id=evidence.weighting_id,
        eligibility_min_weight=float(evidence.ledger["eligibility_min_weight"]),
    )


def write_art_band_catalog(path: str | Path, catalog: ArtBandCatalog) -> None:
    """Write one canonical, identity-bearing catalog snapshot."""
    payload = {"catalog_id": catalog.catalog_id, "content": catalog.to_dict()}
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_art_band_catalog(path: str | Path) -> ArtBandCatalog:
    """Load a strict snapshot and revalidate every content-derived identity."""
    payload = _require_exact_keys(
        json.loads(Path(path).read_text(encoding="utf-8")),
        {"catalog_id", "content"},
        "catalog snapshot",
    )
    content = _require_exact_keys(payload["content"], _CATALOG_KEYS, "catalog content")
    raw_members = content["members"]
    if not isinstance(raw_members, list):
        raise ValueError("catalog content members must be a JSON array")

    members: list[ArtBandMember] = []
    for index, raw_member in enumerate(raw_members):
        member_payload = _require_exact_keys(
            raw_member,
            _MEMBER_KEYS,
            f"catalog member {index}",
        )
        member = ArtBandMember(
            hkl=member_payload["hkl"],
            normal_crystal=member_payload["normal_crystal"],
            bragg_half_width_rad=member_payload["bragg_half_width_rad"],
            structure_factor_magnitude=member_payload["structure_factor_magnitude"],
            normalized_weight=member_payload["normalized_weight"],
            globe_cohort=member_payload["globe_cohort"],
            globe_eligible=member_payload["globe_eligible"],
            tattoo_eligible=member_payload["tattoo_eligible"],
            acceptance_state=member_payload["acceptance_state"],
            acceptance_reason=member_payload["acceptance_reason"],
        )
        if member_payload["member_id"] != member.member_id:
            raise ValueError(f"catalog member {index} member_id does not match its content")
        members.append(member)

    catalog = ArtBandCatalog(
        schema_version=content["schema_version"],
        source_structure_id=content["source_structure_id"],
        source_structure_sha256=content["source_structure_sha256"],
        source_recipe_id=content["source_recipe_id"],
        presentation_recipe_id=content["presentation_recipe_id"],
        eligibility_min_weight=content["eligibility_min_weight"],
        members=tuple(members),
    )
    if payload["catalog_id"] != catalog.catalog_id:
        raise ValueError("catalog_id does not match catalog content")
    return catalog


__all__ = [
    "build_art_band_catalog",
    "build_art_band_catalog_from_evidence",
    "load_art_band_catalog",
    "write_art_band_catalog",
]

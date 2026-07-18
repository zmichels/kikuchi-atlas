"""Tie-preserving selection for reflector catalog snapshots."""

from __future__ import annotations

from dataclasses import replace
from importlib.metadata import version
from itertools import combinations

from kikuchi_lab.sources.structure import StructureRecord

from .contracts import ReflectorCatalog, ReflectorMember
from .diffsims_adapter import enumerate_reflector_members
from .recipe import ReflectorRecipe


def _cohorts(members: list[ReflectorMember], cohort_count: int) -> dict[str, int]:
    """Assign near-equal-sized cohorts without splitting equal-weight blocks."""
    blocks: list[list[ReflectorMember]] = []
    for member in members:
        if not blocks or member.normalized_weight != blocks[-1][0].normalized_weight:
            blocks.append([])
        blocks[-1].append(member)
    if len(blocks) < cohort_count:
        raise ValueError("eligible members require at least one tied block per cohort")

    cumulative = [0]
    for block in blocks:
        cumulative.append(cumulative[-1] + len(block))
    targets = tuple(len(members) * index / cohort_count for index in range(1, cohort_count))
    boundaries = min(
        combinations(range(1, len(blocks)), cohort_count - 1),
        key=lambda candidate: (
            sum(
                (cumulative[boundary] - target) ** 2
                for boundary, target in zip(candidate, targets, strict=True)
            ),
            candidate,
        ),
    )
    result: dict[str, int] = {}
    for index, block in enumerate(blocks):
        cohort = cohort_count - sum(index >= boundary for boundary in boundaries)
        result.update((member.member_id, cohort) for member in block)
    return result


def build_reflector_catalog(source: StructureRecord, recipe: ReflectorRecipe) -> ReflectorCatalog:
    """Build a stable, tie-preserving reflector catalog from tracked source evidence."""
    members = list(enumerate_reflector_members(source, recipe))
    members.sort(key=lambda member: (-member.normalized_weight, member.hkl, member.member_id))
    eligible = [member for member in members if member.normalized_weight >= recipe.eligibility_min_weight]
    cohort_by_member = _cohorts(eligible, recipe.cohort_count)
    selected = tuple(
        replace(
            member,
            eligible=member.member_id in cohort_by_member,
            cohort=cohort_by_member.get(member.member_id),
        )
        for member in members
    )
    return ReflectorCatalog(
        source_structure_id=source.identifier,
        source_structure_sha256=source.sha256,
        energy_kev=recipe.energy_kev,
        reflection_recipe_id=recipe.recipe_id,
        selection={
            "frame": "crystal reciprocal Cartesian",
            "eligibility_min_weight": recipe.eligibility_min_weight,
            "tie_policy": recipe.tie_policy,
            "cohort_count": recipe.cohort_count,
            "source_master_relative_factor": recipe.source_master_relative_factor,
            "selection_relative_factor": recipe.selection_relative_factor,
            "weight_exponent": recipe.weight_exponent,
            "selection_rule": (
                "retain signed reflectors with abs(F) >= "
                "selection_relative_factor * max(abs(F)); then collapse axial pairs"
            ),
            "weight_normalization": (
                "(abs(structure_factor) / max(abs(structure_factor))) ** weight_exponent"
            ),
            "package_versions": {
                package: version(package)
                for package in ("diffpy-structure", "diffsims", "orix")
            },
        },
        members=selected,
    )

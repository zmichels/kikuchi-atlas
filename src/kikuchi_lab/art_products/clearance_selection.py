"""Deterministic bounded selection satisfying both tattoo clearance treatments."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping

from kikuchi_lab.art_products.contracts import ArtBandCatalog
from kikuchi_lab.art_products.tattoo_selection import (
    HemisphereSelectionRecipe,
    TattooSelection,
    _select_tattoo_paths,
)
from kikuchi_lab.art_products.tattoo_vector import (
    TattooClearanceError,
    build_tattoo_geometry,
)
from kikuchi_lab.model.identity import plain_data


MAX_CLEARANCE_SEARCH_STATES = 256
_ALGORITHM_VERSION = "bounded-bfs-wide-clearance-v1"
_WIDE_WIDTH_SCALE = 1.15
_STANDARD_WIDTH_SCALE = 1.0
_STANDARD_ALGORITHM_VERSION = "bounded-bfs-standard-clearance-v1"


class ClearanceSelectionFeasibilityError(ValueError):
    """Bounded search exhaustion with the last structured path conflict."""

    def __init__(
        self,
        *,
        phase_slug: str,
        catalog_id: str,
        evaluated_state_count: int,
        last_conflict: Mapping[str, object],
    ) -> None:
        conflict = dict(last_conflict)
        super().__init__(
            f"no clearance-valid tattoo selection for phase {phase_slug} and "
            f"catalog {catalog_id} after {evaluated_state_count} evaluated states; "
            f"last conflict: {conflict['message']}"
        )
        self.phase_slug = phase_slug
        self.catalog_id = catalog_id
        self.evaluated_state_count = evaluated_state_count
        self.last_conflict = conflict


def _conflict_record(
    error: TattooClearanceError,
    *,
    evaluated_state: int,
    exclusions: frozenset[str],
) -> dict[str, object]:
    return {
        "evaluated_state": evaluated_state,
        "excluded_member_ids": sorted(exclusions),
        "clearance_kind": error.clearance_kind,
        "member_ids": list(error.member_ids),
        "message": str(error),
    }


def _last_conflict(record: Mapping[str, object]) -> dict[str, object]:
    return {
        "clearance_kind": record["clearance_kind"],
        "member_ids": list(record["member_ids"]),
        "message": record["message"],
    }


def _with_search_ledger(
    selection: TattooSelection,
    *,
    exclusions: frozenset[str],
    evaluated_state_count: int,
    conflict_history: list[dict[str, object]],
    ledger_key: str,
    algorithm_version: str,
    width_scales: tuple[float, ...],
) -> TattooSelection:
    ledger = plain_data(selection.ledger)
    ledger[ledger_key] = {
        "algorithm_version": algorithm_version,
        "width_scale": width_scales[0],
        "state_limit": MAX_CLEARANCE_SEARCH_STATES,
        "chosen_exclusions": sorted(exclusions),
        "evaluated_state_count": evaluated_state_count,
        "conflict_history": conflict_history,
    }
    return TattooSelection(
        catalog_id=selection.catalog_id,
        recipe_id=selection.recipe_id,
        orientation_id=selection.orientation_id,
        candidates=selection.candidates,
        selected_paths=selection.selected_paths,
        ledger=ledger,
    )


def _branch_member_ids(
    selection: TattooSelection,
    error: TattooClearanceError,
) -> tuple[str, ...]:
    priority = {
        path.member_id: index for index, path in enumerate(selection.selected_paths)
    }
    ordered = sorted(
        error.member_ids,
        key=lambda member_id: (-priority[member_id], member_id),
    )
    return tuple(ordered)


def _select_clearance_valid_tattoo_paths(
    catalog: ArtBandCatalog,
    recipe: HemisphereSelectionRecipe,
    *,
    width_scales: tuple[float, ...],
    ledger_key: str,
    algorithm_version: str,
) -> TattooSelection:
    """Select paths by bounded BFS across the requested clearance treatments."""
    queue = deque([frozenset[str]()])
    queued = {frozenset[str]()}
    conflict_history: list[dict[str, object]] = []
    evaluated_state_count = 0

    while queue and evaluated_state_count < MAX_CLEARANCE_SEARCH_STATES:
        exclusions = queue.popleft()
        evaluated_state_count += 1
        try:
            selection = _select_tattoo_paths(
                catalog,
                recipe,
                excluded_member_ids=exclusions,
            )
        except ValueError:
            if not exclusions:
                raise
            continue

        try:
            for width_scale in width_scales:
                build_tattoo_geometry(
                    selection,
                    recipe,
                    width_scale=width_scale,
                )
        except TattooClearanceError as error:
            record = _conflict_record(
                error,
                evaluated_state=evaluated_state_count,
                exclusions=exclusions,
            )
            conflict_history.append(record)
            for member_id in _branch_member_ids(selection, error):
                branch = exclusions | {member_id}
                if branch not in queued:
                    queued.add(branch)
                    queue.append(branch)
            continue

        if not exclusions:
            return selection
        return _with_search_ledger(
            selection,
            exclusions=exclusions,
            evaluated_state_count=evaluated_state_count,
            conflict_history=conflict_history,
            ledger_key=ledger_key,
            algorithm_version=algorithm_version,
            width_scales=width_scales,
        )

    if not conflict_history:
        raise RuntimeError("clearance search ended without a structured conflict")
    phase_slug = str(getattr(recipe, "phase_slug", catalog.source_structure_id))
    raise ClearanceSelectionFeasibilityError(
        phase_slug=phase_slug,
        catalog_id=catalog.catalog_id,
        evaluated_state_count=evaluated_state_count,
        last_conflict=_last_conflict(conflict_history[-1]),
    )


def select_clearance_valid_tattoo_paths(
    catalog: ArtBandCatalog,
    recipe: HemisphereSelectionRecipe,
) -> TattooSelection:
    """Select paths by bounded BFS and validate wide before standard geometry."""
    return _select_clearance_valid_tattoo_paths(
        catalog,
        recipe,
        width_scales=(_WIDE_WIDTH_SCALE, _STANDARD_WIDTH_SCALE),
        ledger_key="wide_clearance_search",
        algorithm_version=_ALGORITHM_VERSION,
    )


def select_standard_clearance_valid_tattoo_paths(
    catalog: ArtBandCatalog,
    recipe: HemisphereSelectionRecipe,
) -> TattooSelection:
    """Select paths by bounded BFS and validate standard geometry only."""
    return _select_clearance_valid_tattoo_paths(
        catalog,
        recipe,
        width_scales=(_STANDARD_WIDTH_SCALE,),
        ledger_key="standard_clearance_search",
        algorithm_version=_STANDARD_ALGORITHM_VERSION,
    )


__all__ = [
    "ClearanceSelectionFeasibilityError",
    "MAX_CLEARANCE_SEARCH_STATES",
    "select_clearance_valid_tattoo_paths",
    "select_standard_clearance_valid_tattoo_paths",
]

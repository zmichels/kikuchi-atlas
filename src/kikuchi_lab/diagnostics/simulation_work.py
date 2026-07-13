"""CPU-only workload bounds for an ebsdsim master-pattern request."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from ebsdsim.cif import parse_cif_crystal
from ebsdsim.kgrid import build_pg_k_grid
from ebsdsim.lookup import prepare_diff_lookup_geometry
from ebsdsim.structure import build_cell_from_cif

from kikuchi_lab.model.recipes import SimulationRecipe


@dataclass(frozen=True)
class SimulationWorkEstimate:
    """Finite upper bounds and a first-order dynamical-work proxy."""

    grid_size: int
    n_k: int
    n_reflections: int
    chunks_per_bin: int
    maximum_energy_bins: int
    minimum_bins_before_relative_stop: int
    smith_rank: int
    work_proxy_per_bin: int
    maximum_work_proxy: int
    checkpoint_policy: str = "atomic-complete-run"
    resumable_within_run: bool = False

    def to_dict(self) -> dict[str, int | str | bool]:
        return asdict(self)


def estimate_simulation_work(
    simulation_cif: str | Path,
    recipe: SimulationRecipe,
) -> SimulationWorkEstimate:
    """Inspect crystallography and recipe controls without creating a GPU device."""
    path = Path(simulation_cif)
    crystal = parse_cif_crystal(path.read_text(encoding="utf-8", errors="replace"))
    cell = build_cell_from_cif(crystal)
    if cell.pg_num is None:
        raise ValueError("cannot estimate work without a resolved point group")
    grid = build_pg_k_grid(cell.pg_num, recipe.halfw)
    n_k = int(grid.khat.size // 3)
    geometry = prepare_diff_lookup_geometry(cell, recipe.dmin_nm)
    n_reflections = int(geometry.hkl.size // 3)
    maximum_energy_bins = max(1, int(recipe.voltage_kv / recipe.energy_binwidth_kev))
    work_proxy_per_bin = n_k * n_reflections * recipe.rank
    return SimulationWorkEstimate(
        grid_size=1 + 2 * recipe.halfw,
        n_k=n_k,
        n_reflections=n_reflections,
        chunks_per_bin=(n_k + recipe.chunk_size - 1) // recipe.chunk_size,
        maximum_energy_bins=maximum_energy_bins,
        minimum_bins_before_relative_stop=1 if maximum_energy_bins == 1 else 2,
        smith_rank=recipe.rank,
        work_proxy_per_bin=work_proxy_per_bin,
        maximum_work_proxy=work_proxy_per_bin * maximum_energy_bins,
    )

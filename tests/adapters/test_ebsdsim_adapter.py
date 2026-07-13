from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from ebsdsim import MasterPattern
from ebsdsim.kgrid import build_pg_k_grid

from kikuchi_lab.cli.main import main
from kikuchi_lab.model.persistence import load_master_product
from kikuchi_lab.model.recipes import SimulationRecipe
from kikuchi_lab.sources.ebsdsim_adapter import (
    load_ebsdsim_npz,
    load_simulation_recipe,
    save_simulation_bundle,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"
PROOF_RECIPE = ROOT / "recipes/proof/forsterite-simulation.yml"


def tiny_recipe(**changes) -> SimulationRecipe:
    values = load_simulation_recipe(PROOF_RECIPE).to_dict()
    values.update(
        {
            "halfw": 4,
            "energy_binwidth_kev": 20.0,
            "n_trajectories": 4096,
            "rank": 4,
            "chunk_size": 8,
            "mc_auto_stop": False,
            "mc_min_trajectories": 4096,
            "mc_max_trajectories": 4096,
        }
    )
    values.update(changes)
    return SimulationRecipe(**values)


def resolved_cell(record=None):
    if record is None:
        record = load_structure_record(SOURCE)
    multiplicities = [4, 4, 4, 4, 4, 8]
    sites = []
    for index, (site, multiplicity) in enumerate(zip(record.sites, multiplicities, strict=True)):
        x, y, z = site.fract
        sites.append(
            {
                "index": index,
                "atomic_number": {"Mg": 12, "Si": 14, "O": 8}[site.element],
                "symbol": site.element,
                "fract": [y, z, x],
                "occupancy": site.occupancy,
                "b_iso_angstrom_sq": 8 * np.pi**2 * site.u_iso_angstrom_sq,
                "b_iso_nm_sq": 8 * np.pi**2 * site.u_iso_angstrom_sq / 100,
                "multiplicity": multiplicity,
            }
        )
    return {
        "a_angstrom": record.lattice_angstrom[1],
        "b_angstrom": record.lattice_angstrom[2],
        "c_angstrom": record.lattice_angstrom[0],
        "alpha_deg": record.lattice_angstrom[4],
        "beta_deg": record.lattice_angstrom[5],
        "gamma_deg": record.lattice_angstrom[3],
        "space_group": record.space_group_number,
        "pg_num": 8,
        "pg_symbol": "mmm",
        "n_sites": len(sites),
        "sites": sites,
    }


def write_deterministic_public_master_pattern_fixture(
    directory: Path,
    *,
    cell=None,
    include_hemisphere_semantics: bool = True,
    invalid: bool = False,
    recipe: SimulationRecipe | None = None,
) -> Path:
    recipe = tiny_recipe() if recipe is None else recipe
    grid = build_pg_k_grid(8, recipe.halfw)
    kij = grid.kij.reshape(-1, 3).astype(np.int32)
    khat = grid.khat.reshape(-1, 3).astype(np.float32)
    n_k = kij.shape[0]
    n_sites = 6
    integrated = np.linspace(1, 2, n_k * n_sites, dtype=np.float32)
    if invalid:
        integrated[0] = np.nan
    metadata = {
        "format": "ebsdsim-master-pattern",
        "source": str(ROOT / "phases/forsterite/COD-9000319.cif"),
        "voltage_kv": recipe.voltage_kv,
        "grid_size": 1 + 2 * recipe.halfw,
        "halfw": recipe.halfw,
        "dmin": recipe.dmin_nm,
        "energy_binwidth_keV": recipe.energy_binwidth_kev,
        "rank": recipe.rank,
        "chunk_size": recipe.chunk_size,
        "exact_slow_cpu": recipe.exact_slow_cpu,
        "marginal_coverage": recipe.marginal_coverage,
        "relative_image_stop": recipe.relative_image_stop,
        "bethe_c_strong": recipe.bethe_c_strong,
        "bethe_c_weak": recipe.bethe_c_weak,
        "bethe_c_cutoff": recipe.bethe_c_cutoff,
        "dbdiff_sg_cutoff": recipe.dbdiff_sg_cutoff,
        "sigma_deg": recipe.sigma_deg,
        "omega_deg": recipe.omega_deg,
        "mc_backend": "gpu_fly_first",
        "mc_n_trajectories": recipe.n_trajectories,
        "mc_auto_stop": recipe.mc_auto_stop,
        "mc_min_trajectories": recipe.mc_min_trajectories,
        "mc_max_trajectories": recipe.mc_max_trajectories,
        "mc_converged": recipe.mc_auto_stop,
        "mc_relative_tol": recipe.mc_relative_tol,
        "cell": resolved_cell() if cell is None else cell,
        "pg_num": 8,
        "pg_symbol": "mmm",
    }
    if include_hemisphere_semantics:
        metadata.update(
            {"is_centrosymmetric": True, "needs_southern_hemisphere": False}
        )
    mp = MasterPattern(
        pattern=np.zeros((9, 9), dtype=np.float32),
        integrated=integrated,
        n_k=n_k,
        n_sites=n_sites,
        metadata=metadata,
        bin_patterns=[integrated.copy()],
        bin_voltages_kv=[recipe.voltage_kv],
        bin_weights=[1.0],
        kij=kij,
        khat=khat,
        pg_num=8,
    )
    return mp.save(directory / "fixture.npz")


def tamper_metadata(path: Path, change) -> None:
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    metadata = json.loads(bytes(arrays["meta_json"].tobytes()).decode("utf-8"))
    change(metadata)
    arrays["meta_json"] = np.frombuffer(json.dumps(metadata).encode(), dtype=np.uint8)
    np.savez_compressed(path, **arrays)


def test_proof_recipe_contains_every_simulation_control():
    recipe = load_simulation_recipe(PROOF_RECIPE)

    assert recipe.mc_backend == "gpu"
    assert recipe.recipe_id.startswith("recipe-")
    assert set(recipe.to_dict()) == set(recipe.__dataclass_fields__)


def test_ebsdsim_conversion_keeps_both_hemispheres(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path)
    source = load_structure_record(SOURCE)
    product = load_ebsdsim_npz(fixture, source=source, recipe=tiny_recipe())

    assert product.intensity.shape == (2, 9, 9)
    assert product.metadata_dict()["hemisphere_order"] == ["north", "south"]
    assert product.metadata_dict()["source_structure"]["source_id"] == source.source_record.source_id
    assert product.metadata_dict()["simulation"]["requested_backend"] == "gpu"
    assert product.metadata_dict()["simulation"]["resolved_backend"] == "gpu_fly_first"
    assert product.metadata_dict()["coordinate_frame"] == "crystal:Pnma-derived-from-Pbnm"
    assert product.metadata_dict()["source_structure"]["simulation_setting"][
        "target_setting"
    ] == "P n m a"


def test_canonical_phase_matches_the_derived_pnma_simulation_cell(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path)
    source = load_structure_record(SOURCE)
    product = load_ebsdsim_npz(fixture, source=source, recipe=tiny_recipe())
    metadata = product.metadata_dict()

    assert metadata["phase"] == {
        "name": "forsterite",
        "formula": "Mg2SiO4",
        "space_group": {"number": 62, "setting": "P n m a"},
        "lattice": {
            "values": [10.207, 5.980, 4.756, 90.0, 90.0, 90.0],
            "units": "angstrom",
        },
    }
    assert metadata["source_structure"]["original_phase"]["space_group"][
        "setting"
    ] == "P b n m"
    assert metadata["source_structure"]["original_phase"]["lattice"]["values"] == [
        4.756,
        10.207,
        5.980,
        90.0,
        90.0,
        90.0,
    ]
    assert metadata["source_structure"]["basis_transform"] == {
        "source_setting": "P b n m",
        "target_setting": "P n m a",
        "target_lattice_from_source": ["b", "c", "a"],
        "target_fractional_from_source": ["y", "z", "x"],
        "target_site_multiplicities": [4, 4, 4, 4, 4, 8],
    }


def test_ebsdsim_conversion_rejects_wrong_resolved_phase(tmp_path):
    source = load_structure_record(SOURCE)
    cell = resolved_cell(source)
    cell["space_group"] = 63
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path, cell=cell)

    with pytest.raises(ValueError, match="space group"):
        load_ebsdsim_npz(fixture, source=source, recipe=tiny_recipe())


def test_ebsdsim_conversion_rejects_per_site_multiplicity_tampering(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path)

    def swap_mg_multiplicities(metadata):
        metadata["cell"]["sites"][0]["multiplicity"] = 8
        metadata["cell"]["sites"][1]["multiplicity"] = 4

    tamper_metadata(fixture, swap_mg_multiplicities)

    with pytest.raises(ValueError, match="multiplicity"):
        load_ebsdsim_npz(
            fixture, source=load_structure_record(SOURCE), recipe=tiny_recipe()
        )


def test_ebsdsim_conversion_rejects_absent_hemisphere_semantics(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(
        tmp_path, include_hemisphere_semantics=False
    )

    with pytest.raises(ValueError, match="hemisphere"):
        load_ebsdsim_npz(
            fixture, source=load_structure_record(SOURCE), recipe=tiny_recipe()
        )


def test_ebsdsim_conversion_rejects_invalid_arrays(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path, invalid=True)

    with pytest.raises(ValueError, match="finite"):
        load_ebsdsim_npz(
            fixture, source=load_structure_record(SOURCE), recipe=tiny_recipe()
        )


def test_simulation_bundle_links_untouched_ebsdsim_and_canonical_artifacts(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path / "upstream")
    before = fixture.read_bytes()
    source = load_structure_record(SOURCE)
    bundle = save_simulation_bundle(
        fixture,
        output_root=tmp_path / "bundle",
        source=source,
        recipe=tiny_recipe(),
    )

    assert fixture.read_bytes() == before
    assert bundle.ebsdsim_npz.read_bytes() == before
    canonical = load_master_product(bundle.canonical_product)
    manifest = json.loads(bundle.manifest.read_text())
    assert manifest["source_id"] == source.source_record.source_id
    assert manifest["master_product_id"] == canonical.product_id
    assert manifest["ebsdsim_npz_sha256"] != canonical.array_sha256
    assert Path(manifest["ebsdsim_npz"]).name == bundle.ebsdsim_npz.name


def test_adapter_rejects_requested_backend_not_honored(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path)
    tamper_metadata(fixture, lambda metadata: metadata.__setitem__("mc_backend", "surrogate"))

    with pytest.raises(ValueError, match="backend"):
        load_ebsdsim_npz(
            fixture, source=load_structure_record(SOURCE), recipe=tiny_recipe()
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("mc_auto_stop", False, "auto-stop"),
        ("mc_relative_tol", 0.02, "mc_relative_tol"),
        ("mc_n_trajectories", 2048, "minimum"),
        ("mc_n_trajectories", 16384, "maximum"),
        ("mc_min_trajectories", 2048, "minimum"),
        ("mc_max_trajectories", 16384, "maximum"),
    ],
)
def test_adapter_rejects_auto_stop_control_mismatch(tmp_path, field, value, message):
    recipe = tiny_recipe(
        mc_auto_stop=True,
        mc_min_trajectories=4096,
        mc_max_trajectories=8192,
    )
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path, recipe=recipe)
    tamper_metadata(fixture, lambda metadata: metadata.__setitem__(field, value))

    with pytest.raises(ValueError, match=message):
        load_ebsdsim_npz(
            fixture,
            source=load_structure_record(SOURCE),
            recipe=recipe,
        )


def test_canonical_identity_does_not_include_elapsed_runtime(tmp_path):
    fixture = write_deterministic_public_master_pattern_fixture(tmp_path)
    source = load_structure_record(SOURCE)
    first = load_ebsdsim_npz(
        fixture, source=source, recipe=tiny_recipe(), elapsed_seconds=1.0
    )
    second = load_ebsdsim_npz(
        fixture, source=source, recipe=tiny_recipe(), elapsed_seconds=99.0
    )

    assert first.product_id == second.product_id
    assert first.metadata_dict() == second.metadata_dict()
    assert "elapsed_seconds" not in first.metadata_dict()["simulation"]


def test_simulate_master_cli_rejects_structure_outside_source_record(tmp_path, capsys):
    status = main(
        [
            "simulate-master",
            "--structure",
            str(tmp_path / "wrong.cif"),
            "--source",
            str(SOURCE),
            "--recipe",
            str(PROOF_RECIPE),
            "--output",
            str(tmp_path / "output"),
        ]
    )

    assert status == 1
    assert "tracked CIF" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()

from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.workflows.proof import ProofRecipeError, load_proof_recipe


ROOT = Path(__file__).parents[2]


def test_proof_recipe_declares_exact_master_admissibility_contract() -> None:
    recipe = load_proof_recipe(ROOT / "recipes/proof/forsterite-proof.yml")

    assert recipe.master_contract == {
        "schema_version": 1,
        "phase": {
            "name": "forsterite",
            "formula": "Mg2SiO4",
            "space_group_number": 62,
            "space_group_setting": "P n m a",
            "lattice_angstrom": [10.207, 5.98, 4.756, 90.0, 90.0, 90.0],
            "lattice_absolute_tolerance": 1e-6,
        },
        "source": {
            "identifier": "COD-9000319",
            "sha256": "550b8c89c617267d39e7cb6a07fe6f55cd2343453c1c45ec77738bf6fd25d9cd",
            "source_id": "source-ca21e09f345e7146",
        },
        "simulation": {
            "requested": {
                "voltage_kv": 20.0,
                "dmin_nm": 0.08,
                "energy_binwidth_kev": 20.0,
                "rank": 8,
                "halfw": 128,
                "mc_backend": "gpu",
            },
            "resolved": {
                "voltage_kv": 20.0,
                "dmin": 0.08,
                "energy_binwidth_keV": 20.0,
                "rank": 8,
                "halfw": 128,
                "grid_size": 257,
                "n_bins_run": 1,
                "n_mc_bins": 1,
                "mc_backend": "gpu_fly_first",
            },
            "requested_backend": "gpu",
            "resolved_backend": "gpu_fly_first",
            "control_evidence": {
                "native_reported": [
                    "mc_converged",
                    "mc_n_trajectories",
                    "mc_relative_tol",
                ],
                "invocation_only": [
                    "mc_auto_stop",
                    "mc_min_trajectories",
                    "mc_max_trajectories",
                ],
            },
        },
        "product": {
            "shape": [2, 257, 257],
            "projection": "Lambert square equal-area",
            "hemisphere_order": ["north", "south"],
            "generator": {"name": "ebsdsim", "version": "0.1.8"},
        },
    }


def test_proof_recipe_normalizes_malformed_yaml(tmp_path: Path) -> None:
    path = tmp_path / "broken.yml"
    path.write_text("schema_version: [")

    with pytest.raises(ProofRecipeError, match="YAML"):
        load_proof_recipe(path)


def test_proof_recipe_normalizes_field_type_errors(tmp_path: Path) -> None:
    payload = (ROOT / "recipes/proof/forsterite-proof.yml").read_text()
    payload = payload.replace(
        "processing_recipe: scientific-clean.yml\nenergy_kev: 20.0",
        "processing_recipe: scientific-clean.yml\nenergy_kev: [20]",
    )
    path = tmp_path / "broken.yml"
    path.write_text(payload)

    with pytest.raises(ProofRecipeError, match="energy_kev"):
        load_proof_recipe(path)

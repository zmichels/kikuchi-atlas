from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.model.recipes import SimulationRecipe
from kikuchi_lab.sources.ebsdsim_adapter import generate_master_pattern
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]


@pytest.mark.gpu
@pytest.mark.slow
def test_tiny_forsterite_gpu_master_pattern(tmp_path):
    source = load_structure_record(ROOT / "phases/forsterite/source.yml")
    recipe = SimulationRecipe(
        voltage_kv=20.0,
        halfw=8,
        dmin_nm=0.08,
        energy_binwidth_kev=20.0,
        n_trajectories=4096,
        sigma_deg=70.0,
        omega_deg=0.0,
        rank=4,
        chunk_size=8,
        marginal_coverage=1.0,
        relative_image_stop=0.01,
        mc_backend="gpu",
        bethe_c_strong=20.0,
        bethe_c_weak=40.0,
        bethe_c_cutoff=200.0,
        dbdiff_sg_cutoff=1.0,
        mc_auto_stop=False,
        mc_relative_tol=0.01,
        mc_min_trajectories=4096,
        mc_max_trajectories=4096,
        exact_slow_cpu=False,
    )

    result = generate_master_pattern(
        source=source,
        recipe=recipe,
        output_npz=tmp_path / "forsterite-tiny-gpu.npz",
    )

    assert result.ebsdsim_npz.is_file()
    assert result.product.intensity.shape == (2, 17, 17)
    assert np.isfinite(result.product.intensity).all()
    assert np.ptp(result.product.intensity) > 0
    metadata = result.product.metadata_dict()
    assert metadata["source_structure"]["source_id"] == source.source_record.source_id
    assert metadata["simulation"]["requested_backend"] == "gpu"
    assert metadata["simulation"]["resolved_backend"] == "gpu_fly_first"
    assert metadata["simulation"]["resolved"]["mc_n_trajectories"] == 4096
    assert metadata["simulation"]["resolved"]["mc_auto_stop"] is False
    assert hashlib.sha256(result.ebsdsim_npz.read_bytes()).hexdigest() == result.npz_sha256
    manifest = json.loads(result.manifest.read_text())
    assert manifest["master_product_id"] == result.product.product_id
    transformed = result.manifest.parent / manifest["simulation_cif"]
    assert transformed.is_file()
    assert hashlib.sha256(transformed.read_bytes()).hexdigest() == manifest[
        "simulation_cif_sha256"
    ]
    assert manifest["basis_transform"] == {
        "source_setting": "P b n m",
        "target_setting": "P n m a",
        "target_fractional_from_source": ["y", "z", "x"],
        "target_lattice_from_source": ["b", "c", "a"],
    }
    assert manifest["elapsed_seconds"] > 0

from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.near_depth.recipe import load_near_depth_recipe


ROOT = Path(__file__).parents[2]
PARITY_RECIPES = {
    "forsterite": (
        "kinematical/forsterite-etched-master.yml",
        "presentation/forsterite-near-depth-atlas-parity.yml",
    ),
    "ice-ih": (
        "kinematical/ice-ih-oxygen-quiet-proof.yml",
        "presentation/ice-ih-near-depth-stepped-band-led.yml",
    ),
    "quartz": (
        "kinematical/quartz-001-atlas-parity-master.yml",
        "presentation/quartz-near-depth-atlas-parity.yml",
    ),
    "zircon": (
        "kinematical/zircon-quiet-master.yml",
        "presentation/zircon-near-depth-stepped-band-led.yml",
    ),
    "titanite": (
        "kinematical/titanite-quiet-master.yml",
        "presentation/titanite-near-depth-stepped-band-led.yml",
    ),
    "diamond": (
        "kinematical/diamond-001-atlas-parity-master.yml",
        "presentation/diamond-near-depth-atlas-parity.yml",
    ),
    "plagioclase-an52": (
        "kinematical/plagioclase-an52-001-atlas-parity-master.yml",
        "presentation/plagioclase-an52-near-depth-atlas-parity.yml",
    ),
    "muscovite-2m1": (
        "kinematical/muscovite-2m1-001-atlas-parity-master.yml",
        "presentation/muscovite-2m1-near-depth-atlas-parity.yml",
    ),
    "diopside": (
        "kinematical/diopside-001-atlas-parity-master.yml",
        "presentation/diopside-near-depth-atlas-parity.yml",
    ),
}


@pytest.mark.parametrize("slug", sorted(PARITY_RECIPES))
def test_every_atlas_phase_has_one_linked_kinematical_and_depth_recipe(slug: str) -> None:
    kinematical_relative, treatment_relative = PARITY_RECIPES[slug]
    kinematical_path = ROOT / "recipes" / kinematical_relative
    treatment_path = ROOT / "recipes" / treatment_relative

    kinematical = load_kinematical_recipe(kinematical_path)
    treatment = load_near_depth_recipe(treatment_path)

    assert kinematical_path.is_file()
    assert treatment_path.is_file()
    assert kinematical.hemisphere == "both"
    assert kinematical.half_size >= 512
    assert treatment.expected_kinematical_recipe_id == kinematical.recipe_id
    assert (treatment_path.parent / treatment.source_kinematical_recipe).resolve() == (
        kinematical_path.resolve()
    )

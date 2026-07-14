from pathlib import Path

import numpy as np

from kikuchi_lab.kinematical import KinematicalArrayProduct, load_kinematical_recipe


RECIPE = (
    Path(__file__).parents[2]
    / "recipes"
    / "kinematical"
    / "forsterite-etched-master.yml"
)


def test_forsterite_kinematical_recipe_fixes_two_etched_styles() -> None:
    recipe = load_kinematical_recipe(RECIPE)
    assert recipe.energy_kev == 20.0
    assert recipe.orientation.euler_bunge_deg == (45.0, 51.50414783, 0.0)
    assert recipe.zone_axis_uvw == (0, 1, 1)
    assert recipe.min_dspacing_angstrom == 0.7
    assert recipe.master_relative_factor == 0.03
    assert recipe.promoted_style == "quiet"
    assert recipe.hemisphere == "both"
    assert [(style.name, style.overlay_relative_factor) for style in recipe.styles] == [
        ("balanced", 0.14),
        ("quiet", 0.22),
    ]


def test_kinematical_array_product_owns_finite_float32_data() -> None:
    source = np.arange(25, dtype=np.float64).reshape(5, 5)
    product = KinematicalArrayProduct.from_array(
        "master-stereographic",
        source,
        metadata={"projection": "stereographic", "hemisphere": "upper"},
    )
    source[:] = -1
    assert product.intensity.dtype == np.float32
    assert not product.intensity.flags.writeable
    assert product.intensity[0, 0] == 0
    assert product.product_id.startswith("kinematical-")

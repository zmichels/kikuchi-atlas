from __future__ import annotations

from pathlib import Path

from kikuchi_lab.ice_globe.intensity import build_ice_intensity_field
from kikuchi_lab.workflows.ice_kinematical import simulate_ice_kinematical


ROOT = Path(__file__).parents[2]
KINEMATICAL_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"


def test_ice_intensity_field_comes_from_master_values_not_reflector_ridges() -> None:
    field = build_ice_intensity_field(simulate_ice_kinematical(KINEMATICAL_RECIPE))

    assert field.source_kind == "kinematical_stereographic_master"
    assert field.field_id.startswith("ice-intensity-field-")
    assert field.raw_values.ptp() > 0.0

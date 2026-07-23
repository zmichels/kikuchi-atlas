from __future__ import annotations

from dataclasses import replace

import pytest

from kikuchi_lab.dictionary.detector_profiles import (
    DetectorProfile,
    ice_ih_virtual_camera_profiles,
)
from kikuchi_lab.model.recipes import DetectorRecipe


def _detector() -> DetectorRecipe:
    return DetectorRecipe(
        shape=(9, 11),
        pcx=0.5,
        pcy=0.65,
        pcz=0.6,
        pc_convention="tsl",
        sample_tilt_deg=70.0,
        detector_tilt_deg=0.0,
        detector_azimuth_deg=0.0,
        detector_twist_deg=0.0,
        pixel_size_um=5.0,
        binning=1,
        supersampling=1,
    )


def test_ice_profiles_are_named_distinct_geometry_variants() -> None:
    detector = _detector()

    profiles = ice_ih_virtual_camera_profiles(detector)

    assert [profile.name for profile in profiles] == ["nominal", "wide-field", "narrow-field"]
    assert profiles[0].detector == detector
    assert [profile.detector.pcz for profile in profiles] == [0.6, 0.45, 0.82]
    assert all(profile.detector.shape == detector.shape for profile in profiles)
    assert profiles[1].to_dict()["detector_geometry"] == profiles[1].detector.to_dict()


@pytest.mark.parametrize("name", ("", "Upper", "two_words", "two--words"))
def test_detector_profile_rejects_nonportable_names(name: str) -> None:
    with pytest.raises(ValueError, match="lowercase hyphenated"):
        DetectorProfile(name, "label", "description", _detector())


def test_detector_profiles_require_a_detector_recipe() -> None:
    with pytest.raises(TypeError, match="DetectorRecipe"):
        DetectorProfile("valid", "label", "description", object())
    with pytest.raises(TypeError, match="DetectorRecipe"):
        ice_ih_virtual_camera_profiles(replace(_detector(), pcz=0.7).to_dict())  # type: ignore[arg-type]

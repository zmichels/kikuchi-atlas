"""Named virtual detector geometries for source-bound transfer proofs."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re

from kikuchi_lab.model.recipes import DetectorRecipe


_PROFILE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


@dataclass(frozen=True)
class DetectorProfile:
    """A declared geometry and explanatory label for one virtual camera view."""

    name: str
    label: str
    description: str
    detector: DetectorRecipe

    def __post_init__(self) -> None:
        if not _PROFILE_NAME.fullmatch(self.name):
            raise ValueError("profile name must be a lowercase hyphenated identifier")
        if not self.label or not self.description:
            raise ValueError("profile label and description are required")
        if not isinstance(self.detector, DetectorRecipe):
            raise TypeError("detector must be a DetectorRecipe")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "detector_geometry": self.detector.to_dict(),
        }


def ice_ih_virtual_camera_profiles(detector: DetectorRecipe) -> tuple[DetectorProfile, ...]:
    """Return three distinct declared virtual cameras for the Ice Ih proof.

    These are intentionally source-bound geometry variants, not models of
    specific commercial cameras or detector calibrations. Their shared pixel
    grid isolates the effect of the named camera distance while retaining the
    same coordinate convention and specimen-frame transform.
    """
    if not isinstance(detector, DetectorRecipe):
        raise TypeError("detector must be a DetectorRecipe")
    return (
        DetectorProfile(
            name="nominal",
            label="source-declared view",
            description="Original TSL projection center and camera distance from the checked Ice Ih recipe.",
            detector=detector,
        ),
        DetectorProfile(
            name="wide-field",
            label="shorter-distance virtual view",
            description="A named lower PCz virtual camera with a wider angular field on the same pixel grid.",
            detector=replace(detector, pcz=0.45),
        ),
        DetectorProfile(
            name="narrow-field",
            label="longer-distance virtual view",
            description="A named higher PCz virtual camera with a narrower angular field on the same pixel grid.",
            detector=replace(detector, pcz=0.82),
        ),
    )


__all__ = ["DetectorProfile", "ice_ih_virtual_camera_profiles"]

"""Project-owned contracts for crisp near-depth presentation renders."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from kikuchi_lab.model.identity import stable_id


@dataclass(frozen=True)
class StrokeStyle:
    """One coincident vector stroke and its wider symmetric casing."""

    relative_factor: float
    width_pt: float
    alpha: float
    casing_width_pt: float
    casing_alpha: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NearDepthTreatmentRecipe:
    """Plain, content-addressed presentation treatment parameters."""

    schema_version: int
    name: str
    source_kinematical_recipe: str
    expected_kinematical_recipe_id: str
    overlap_relative_factor: float
    weight_exponent: float
    normalization_percentile: float
    optical_depth_gain: float
    luminance_ceiling: float
    center: StrokeStyle
    boundary: StrokeStyle
    figure_size_px: int
    background_color: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_kinematical_recipe": self.source_kinematical_recipe,
            "expected_kinematical_recipe_id": self.expected_kinematical_recipe_id,
            "overlap": {
                "relative_factor": self.overlap_relative_factor,
                "weight_exponent": self.weight_exponent,
                "normalization_percentile": self.normalization_percentile,
            },
            "optical_depth": {
                "gain": self.optical_depth_gain,
                "luminance_ceiling": self.luminance_ceiling,
            },
            "center": self.center.to_dict(),
            "boundary": self.boundary.to_dict(),
            "figure_size_px": self.figure_size_px,
            "background_color": self.background_color,
        }

    @property
    def recipe_id(self) -> str:
        payload = self.to_dict()
        del payload["source_kinematical_recipe"]
        return stable_id("recipe", payload)


__all__ = ["NearDepthTreatmentRecipe", "StrokeStyle"]

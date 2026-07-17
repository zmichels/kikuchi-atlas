"""Crystal habit recipe and crystallographic expansion contracts."""

from .crystallography import CrystalPhase, ExpandedPlane, expand_habit_planes
from .geometry import (
    LabeledPolygonMesh,
    PolygonFace,
    TriangleMesh,
    orient_and_scale_habit,
    solve_convex_habit,
    triangulate_habit,
)
from .mesh import MeshValidation, stl_bytes, validate_triangle_mesh, write_habit_preview
from .recipes import FDMContext, HabitFace, HabitRecipe, PhaseSource, load_habit_recipe
from .workflow import HabitBuildResult, build_habit

__all__ = [
    "CrystalPhase",
    "ExpandedPlane",
    "FDMContext",
    "HabitFace",
    "HabitBuildResult",
    "HabitRecipe",
    "LabeledPolygonMesh",
    "MeshValidation",
    "PhaseSource",
    "PolygonFace",
    "TriangleMesh",
    "expand_habit_planes",
    "build_habit",
    "load_habit_recipe",
    "orient_and_scale_habit",
    "solve_convex_habit",
    "stl_bytes",
    "triangulate_habit",
    "validate_triangle_mesh",
    "write_habit_preview",
]

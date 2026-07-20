"""Portable, explicitly bounded spherical dictionary resources."""

from .spherical import (
    DictionaryMatch,
    OrientationEntry,
    SphericalDictionaryVerification,
    SphericalDictionaryResult,
    cube_shell_directions,
    downsample_to_cube_shell,
    publish_spherical_dictionary,
    quaternion_rotation_matrix,
    rank_spherical_dictionary,
    rotate_canonical_signal_to_sample,
    verify_spherical_dictionary,
)

__all__ = [
    "DictionaryMatch",
    "OrientationEntry",
    "SphericalDictionaryVerification",
    "SphericalDictionaryResult",
    "cube_shell_directions",
    "downsample_to_cube_shell",
    "publish_spherical_dictionary",
    "quaternion_rotation_matrix",
    "rank_spherical_dictionary",
    "rotate_canonical_signal_to_sample",
    "verify_spherical_dictionary",
]

from __future__ import annotations

import json

import numpy as np
import pytest

from kikuchi_lab.dictionary.observation import (
    prepare_detector_observation,
    publish_detector_observation_package,
    verify_detector_observation_package,
)
from kikuchi_lab.dictionary.signal_space_bridge import sample_frame_rays_from_gnomonic
from kikuchi_lab.model.recipes import DetectorRecipe
from kikuchi_lab.projection.kikuchipy_adapter import _to_kikuchipy_detector


def _detector() -> DetectorRecipe:
    return DetectorRecipe(
        shape=(5, 7),
        pcx=0.5,
        pcy=0.5,
        pcz=0.8,
        pc_convention="tsl",
        sample_tilt_deg=0.0,
        detector_tilt_deg=0.0,
        detector_azimuth_deg=0.0,
        detector_twist_deg=0.0,
        pixel_size_um=5.0,
        binning=1,
        supersampling=1,
    )


def _directions() -> np.ndarray:
    detector = _to_kikuchipy_detector(_detector())
    pixels = np.asarray(((2.0, 3.0), (1.0, 3.0), (3.0, 3.0)))
    gnomonic = np.asarray(detector.to_gnomonic_coords(pixels), dtype=np.float64)[0]
    matrix = np.asarray(detector.sample_to_detector.to_matrix(), dtype=np.float64)[0]
    return sample_frame_rays_from_gnomonic(gnomonic, matrix)


def test_published_identity_observation_package_is_portable_and_verifiable(tmp_path) -> None:
    detector = _detector()
    image = np.fromfunction(lambda row, column: 10.0 * row + column, detector.shape)

    result = publish_detector_observation_package(
        output_root=tmp_path / "observation",
        detector_intensity=image.astype(np.float32),
        directions=_directions(),
        detector=detector,
        source={"kind": "synthetic", "id": "unit-test", "sha256": "a" * 64},
        observation_version="0.1.0-test",
        created_at="2026-07-22T00:00:00Z",
        authors=("Kikuchi Lab unit test",),
    )

    manifest = json.loads((result.path / "observation.manifest.json").read_text())
    assert manifest["schema"] == "kikuchi.detector-observation/v1"
    assert manifest["preprocessing"]["stages"] == [{"name": "identity", "parameters": {}}]
    assert manifest["adapter"]["projection_model"] == "gnomonic"
    assert (result.path / "observed-detector.npy").is_file()
    assert (result.path / "partial-s2-signal.npz").is_file()
    verification = verify_detector_observation_package(result.path)
    assert verification.observation_id == result.observation_id
    assert verification.direction_count == 3
    assert verification.covered_direction_count >= 2


def test_observation_refuses_hidden_or_nonidentity_preprocessing() -> None:
    detector = _detector()
    image = np.arange(35, dtype=np.float32).reshape(detector.shape)

    with pytest.raises(ValueError, match="identity preprocessing"):
        prepare_detector_observation(
            image,
            _directions(),
            detector,
            preprocessing=({"name": "gaussian_blur", "parameters": {"sigma": 1.0}},),
        )


def test_observation_refuses_mismatched_detector_shape() -> None:
    with pytest.raises(ValueError, match="declared detector shape"):
        prepare_detector_observation(
            np.ones((3, 3), dtype=np.float32),
            _directions(),
            _detector(),
        )

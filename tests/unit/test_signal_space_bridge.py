from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image

from kikuchi_lab.dictionary.signal_space_bridge import _load_rgb, publish_signal_space_bridge


def _write_source_image(path, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (40, 32), color)
    image.save(path)


def test_signal_space_bridge_publishes_labeled_source_bound_bundle(tmp_path) -> None:
    detector = tmp_path / "detector.png"
    master = tmp_path / "master.png"
    directions_path = tmp_path / "directions.npy"
    observed_path = tmp_path / "observed.npy"
    _write_source_image(detector, (32, 48, 64))
    _write_source_image(master, (96, 112, 128))
    np.save(
        directions_path,
        np.asarray(
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, -1.0))
        ),
    )
    np.save(observed_path, np.asarray((0.1, 0.4, 0.8, 0.2), dtype=np.float32))

    result = publish_signal_space_bridge(
        output_root=tmp_path / "bridge",
        detector_image=detector,
        master_image=master,
        directions_path=directions_path,
        observed_signal_path=observed_path,
        source_root=tmp_path,
        phase_name="Ice Ih average oxygen sublattice",
        dictionary_id="ice-ih-test-dictionary",
        dictionary_manifest_sha256="a" * 64,
        dictionary_entry_count=12,
    )

    assert result.path == tmp_path / "bridge"
    assert (result.path / "ice-ih-signal-space-bridge.png").is_file()
    manifest = json.loads((result.path / "signal-space-bridge.json").read_text(encoding="utf-8"))
    assert manifest["phase_name"] == "Ice Ih average oxygen sublattice"
    assert manifest["dictionary"]["id"] == "ice-ih-test-dictionary"
    assert manifest["dictionary"]["entry_count"] == 12
    assert manifest["cache_signal"]["direction_count"] == 4
    assert manifest["claim_boundary"]["hough_space"] == "not represented"
    assert manifest["claim_boundary"]["detector_to_s2_adapter"] == "not implemented"
    assert {entry["path"] for entry in manifest["source_files"]} == {
        "detector.png",
        "directions.npy",
        "master.png",
        "observed.npy",
    }
    checksums = json.loads((result.path / "checksums.json").read_text(encoding="utf-8"))
    assert set(checksums["files"]) == {
        "ice-ih-signal-space-bridge.png",
        "signal-space-bridge.json",
    }


def test_signal_space_bridge_rejects_signal_width_mismatch(tmp_path) -> None:
    detector = tmp_path / "detector.png"
    master = tmp_path / "master.png"
    directions_path = tmp_path / "directions.npy"
    observed_path = tmp_path / "observed.npy"
    _write_source_image(detector, (32, 48, 64))
    _write_source_image(master, (96, 112, 128))
    np.save(directions_path, np.asarray(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))))
    np.save(observed_path, np.asarray((0.1, 0.4, 0.8), dtype=np.float32))

    with pytest.raises(ValueError, match="same number of values"):
        publish_signal_space_bridge(
            output_root=tmp_path / "bridge",
            detector_image=detector,
            master_image=master,
            directions_path=directions_path,
            observed_signal_path=observed_path,
            source_root=tmp_path,
            phase_name="Ice Ih",
            dictionary_id="ice-ih-test-dictionary",
            dictionary_manifest_sha256="a" * 64,
            dictionary_entry_count=12,
        )


def test_signal_space_bridge_preserves_16_bit_grayscale_contrast(tmp_path) -> None:
    source = tmp_path / "sixteen-bit.png"
    values = np.asarray(((0, 32_768), (16_384, 65_535)), dtype=np.uint16)
    Image.frombytes("I;16", (2, 2), values.tobytes()).save(source)

    rendered = _load_rgb(source)

    assert rendered.shape == (2, 2, 3)
    assert rendered[0, 0, 0] == pytest.approx(0.0)
    assert rendered[0, 1, 0] == pytest.approx(32_768 / 65_535)
    assert rendered[1, 1, 0] == pytest.approx(1.0)
    assert np.array_equal(rendered[:, :, 0], rendered[:, :, 1])

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.dictionary import (
    OrientationEntry,
    cube_shell_directions,
    publish_spherical_dictionary,
    rank_spherical_dictionary,
    rotate_canonical_signal_to_sample,
    verify_spherical_dictionary,
)


def _quarter_turn_entries() -> tuple[OrientationEntry, ...]:
    root_half = float(np.sqrt(0.5))
    return (
        OrientationEntry("FST-0000-identity", (1.0, 0.0, 0.0, 0.0)),
        OrientationEntry("FST-0001-z-plus-90", (root_half, 0.0, 0.0, root_half)),
        OrientationEntry("FST-0002-x-plus-90", (root_half, root_half, 0.0, 0.0)),
    )


def test_cube_shell_is_unit_and_closed_under_supported_quarter_turns() -> None:
    directions = cube_shell_directions()

    assert directions.shape == (26, 3)
    assert np.allclose(np.linalg.norm(directions, axis=1), 1.0, rtol=0.0, atol=1e-15)

    signal = np.arange(len(directions), dtype=np.float64)
    for entry in _quarter_turn_entries():
        sample_directions, oriented = rotate_canonical_signal_to_sample(
            directions,
            signal,
            entry,
        )
        assert np.array_equal(sample_directions, directions)
        assert np.array_equal(np.sort(oriented), signal)


def test_orientation_patterns_rank_against_explicit_crystal_to_sample_convention() -> None:
    directions = cube_shell_directions()
    signal = np.arange(len(directions), dtype=np.float64)
    entries = _quarter_turn_entries()
    observed_directions, observed_signal = rotate_canonical_signal_to_sample(
        directions,
        signal,
        entries[1],
    )

    ranked = rank_spherical_dictionary(
        canonical_directions=directions,
        canonical_signal=signal,
        entries=entries,
        sample_directions=observed_directions,
        observed_signal=observed_signal,
    )

    assert ranked[0].entry_id == "FST-0001-z-plus-90"
    assert ranked[0].score == 1.0
    assert ranked[0].root_mean_square_error == 0.0


def test_published_spherical_dictionary_has_portable_contract_and_exact_hashes(
    tmp_path: Path,
) -> None:
    directions = cube_shell_directions()
    signal = np.linspace(0.0, 1.0, len(directions), dtype=np.float64)
    output = tmp_path / "forsterite-fixture"

    result = publish_spherical_dictionary(
        output_root=output,
        dictionary_name="forsterite-spherical-fixture",
        phase={
            "name": "forsterite",
            "formula": "Mg2SiO4",
            "space_group_number": 62,
            "setting": "P n m a",
        },
        source={
            "kind": "synthetic-test-source",
            "source_field_id": "s2-field-test",
            "source_file_sha256": "a" * 64,
            "intensity_channel": "intensity_raw",
        },
        recipe={"name": "unit-test", "schema_version": 1},
        canonical_directions=directions,
        canonical_signal=signal,
        entries=_quarter_turn_entries(),
        validation_entry_id="FST-0001-z-plus-90",
        license_id="CC0-1.0",
        citation_text="Synthetic unit-test provenance only.",
        dictionary_version="0.1.0-fixture",
        created_at="2026-07-20T00:00:00Z",
        authors=("Kikuchi Lab unit test",),
    )

    assert result.path == output
    manifest = json.loads((output / "dictionary.manifest.json").read_text(encoding="utf-8"))
    assert manifest["representation"]["kind"] == "spherical"
    assert manifest["schema_name"] == "ebsd-pattern-dictionary"
    assert manifest["dictionary_version"] == "0.1.0-fixture"
    assert manifest["manifest_sha256"]
    assert manifest["representation_kind"] == "spherical"
    assert manifest["orientation_convention"]["rotation_direction"] == "crystal-to-sample"
    assert manifest["entries"]["count"] == 3
    assert manifest["claim_boundary"]["experimental_ebsd_validated"] is False
    assert (output / "entries.csv").is_file()
    assert (output / "spherical_signal.npz").is_file()
    assert (output / "patterns/FST-0001-z-plus-90.npz").is_file()
    assert (output / "validation/observed-FST-0001-z-plus-90.npz").is_file()

    with np.load(output / "spherical_signal.npz", allow_pickle=False) as archive:
        assert np.array_equal(archive["directions"], directions)
        assert np.array_equal(archive["intensity"], signal)

    checksums = json.loads((output / "checksums.json").read_text(encoding="utf-8"))
    assert "checksums.json" not in checksums["files"]
    for relative_path, record in checksums["files"].items():
        payload = (output / relative_path).read_bytes()
        assert record["bytes"] == len(payload)
        assert record["sha256"] == hashlib.sha256(payload).hexdigest()

    verification = verify_spherical_dictionary(output)
    assert verification.dictionary_id == result.dictionary_id
    assert verification.expected_top_entry_id == "FST-0001-z-plus-90"
    assert verification.file_count == len(checksums["files"])

    with (output / "entries.csv").open("ab") as handle:
        handle.write(b"tampered\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_spherical_dictionary(output)

#!/usr/bin/env python3
"""Render an honest visual bridge for the current Ice Ih S² dictionary input."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from kikuchi_lab.dictionary.ice_ih import verify_ice_ih_candidate_dictionary
from kikuchi_lab.dictionary.signal_space_bridge import publish_signal_space_bridge


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / "local/dictionaries/ice-ih-spherical-candidate-v0.1.3"
DEFAULT_RUN = ROOT / "local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21"
DEFAULT_OUTPUT = ROOT / "local/dictionaries/ice-ih-signal-space-bridge-v0.1.0"
_DETECTOR_PNG = "products/kinematical-detector.png"
_MASTER_PNG = "products/kinematical-master-stereographic.png"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _declared_source_image(run_root: Path, relative_path: str) -> Path:
    manifest_path = run_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(relative_path), dict):
        raise ValueError(f"source run manifest does not declare {relative_path}")
    source = run_root / relative_path
    declared_sha256 = files[relative_path].get("sha256")
    if not isinstance(declared_sha256, str) or _sha256(source) != declared_sha256:
        raise ValueError(f"source run image hash differs from its run manifest: {relative_path}")
    return source


def render(dictionary_root: Path, run_root: Path, output_root: Path) -> None:
    dictionary_root = dictionary_root.resolve()
    run_root = run_root.resolve()
    output_root = output_root.resolve()
    verification = verify_ice_ih_candidate_dictionary(dictionary_root)
    manifest = json.loads((dictionary_root / "dictionary.manifest.json").read_text(encoding="utf-8"))
    cache = manifest.get("candidate_cache")
    validation = manifest.get("validation")
    if not isinstance(cache, dict) or not isinstance(validation, dict):
        raise ValueError("Ice Ih package lacks candidate-cache or validation metadata")
    directions = cache.get("directions_path")
    observed = validation.get("observed_fixture")
    if not isinstance(directions, str) or not isinstance(observed, str):
        raise ValueError("Ice Ih package lacks declared S² input files")
    detector = _declared_source_image(run_root, _DETECTOR_PNG)
    master = _declared_source_image(run_root, _MASTER_PNG)
    result = publish_signal_space_bridge(
        output_root=output_root,
        detector_image=detector,
        master_image=master,
        directions_path=dictionary_root / directions,
        observed_signal_path=dictionary_root / observed,
        source_root=ROOT,
        phase_name="Ice Ih average oxygen sublattice",
        dictionary_id=verification.dictionary_id,
        dictionary_manifest_sha256=manifest["manifest_sha256"],
        dictionary_entry_count=verification.entry_count,
    )
    print(f"Signal-space bridge: {result.path}")
    print(f"Manifest SHA-256: {result.manifest_sha256}")
    print("Matcher input: fixed sample-frame S² feature vector; not detector pixels or Hough space.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        render(args.dictionary, args.run, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

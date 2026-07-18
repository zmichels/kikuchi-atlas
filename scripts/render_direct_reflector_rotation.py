#!/usr/bin/env python3
"""Export a fast, seamless direct-reflector rotation animation from one bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from kikuchi_lab.art_products.rotation_animation import (
    RotationAnimationSpec,
    render_direct_reflector_frame,
    selected_bands_from_snapshots,
)
from kikuchi_lab.model.recipes import Orientation


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/phase-general-direct-reflector-art/series/forsterite-hemisphere-standard-run-1c34e517644729c5"
OUTPUT = ROOT / "local/phase-general-direct-reflector-art/exports/forsterite-oblique-axis-rotation-v1"
BASE_ORIENTATION = Orientation((17.0, 31.0, 43.0))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--frames", type=int, default=144)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        raise ValueError("fps must be positive")
    output = args.output.resolve()
    if output.exists() and (output / "manifest.json").exists():
        raise FileExistsError(f"completed output already exists: {output}")
    catalog_path = SOURCE / "art-band-catalog.json"
    selection_path = SOURCE / "band-selection-ledger.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    bands = selected_bands_from_snapshots(catalog, selection)
    spec = RotationAnimationSpec(
        axis_sample=(2.0, 1.0, 1.0),
        frame_count=args.frames,
        frame_size_px=args.size,
        supersampling=2,
    )
    output.mkdir(parents=True, exist_ok=True)
    frames = output / "frames"
    frames.mkdir(exist_ok=True)
    for index in range(spec.frame_count):
        frame_path = frames / f"frame-{index:04d}.png"
        if not frame_path.exists():
            frame = render_direct_reflector_frame(bands, BASE_ORIENTATION, spec, index)
            frame.save(frame_path, format="PNG", optimize=True)
    shutil.copy2(frames / "frame-0000.png", output / "preview.png")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the MP4 export")
    movie = output / "forsterite-oblique-axis-rotation.mp4"
    partial_movie = output / "forsterite-oblique-axis-rotation.partial.mp4"
    partial_movie.unlink(missing_ok=True)
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"), "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(partial_movie),
        ],
        check=True,
    )
    subprocess.run([ffmpeg, "-v", "error", "-i", str(partial_movie), "-f", "null", "-"], check=True)
    partial_movie.replace(movie)
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"),
            "-vf", "scale=512:512:flags=lanczos", "-loop", "0",
            str(output / "forsterite-oblique-axis-rotation-preview.gif"),
        ],
        check=True,
    )
    manifest = {
        "schema_version": 1,
        "phase": "forsterite",
        "source_bundle": str(SOURCE.relative_to(ROOT)),
        "source_files": {
            catalog_path.name: sha256(catalog_path),
            selection_path.name: sha256(selection_path),
        },
        "selection": {
            "catalog_id": selection["catalog_id"],
            "selection_id": selection["selection_id"],
            "member_ids": [band.member_id for band in bands],
            "width_mm": [band.width_mm for band in bands],
        },
        "rotation": {
            "kind": "active sample-frame axis-angle",
            "axis_sample_proportional": [2, 1, 1],
            "axis_sample_unit": spec.unit_axis_sample.tolist(),
            "base_bunge_zxz_deg": list(BASE_ORIENTATION.euler_bunge_deg),
            "frame": "crystal_to_sample",
            "angle_per_frame_deg": 360.0 / spec.frame_count,
            "loop_contract": "frame_count distinct angles cover [0, 360); the player repeats frame 0",
        },
        "render": {
            "frame_count": spec.frame_count,
            "fps": args.fps,
            "duration_seconds": spec.frame_count / args.fps,
            "frame_size_px": args.size,
            "supersampling": spec.supersampling,
            "great_circle_samples": spec.great_circle_samples,
            "projection": "upper specimen stereographic hemisphere",
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"rotation-animation output={output} frames={spec.frame_count} fps={args.fps}")


if __name__ == "__main__":
    main()

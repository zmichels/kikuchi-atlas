#!/usr/bin/env python3
"""Export dark additive-ribbon rotations from saved direct-reflector catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from kikuchi_lab.art_products.rotation_animation import (
    RotationAnimationSpec,
    render_direct_reflector_depth_frame,
    selected_bands_from_snapshots,
)
from kikuchi_lab.model.recipes import Orientation


ROOT = Path(__file__).resolve().parents[1]
PHASE_SOURCES = {
    "ice-ih": Path("local/phase-general-direct-reflector-art/ice-ih-corrected-reviewed-v2/ice-tattoo-run-a4cecd7a5122f980"),
    "titanite": Path("local/phase-general-direct-reflector-art/series/titanite-hemisphere-standard-run-7a58d5c09fe6273c"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _base_orientation(source: Path) -> Orientation:
    for name in ("hemisphere-composition-recipe.json", "tattoo-recipe.json"):
        candidate = source / name
        if not candidate.is_file():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        content = payload.get("content")
        orientation = content.get("orientation") if isinstance(content, dict) else None
        if isinstance(orientation, dict):
            eulers, frame = orientation.get("euler_bunge_deg"), orientation.get("frame")
            if isinstance(eulers, list) and len(eulers) == 3 and isinstance(frame, str):
                return Orientation(tuple(float(value) for value in eulers), frame=frame)
    raise ValueError(f"source bundle lacks a usable active Bunge orientation: {source}")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=tuple(PHASE_SOURCES), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frames", type=int, default=144)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    args = _args()
    if args.frames < 2 or args.fps <= 0 or args.size < 128:
        raise ValueError("frames >= 2, fps > 0, and size >= 128 are required")
    source = ROOT / PHASE_SOURCES[args.phase]
    output = (
        args.output.resolve()
        if args.output is not None
        else ROOT / f"local/idealized-direct-reflector-depth-rotation/{args.phase}-x-axis-v1"
    )
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    catalog_path = source / "art-band-catalog.json"
    selection_path = source / "band-selection-ledger.json"
    bands = selected_bands_from_snapshots(
        json.loads(catalog_path.read_text(encoding="utf-8")),
        json.loads(selection_path.read_text(encoding="utf-8")),
    )
    orientation = _base_orientation(source)
    spec = RotationAnimationSpec(
        axis_sample=(1.0, 0.0, 0.0),
        frame_count=args.frames,
        frame_size_px=args.size,
        supersampling=2,
    )
    output.mkdir(parents=True)
    frames = output / "frames"
    frames.mkdir()
    for index in range(args.frames):
        render_direct_reflector_depth_frame(bands, orientation, spec, index).save(
            frames / f"frame-{index:04d}.png", format="PNG", optimize=True
        )
    shutil.copy2(frames / "frame-0000.png", output / "preview.png")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the animation")
    stem = f"{args.phase}-direct-reflector-depth-x-axis-rotation"
    movie = output / f"{stem}.mp4"
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"), "-frames:v", str(args.frames),
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(movie),
        ],
        check=True,
    )
    subprocess.run([ffmpeg, "-v", "error", "-i", str(movie), "-f", "null", "-"], check=True)
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"), "-frames:v", str(args.frames),
            "-vf", "scale=512:512:flags=lanczos", "-loop", "0", str(output / f"{stem}.gif"),
        ],
        check=True,
    )
    manifest = {
        "schema_version": 1,
        "product_kind": "idealized direct-reflector additive-ribbon rotation",
        "scientific_boundary": "Exact catalog-derived reflector normals and widths are actively rotated and projected. Ribbon translucency and additive overlap brightness are presentation-only; this is not a detector acquisition or intensity simulation.",
        "phase": args.phase,
        "source_bundle": str(PHASE_SOURCES[args.phase]),
        "source_sha256": {catalog_path.name: _sha256(catalog_path), selection_path.name: _sha256(selection_path)},
        "selection": {"member_ids": [band.member_id for band in bands], "width_mm": [band.width_mm for band in bands]},
        "rotation": {"kind": "active sample-frame x-axis", "axis_sample_unit": [1.0, 0.0, 0.0], "base_bunge_zxz_deg": list(orientation.euler_bunge_deg), "frame_count": args.frames, "angle_per_frame_deg": 360.0 / args.frames, "fps": args.fps, "duration_seconds": args.frames / args.fps},
        "presentation": {"background": "#101519", "band_compositing": "exact trace geometry; width-weighted translucent envelope and core; additive overlap brightness", "frame_size_px": args.size, "supersampling": spec.supersampling},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"output={output} phase={args.phase} frames={args.frames} fps={args.fps}")


if __name__ == "__main__":
    main()

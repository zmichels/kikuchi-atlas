#!/usr/bin/env python3
"""Render a bounded active x-axis grayscale proof from a stored master pattern."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from kikuchi_lab.dynamical_master_rotation import (
    DynamicalMasterRotationSpec,
    DynamicalToneMap,
    render_dynamical_master_frame,
)
from kikuchi_lab.model import load_master_product
from kikuchi_lab.relief.field import build_spherical_scalar_field
from kikuchi_lab.relief.recipes import ReliefSourceExpectation


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER = ROOT / "local/master-patterns/forsterite-proof/COD-9000319-ebsdsim.bundle/master-3042267c1739a530.npz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "local/dynamical-master-rotation/forsterite-x-axis-proof-v1",
    )
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--fps", type=int, default=3)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--gif-size", type=int, default=512)
    parser.add_argument(
        "--product-kind",
        default="proof-grade dynamical-master spherical animation",
    )
    return parser.parse_args()


def contact_sheet(frames: list[Path], destination: Path) -> None:
    columns = 6
    cell = 256
    rows = (len(frames) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell, rows * cell), (14, 20, 23))
    draw = ImageDraw.Draw(canvas)
    for index, path in enumerate(frames):
        image = Image.open(path).convert("RGB").resize((cell, cell), Image.Resampling.LANCZOS)
        x, y = (index % columns) * cell, (index // columns) * cell
        canvas.paste(image, (x, y))
        draw.text((x + 8, y + 8), f"{360.0 * index / len(frames):.0f}°", fill=(230, 235, 238))
    canvas.save(destination, format="PNG", optimize=True)


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        raise ValueError("fps must be positive")
    if args.gif_size <= 0:
        raise ValueError("gif-size must be positive")
    master_path = args.master.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    master = load_master_product(master_path)
    field = build_spherical_scalar_field(
        master,
        ReliefSourceExpectation(
            product_id=master.product_id,
            array_sha256=master.array_sha256,
            file_sha256=sha256(master_path),
        ),
    )
    spec = DynamicalMasterRotationSpec(
        axis_sample=(1.0, 0.0, 0.0),
        frame_count=args.frames,
        frame_size_px=args.size,
    )
    tone = DynamicalToneMap()
    output.mkdir(parents=True)
    frames = output / "frames"
    frames.mkdir()
    frame_paths: list[Path] = []
    for index in range(spec.frame_count):
        path = frames / f"frame-{index:04d}.png"
        render_dynamical_master_frame(field, spec, frame_index=index, tone_map=tone).save(
            path, format="PNG", optimize=True
        )
        frame_paths.append(path)
    shutil.copy2(frame_paths[0], output / "preview.png")
    contact_sheet(frame_paths, output / "contact-sheet.png")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode animation exports")
    movie = output / "forsterite-dynamical-master-x-axis-proof.mp4"
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"), "-c:v", "libx264", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(movie),
        ],
        check=True,
    )
    subprocess.run([ffmpeg, "-v", "error", "-i", str(movie), "-f", "null", "-"], check=True)
    gif = output / "forsterite-dynamical-master-x-axis-proof.gif"
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"),
            "-vf", f"scale={args.gif_size}:{args.gif_size}:flags=lanczos", "-loop", "0", str(gif),
        ],
        check=True,
    )
    black, white = tone.limits(field)
    manifest = {
        "schema_version": 1,
        "product_kind": args.product_kind,
        "scientific_boundary": (
            "Frames are active x-axis resamples of a retained raw dynamical master. "
            "They are not simulated detector acquisitions and no diffraction calculation ran per frame."
        ),
        "source_master": {
            "path": str(master_path.relative_to(ROOT)),
            "file_sha256": sha256(master_path),
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "shape": list(master.intensity.shape),
            "metadata": {
                key: master.metadata_dict()[key]
                for key in ("phase", "generator", "simulation", "coordinate_frame", "intensity_units")
            },
        },
        "rotation": {
            "kind": "active sample-frame x-axis; inverse field lookup in crystal coordinates",
            "axis_sample_unit": spec.unit_axis_sample.tolist(),
            "frame_count": spec.frame_count,
            "angle_per_frame_deg": 360.0 / spec.frame_count,
            "loop_contract": "frame_count distinct angles cover [0, 360); player repeats frame 0",
        },
        "render": {
            "projection": "upper specimen stereographic hemisphere",
            "frame_size_px": spec.frame_size_px,
            "disk_radius_fraction": spec.disk_radius_fraction,
            "lambert_interpolation": "bilinear",
            "tone_map": {
                "black_percentile": tone.black_percentile,
                "white_percentile": tone.white_percentile,
                "gamma": tone.gamma,
                "raw_limits": [black, white],
                "scope": "one source-field mapping shared by every frame",
            },
            "fps": args.fps,
            "duration_seconds": spec.frame_count / args.fps,
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"dynamical-master rotation proof output={output}")


if __name__ == "__main__":
    main()

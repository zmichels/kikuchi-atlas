#!/usr/bin/env python3
"""Animate the retained Ice Ih near-depth presentation field without rerunning diffraction.

The source is the published Ice Ih near-depth stepped-band render.  Every frame
pulls a fixed specimen stereographic hemisphere back through an active
sample-frame rotation, samples the retained two-hemisphere master and the
retained antipodal overlap field, then applies the original presentation-only
optical-depth transform.  This is not a 2-D image rotation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kikuchi_lab.art_products.rotation_animation import axis_angle_matrix
from kikuchi_lab.kinematical.render import asinh_tone_map
from kikuchi_lab.near_depth.overlap import apply_optical_depth


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = Path(
    "local/runs/kinematical-depth-ice-band-led/near-depth-run-90186c9901710abe"
)
SOURCE_KINEMATICAL_RUN = Path("local/runs/kinematical-ice/kinematical-run-8e0fa453f0869a21")
BACKGROUND_RGB = (16, 21, 25)
RIM_RGB = (214, 224, 230)
RIM_FRACTION = 1.0 / 1.025


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_two_hemisphere_field(field: np.ndarray, directions: np.ndarray) -> np.ndarray:
    """Bilinearly sample a [upper, lower] stereographic field at unit directions."""
    upper = directions[:, 2] >= 0.0
    pole = np.where(upper, -1.0, 1.0)
    denominator = 1.0 - pole * directions[:, 2]
    x = directions[:, 0] / denominator
    y = directions[:, 1] / denominator
    size = field.shape[-1]
    column = np.clip((x + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    row = np.clip((y + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    c0, r0 = np.floor(column).astype(np.int64), np.floor(row).astype(np.int64)
    c1, r1 = np.minimum(c0 + 1, size - 1), np.minimum(r0 + 1, size - 1)
    dc, dr = column - c0, row - r0
    plane = np.where(upper, 0, 1)
    return (
        (1.0 - dr) * (1.0 - dc) * field[plane, r0, c0]
        + (1.0 - dr) * dc * field[plane, r0, c1]
        + dr * (1.0 - dc) * field[plane, r1, c0]
        + dr * dc * field[plane, r1, c1]
    )


def _sample_axial_upper_field(field: np.ndarray, directions: np.ndarray) -> np.ndarray:
    """Bilinearly sample an upper-hemisphere field with antipodal ownership."""
    upper = np.where(directions[:, 2:3] >= 0.0, directions, -directions)
    denominator = 1.0 + upper[:, 2]
    x = upper[:, 0] / denominator
    y = upper[:, 1] / denominator
    size = field.shape[-1]
    column = np.clip((x + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    row = np.clip((y + 1.0) * (size - 1) / 2.0, 0.0, size - 1.0)
    c0, r0 = np.floor(column).astype(np.int64), np.floor(row).astype(np.int64)
    c1, r1 = np.minimum(c0 + 1, size - 1), np.minimum(r0 + 1, size - 1)
    dc, dr = column - c0, row - r0
    return (
        (1.0 - dr) * (1.0 - dc) * field[r0, c0]
        + (1.0 - dr) * dc * field[r0, c1]
        + dr * (1.0 - dc) * field[r1, c0]
        + dr * dc * field[r1, c1]
    )


def _screen_directions(size: int) -> tuple[np.ndarray, np.ndarray]:
    """Return an image-row ordered upper stereographic hemisphere and disk mask."""
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinate, coordinate[::-1])
    x /= RIM_FRACTION
    y /= RIM_FRACTION
    radius_squared = x * x + y * y
    valid = radius_squared <= 1.0
    denominator = 1.0 + radius_squared[valid]
    directions = np.empty((int(np.count_nonzero(valid)), 3), dtype=np.float64)
    directions[:, 0] = 2.0 * x[valid] / denominator
    directions[:, 1] = 2.0 * y[valid] / denominator
    directions[:, 2] = (1.0 - radius_squared[valid]) / denominator
    return directions, valid


def _render_frame(
    toned_master: np.ndarray,
    overlap: np.ndarray,
    *,
    normalization: float,
    gain: float,
    ceiling: float,
    screen_directions: np.ndarray,
    screen_valid: np.ndarray,
    rotation: np.ndarray,
) -> Image.Image:
    crystal_directions = screen_directions @ rotation
    base = _sample_two_hemisphere_field(toned_master, crystal_directions)
    additional = _sample_axial_upper_field(overlap, crystal_directions)
    luminance = apply_optical_depth(
        base,
        np.clip(additional / normalization, 0.0, 1.0),
        gain=gain,
        luminance_ceiling=ceiling,
    )
    pixel = np.full((*screen_valid.shape, 3), BACKGROUND_RGB, dtype=np.uint8)
    gray = np.rint(np.clip(luminance, 0.0, 1.0) * 255.0).astype(np.uint8)
    pixel[screen_valid] = gray[:, None]
    image = Image.fromarray(pixel, mode="RGB")
    radius = RIM_FRACTION * (image.width - 1) / 2.0
    center = (image.width - 1) / 2.0
    ImageDraw.Draw(image).ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        outline=RIM_RGB,
        width=max(1, round(image.width / 1600)),
    )
    return image


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frames", type=int, default=144)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.frames < 2 or args.fps <= 0 or args.size < 128:
        raise ValueError("frames >= 2, fps > 0, and size >= 128 are required")
    source_run = ROOT / SOURCE_RUN
    source_kinematical = ROOT / SOURCE_KINEMATICAL_RUN
    output = (
        args.output.resolve()
        if args.output is not None
        else ROOT / "local/idealized-near-depth-rotation/ice-ih-x-axis-band-led-v1"
    )
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")

    master_path = source_kinematical / "products/kinematical-master-stereographic.npy"
    overlap_path = source_run / "diagnostics/overlap-additional-depth.npy"
    ledger_path = source_run / "diagnostics/depth-render-ledger.json"
    source_recipe_path = source_kinematical / "recipes/kinematical.json"
    master = np.load(master_path)
    overlap = np.load(overlap_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    source_recipe = json.loads(source_recipe_path.read_text(encoding="utf-8"))
    tone = source_recipe["tone"]
    toned_master = np.stack(
        [
            asinh_tone_map(master[index], percentiles=tuple(tone["percentiles"]), scale=tone["asinh_scale"])
            for index in (0, 1)
        ]
    ).astype(np.float32)
    screen_directions, screen_valid = _screen_directions(args.size)
    normalization = float(ledger["overlap"]["normalization_value"])
    gain = float(ledger["optical_depth"]["gain"])
    ceiling = float(ledger["optical_depth"]["luminance_ceiling"])

    output.mkdir(parents=True)
    frames = output / "frames"
    frames.mkdir()
    axis = np.array((1.0, 0.0, 0.0), dtype=np.float64)
    for index in range(args.frames):
        rotation = axis_angle_matrix(axis, 360.0 * index / args.frames)
        image = _render_frame(
            toned_master,
            overlap,
            normalization=normalization,
            gain=gain,
            ceiling=ceiling,
            screen_directions=screen_directions,
            screen_valid=screen_valid,
            rotation=rotation,
        )
        image.save(frames / f"frame-{index:04d}.png", format="PNG", optimize=True)
    shutil.copy2(frames / "frame-0000.png", output / "preview.png")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the animation")
    stem = "ice-ih-near-depth-x-axis-rotation"
    movie = output / f"{stem}.mp4"
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
            "-i", str(frames / "frame-%04d.png"), "-frames:v", str(args.frames),
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(movie),
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
        "product_kind": "idealized Ice Ih near-depth retained-field rotation",
        "scientific_boundary": "This is a presentation-only active rotation of retained kinematical master and overlap fields. It is not a detector acquisition, a dynamical master, or a per-frame diffraction simulation.",
        "source": {
            "near_depth_run": str(SOURCE_RUN),
            "kinematical_run": str(SOURCE_KINEMATICAL_RUN),
            "master_sha256": _sha256(master_path),
            "overlap_sha256": _sha256(overlap_path),
            "depth_ledger_sha256": _sha256(ledger_path),
        },
        "rotation": {
            "kind": "active sample-frame x-axis; inverse directional sampling in the retained crystal field",
            "axis_sample_unit": [1.0, 0.0, 0.0],
            "frame_count": args.frames,
            "angle_per_frame_deg": 360.0 / args.frames,
            "fps": args.fps,
            "duration_seconds": args.frames / args.fps,
            "loop_contract": "frame_count distinct angles cover [0, 360); player repeats frame 0",
        },
        "display_treatment": {
            "source_treatment_recipe_id": ledger["treatment_recipe_id"],
            "base_tone": "source pointwise asinh tone map",
            "overlap": ledger["overlap"],
            "optical_depth": ledger["optical_depth"],
            "vector_edge_layer": "not redrawn in this retained-field first animation",
            "background": "#101519",
            "rim": "static circular specimen hemisphere boundary",
        },
        "render": {"frame_size_px": args.size, "field_interpolation": "bilinear", "spatial_filter": "none"},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"output={output} frames={args.frames} size={args.size} fps={args.fps}")


if __name__ == "__main__":
    main()

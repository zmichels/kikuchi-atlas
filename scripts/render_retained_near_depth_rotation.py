#!/usr/bin/env python3
"""Animate a saved kinematical master plus saved near-depth overlap field.

Every frame uses inverse directional sampling through an active sample-frame
x-axis rotation. It neither reruns diffraction nor applies a planar rotation to
the rendered image.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import shutil
import subprocess
from collections import deque
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kikuchi_lab.artifacts.video import (
    encode_and_validate,
    encode_artist_master_exports,
    encode_artist_master_stream,
    file_sha256,
    probe_movie,
)
from kikuchi_lab.art_products.rotation_animation import axis_angle_matrix
from kikuchi_lab.kinematical.render import asinh_tone_map
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.near_depth.overlap import apply_optical_depth
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_RGB = (16, 21, 25)
RIM_RGB = (214, 224, 230)
RIM_FRACTION = 1.0 / 1.025


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    return hashlib.sha256(value.tobytes(order="C")).hexdigest()


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
    """Bilinearly sample one upper-hemisphere field with antipodal ownership."""
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


def _screen_direction_tile(
    size: int, row_start: int, row_stop: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build one bounded row tile of the same stereographic screen grid."""
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(coordinate, coordinate[::-1][row_start:row_stop])
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
    base_orientation: np.ndarray,
) -> Image.Image:
    crystal_directions = screen_directions @ rotation @ base_orientation
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


def _render_frame_tiled(
    toned_master: np.ndarray,
    overlap: np.ndarray,
    *,
    normalization: float,
    gain: float,
    ceiling: float,
    frame_size: int,
    tile_rows: int,
    rotation: np.ndarray,
    base_orientation: np.ndarray,
) -> Image.Image:
    """Render the exact field treatment in bounded row tiles for large frames."""
    pixel = np.full((frame_size, frame_size, 3), BACKGROUND_RGB, dtype=np.uint8)
    for row_start in range(0, frame_size, tile_rows):
        row_stop = min(row_start + tile_rows, frame_size)
        screen_directions, screen_valid = _screen_direction_tile(
            frame_size, row_start, row_stop
        )
        crystal_directions = screen_directions @ rotation @ base_orientation
        base = _sample_two_hemisphere_field(toned_master, crystal_directions)
        additional = _sample_axial_upper_field(overlap, crystal_directions)
        luminance = apply_optical_depth(
            base,
            np.clip(additional / normalization, 0.0, 1.0),
            gain=gain,
            luminance_ceiling=ceiling,
        )
        gray = np.rint(np.clip(luminance, 0.0, 1.0) * 255.0).astype(np.uint8)
        tile = pixel[row_start:row_stop]
        tile[screen_valid] = gray[:, None]
    image = Image.fromarray(pixel, mode="RGB")
    radius = RIM_FRACTION * (image.width - 1) / 2.0
    center = (image.width - 1) / 2.0
    ImageDraw.Draw(image).ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        outline=RIM_RGB,
        width=max(1, round(image.width / 1600)),
    )
    return image


def _render_frames(
    *,
    frames: Path,
    toned_master: np.ndarray,
    overlap: np.ndarray,
    normalization: float,
    gain: float,
    ceiling: float,
    base_orientation: np.ndarray,
    frame_count: int,
    frame_size: int,
    tile_rows: int,
    workers: int,
) -> None:
    axis = np.array((1.0, 0.0, 0.0), dtype=np.float64)

    def render_one(index: int) -> int:
        path = frames / f"frame-{index:04d}.png"
        if path.is_file():
            with Image.open(path) as retained:
                if retained.size != (frame_size, frame_size) or retained.mode != "RGB":
                    raise ValueError(f"retained frame does not match the render plan: {path}")
            return index
        image = _render_frame_tiled(
            toned_master,
            overlap,
            normalization=normalization,
            gain=gain,
            ceiling=ceiling,
            frame_size=frame_size,
            tile_rows=tile_rows,
            rotation=axis_angle_matrix(axis, 360.0 * index / frame_count),
            base_orientation=base_orientation,
        )
        image.save(path, format="PNG", compress_level=1)
        return index

    progress_interval = max(1, min(frame_count, frame_count // 24))
    if workers == 1:
        completed = map(render_one, range(frame_count))
        for index in completed:
            if (index + 1) % progress_interval == 0 or index + 1 == frame_count:
                print(f"rendered {index + 1}/{frame_count} frames", flush=True)
        return
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for index in executor.map(render_one, range(frame_count)):
            if (index + 1) % progress_interval == 0 or index + 1 == frame_count:
                print(f"rendered {index + 1}/{frame_count} frames", flush=True)


def _iter_rendered_images(
    *,
    toned_master: np.ndarray,
    overlap: np.ndarray,
    normalization: float,
    gain: float,
    ceiling: float,
    base_orientation: np.ndarray,
    frame_count: int,
    frame_size: int,
    tile_rows: int,
    workers: int,
) -> Iterator[tuple[int, Image.Image]]:
    """Yield ordered rendered images while allowing bounded concurrent work."""
    axis = np.array((1.0, 0.0, 0.0), dtype=np.float64)

    def render_one(index: int) -> tuple[int, Image.Image]:
        return index, _render_frame_tiled(
            toned_master,
            overlap,
            normalization=normalization,
            gain=gain,
            ceiling=ceiling,
            frame_size=frame_size,
            tile_rows=tile_rows,
            rotation=axis_angle_matrix(axis, 360.0 * index / frame_count),
            base_orientation=base_orientation,
        )

    if workers == 1:
        yield from map(render_one, range(frame_count))
        return
    with ThreadPoolExecutor(max_workers=workers) as executor:
        next_index = 0
        pending = deque()
        while next_index < min(workers, frame_count):
            pending.append(executor.submit(render_one, next_index))
            next_index += 1
        while pending:
            completed = pending.popleft().result()
            if next_index < frame_count:
                pending.append(executor.submit(render_one, next_index))
                next_index += 1
            yield completed


def _relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-slug", required=True)
    parser.add_argument("--phase-label", required=True)
    parser.add_argument("--kinematical-run", type=Path, required=True)
    parser.add_argument("--near-depth-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initial-euler-bunge-deg", nargs=3, type=float)
    parser.add_argument("--edition-slug")
    parser.add_argument("--frames", type=int, default=144)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument(
        "--viewing-size",
        type=int,
        help="H.264 width and height; defaults to half the artist-master size",
    )
    parser.add_argument("--tile-rows", type=int, default=256)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--frame-storage",
        choices=("retain", "stream"),
        default="retain",
        help="retain PNG frames or stream ordered RGB frames directly into the artist master",
    )
    parser.add_argument(
        "--export-profile",
        choices=("standard", "artist-master"),
        default="standard",
    )
    parser.add_argument(
        "--reencode",
        action="store_true",
        help="reuse an exactly matching retained frame plan and rebuild completed movie exports",
    )
    return parser.parse_args()


def main() -> None:
    args = _args()
    if (
        args.frames < 2
        or args.fps <= 0
        or args.size < 128
        or args.tile_rows <= 0
        or args.workers <= 0
    ):
        raise ValueError(
            "frames >= 2, fps > 0, size >= 128, tile-rows > 0, and workers > 0 are required"
        )
    if args.frame_storage == "stream" and args.export_profile != "artist-master":
        raise ValueError("stream frame storage requires the artist-master export profile")
    if args.viewing_size is not None and not 128 <= args.viewing_size <= args.size:
        raise ValueError("viewing-size must be between 128 and size")
    kinematical_run = args.kinematical_run.resolve()
    near_depth_run = args.near_depth_run.resolve()
    output = args.output.resolve()
    if output.exists() and (output / "manifest.json").is_file() and not args.reencode:
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    master_path = kinematical_run / "products" / "kinematical-master-stereographic.npy"
    overlap_path = near_depth_run / "diagnostics" / "overlap-additional-depth.npy"
    ledger_path = near_depth_run / "diagnostics" / "depth-render-ledger.json"
    source_recipe_path = kinematical_run / "recipes" / "kinematical.json"
    near_depth_manifest_path = near_depth_run / "manifest.json"
    for path in (master_path, overlap_path, ledger_path, source_recipe_path, near_depth_manifest_path):
        if not path.is_file():
            raise FileNotFoundError(f"missing retained-field input: {path}")
    master = np.load(master_path, allow_pickle=False)
    overlap = np.load(overlap_path, allow_pickle=False)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    source_recipe = json.loads(source_recipe_path.read_text(encoding="utf-8"))
    near_depth_manifest = json.loads(near_depth_manifest_path.read_text(encoding="utf-8"))
    if master.ndim != 3 or master.shape[0] != 2 or master.shape[1] != master.shape[2]:
        raise ValueError("stored master must have shape [upper, lower, N, N]")
    if overlap.shape != master.shape[1:]:
        raise ValueError("stored overlap must match one master hemisphere")
    expected_master_hash = near_depth_manifest["run_identity"][
        "base_stereographic_array_sha256"
    ]
    if _array_sha256(master) != expected_master_hash:
        raise ValueError("stored master array checksum does not match near-depth input")
    if ledger["base_stereographic_array_sha256"] != near_depth_manifest["run_identity"][
        "base_stereographic_array_sha256"
    ]:
        raise ValueError("near-depth ledger and manifest disagree about their master field")
    tone = source_recipe["tone"]
    toned_master = np.stack(
        [
            asinh_tone_map(
                master[index],
                percentiles=tuple(tone["percentiles"]),
                scale=tone["asinh_scale"],
            )
            for index in (0, 1)
        ]
    ).astype(np.float32)
    if args.initial_euler_bunge_deg is None:
        eulers = source_recipe["orientation"]["euler_bunge_deg"]
        orientation_source = "stored kinematical recipe"
    else:
        eulers = args.initial_euler_bunge_deg
        orientation_source = "explicit animation argument"
    orientation = Orientation(tuple(eulers), frame="crystal_to_sample")
    base_orientation = orientation_matrix(orientation)
    normalization = float(ledger["overlap"]["normalization_value"])
    gain = float(ledger["optical_depth"]["gain"])
    ceiling = float(ledger["optical_depth"]["luminance_ceiling"])

    render_plan = {
        "phase_slug": args.phase_slug,
        "edition_slug": args.edition_slug,
        "kinematical_run": _relative_to_root(kinematical_run),
        "near_depth_run": _relative_to_root(near_depth_run),
        "master_sha256": _sha256(master_path),
        "overlap_sha256": _sha256(overlap_path),
        "initial_euler_bunge_deg": [float(value) for value in eulers],
        "frame_count": args.frames,
        "fps": args.fps,
        "frame_size_px": args.size,
        "viewing_size_px": args.viewing_size,
        "tile_rows": args.tile_rows,
        "frame_storage": args.frame_storage,
        "export_profile": args.export_profile,
    }
    output.mkdir(parents=True, exist_ok=True)
    render_plan_path = output / "render-plan.json"
    if render_plan_path.is_file():
        retained_plan = json.loads(render_plan_path.read_text(encoding="utf-8"))
        if retained_plan != render_plan:
            raise ValueError(f"existing incomplete output has a different render plan: {output}")
    else:
        render_plan_path.write_text(json.dumps(render_plan, indent=2) + "\n", encoding="utf-8")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the animation")
    edition = f"-{args.edition_slug}" if args.edition_slug else ""
    stem = f"{args.phase_slug}-near-depth{edition}-x-axis-rotation"
    if args.frame_storage == "stream":
        progress_interval = max(1, min(args.frames, args.frames // 24))

        def streamed_rgb24_frames() -> Iterator[bytes]:
            for index, image in _iter_rendered_images(
                toned_master=toned_master,
                overlap=overlap,
                normalization=normalization,
                gain=gain,
                ceiling=ceiling,
                base_orientation=base_orientation,
                frame_count=args.frames,
                frame_size=args.size,
                tile_rows=args.tile_rows,
                workers=args.workers,
            ):
                if index == 0:
                    image.save(output / "preview.png", format="PNG", compress_level=1)
                if (index + 1) % progress_interval == 0 or index + 1 == args.frames:
                    print(f"streamed {index + 1}/{args.frames} frames", flush=True)
                yield image.tobytes()

        exports = encode_artist_master_stream(
            ffmpeg=ffmpeg,
            rgb24_frames=streamed_rgb24_frames(),
            output=output,
            stem=stem,
            fps=args.fps,
            size=args.size,
            frame_count=args.frames,
            viewing_size=args.viewing_size,
        )
    else:
        frames = output / "frames"
        frames.mkdir(exist_ok=True)
        _render_frames(
            frames=frames,
            toned_master=toned_master,
            overlap=overlap,
            normalization=normalization,
            gain=gain,
            ceiling=ceiling,
            base_orientation=base_orientation,
            frame_count=args.frames,
            frame_size=args.size,
            tile_rows=args.tile_rows,
            workers=args.workers,
        )
        shutil.copy2(frames / "frame-0000.png", output / "preview.png")
    if args.frame_storage == "retain" and args.export_profile == "artist-master":
        exports = encode_artist_master_exports(
            ffmpeg=ffmpeg,
            frames_pattern=frames / "frame-%04d.png",
            output=output,
            stem=stem,
            fps=args.fps,
            size=args.size,
            viewing_size=args.viewing_size,
        )
    elif args.frame_storage == "retain":
        movie = output / f"{stem}.mp4"
        encode_and_validate(
            [
                ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
                "-i", str(frames / "frame-%04d.png"), "-frames:v", str(args.frames),
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ],
            output / f"{stem}.partial.mp4",
            movie,
        )
        gif = output / f"{stem}.gif"
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
                "-i", str(frames / "frame-%04d.png"), "-frames:v", str(args.frames),
                "-vf", "scale=512:512:flags=lanczos", "-loop", "0", str(gif),
            ],
            check=True,
        )
        exports = {
            "movie": {
                "file": movie.name,
                "role": "viewing-copy",
                "sha256": file_sha256(movie),
                "ffprobe": probe_movie(movie),
            },
            "preview_gif": {
                "file": gif.name,
                "role": "preview",
                "sha256": file_sha256(gif),
            },
        }
    manifest = {
        "schema_version": 1,
        "product_kind": f"idealized {args.phase_label} near-depth retained-field rotation",
        "scientific_boundary": "This is a presentation-only active rotation of retained kinematical master and overlap fields. It is not a detector acquisition, a dynamical master, or a per-frame diffraction simulation.",
        "source": {
            "near_depth_run": _relative_to_root(near_depth_run),
            "kinematical_run": _relative_to_root(kinematical_run),
            "master_sha256": _sha256(master_path),
            "overlap_sha256": _sha256(overlap_path),
            "depth_ledger_sha256": _sha256(ledger_path),
        },
        "rotation": {
            "kind": "active sample-frame x-axis; inverse directional sampling in retained crystal field",
            "axis_sample_unit": [1.0, 0.0, 0.0],
            "initial_orientation": orientation.to_dict(),
            "initial_orientation_source": orientation_source,
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
            "vector_edge_layer": "not redrawn in retained-field animation; static near-depth product retains its band edges",
            "background": "#101519",
            "rim": "static circular specimen hemisphere boundary",
        },
        "render": {
            "frame_size_px": args.size,
            "source_master_shape": list(master.shape),
            "source_overlap_shape": list(overlap.shape),
            "field_interpolation": "bilinear",
            "spatial_filter": "none",
            "tile_rows": args.tile_rows,
            "frame_storage": args.frame_storage,
        },
        "edition_slug": args.edition_slug,
        "export_profile": args.export_profile,
        "exports": exports,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"output={output} frames={args.frames} size={args.size} fps={args.fps}")


if __name__ == "__main__":
    main()

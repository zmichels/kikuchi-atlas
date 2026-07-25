#!/usr/bin/env python3
"""Export a fast, seamless direct-reflector rotation animation from one bundle."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from kikuchi_lab.artifacts.video import (
    encode_and_validate,
    encode_artist_master_exports,
    probe_movie,
)
from kikuchi_lab.art_products.rotation_animation import (
    RotationAnimationSpec,
    render_direct_reflector_frame,
    selected_bands_from_snapshots,
)
from kikuchi_lab.model.recipes import Orientation


ROOT = Path(__file__).resolve().parents[1]
PHASE_SOURCES = {
    "ice-ih": Path("local/phase-general-direct-reflector-art/ice-ih-corrected-reviewed-v2/ice-tattoo-run-a4cecd7a5122f980"),
    "forsterite": Path("local/phase-general-direct-reflector-art/series/forsterite-hemisphere-standard-run-1c34e517644729c5"),
    "quartz": Path("local/phase-general-direct-reflector-art/series/quartz-hemisphere-standard-run-c8e68d027682d562"),
    "zircon": Path("local/phase-general-direct-reflector-art/series/zircon-hemisphere-standard-run-ad71aeef33302d99"),
    "titanite": Path("local/phase-general-direct-reflector-art/series/titanite-hemisphere-standard-run-7a58d5c09fe6273c"),
    "diamond": Path("local/phase-general-direct-reflector-art/exports/diamond-rotated-tattoo-templates-v1/diamond-hemisphere-standard-run-9b89c88619fe53e8"),
    "plagioclase-an52": Path("local/phase-general-direct-reflector-art/exports/plagioclase-an52-standard-plus-orientation-gallery-v1/plagioclase-an52-hemisphere-standard-run-cb6af5ff9f8c51c1"),
    "muscovite-2m1": Path("local/phase-general-direct-reflector-art/exports/muscovite-2m1-standard-plus-orientation-gallery-v1/muscovite-2m1-hemisphere-standard-run-723537ba31df321e"),
    "diopside": Path("local/phase-general-direct-reflector-art/exports/diopside-standard-plus-orientation-gallery-v2/diopside-hemisphere-standard-run-5961de0cf850d6ef"),
    "calcite": Path("local/atlas-expansion/calcite/templates/calcite-hemisphere-standard-run-83d9c94e36df77ed"),
    "enstatite": Path("local/atlas-expansion/enstatite/templates/enstatite-hemisphere-standard-run-5ac8464fe1575028"),
    "pyrope": Path("local/atlas-expansion/pyrope/templates/pyrope-hemisphere-standard-run-cf3ddb145179cc6e"),
}
AXES = {"x": (1.0, 0.0, 0.0), "oblique": (2.0, 1.0, 1.0)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=tuple(PHASE_SOURCES), default="forsterite")
    parser.add_argument("--axis", choices=tuple(AXES), default="oblique")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frames", type=int, default=144)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument(
        "--export-profile",
        choices=("standard", "artist-master"),
        default="standard",
        help=(
            "standard writes the historical H.264 MP4/GIF pair; artist-master writes "
            "a full-resolution ProRes 422 HQ master and a half-resolution H.264 viewing copy"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="parallel frame renderers; use conservatively because supersampled frames are large",
    )
    parser.add_argument(
        "--reencode",
        action="store_true",
        help="reuse an exactly matching retained frame plan and rebuild completed movie exports",
    )
    return parser.parse_args()


def base_orientation(source: Path) -> Orientation:
    """Load the source bundle's explicit active Bunge orientation."""
    for name in ("hemisphere-composition-recipe.json", "tattoo-recipe.json"):
        candidate = source / name
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            content = payload.get("content")
            if isinstance(content, dict):
                orientation = content.get("orientation")
                if isinstance(orientation, dict):
                    eulers = orientation.get("euler_bunge_deg")
                    frame = orientation.get("frame")
                    if isinstance(eulers, list) and len(eulers) == 3 and isinstance(frame, str):
                        return Orientation(tuple(float(value) for value in eulers), frame=frame)
    raise ValueError(f"source bundle lacks a usable active Bunge orientation: {source}")


def render_frame_file(
    index: int,
    frame_path: Path,
    bands: tuple,
    orientation: Orientation,
    spec: RotationAnimationSpec,
) -> int:
    """Render one resumable PNG frame and return its index for progress reporting."""
    if not frame_path.exists():
        frame = render_direct_reflector_frame(bands, orientation, spec, index)
        frame.save(frame_path, format="PNG", optimize=True)
    return index


def render_frames(
    *,
    frames: Path,
    bands: tuple,
    orientation: Orientation,
    spec: RotationAnimationSpec,
    workers: int,
) -> None:
    jobs = [
        (index, frames / f"frame-{index:04d}.png", bands, orientation, spec)
        for index in range(spec.frame_count)
    ]
    if workers == 1:
        completed = (render_frame_file(*job) for job in jobs)
    else:
        executor = ProcessPoolExecutor(max_workers=workers)
        completed = executor.map(_render_frame_job, jobs, chunksize=1)
    try:
        progress_interval = max(1, min(spec.frame_count, spec.frame_count // 24))
        for index in completed:
            if (index + 1) % progress_interval == 0 or index + 1 == spec.frame_count:
                print(f"rendered {index + 1}/{spec.frame_count} frames", flush=True)
    finally:
        if workers != 1:
            executor.shutdown()


def _render_frame_job(job: tuple) -> int:
    """Process-pool adapter kept at module scope so spawn-based workers can import it."""
    return render_frame_file(*job)


def encode_standard_exports(
    *, ffmpeg: str, frames: Path, output: Path, stem: str, fps: int
) -> dict[str, dict[str, object]]:
    movie = output / f"{stem}.mp4"
    encode_and_validate(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps),
            "-i", str(frames / "frame-%04d.png"), "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ],
        output / f"{stem}.partial.mp4",
        movie,
    )
    gif = output / f"{stem}-preview.gif"
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps),
            "-i", str(frames / "frame-%04d.png"),
            "-vf", "scale=512:512:flags=lanczos", "-loop", "0", str(gif),
        ],
        check=True,
    )
    return {
        "movie": {
            "file": movie.name,
            "role": "viewing-copy",
            "sha256": sha256(movie),
            "ffprobe": probe_movie(movie),
        },
        "preview_gif": {"file": gif.name, "role": "preview", "sha256": sha256(gif)},
    }


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        raise ValueError("fps must be positive")
    if args.workers <= 0:
        raise ValueError("workers must be positive")
    source = ROOT / PHASE_SOURCES[args.phase]
    output = (
        args.output.resolve()
        if args.output is not None
        else ROOT / f"local/phase-general-direct-reflector-art/exports/{args.phase}-{args.axis}-axis-rotation-v1"
    )
    if output.exists() and (output / "manifest.json").exists() and not args.reencode:
        raise FileExistsError(f"completed output already exists: {output}")
    catalog_path = source / "art-band-catalog.json"
    selection_path = source / "band-selection-ledger.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    bands = selected_bands_from_snapshots(catalog, selection)
    orientation = base_orientation(source)
    spec = RotationAnimationSpec(
        axis_sample=AXES[args.axis],
        frame_count=args.frames,
        frame_size_px=args.size,
        supersampling=2,
    )
    output.mkdir(parents=True, exist_ok=True)
    frames = output / "frames"
    frames.mkdir(exist_ok=True)
    render_plan = {
        "phase": args.phase,
        "axis": args.axis,
        "frame_count": spec.frame_count,
        "fps": args.fps,
        "frame_size_px": spec.frame_size_px,
        "supersampling": spec.supersampling,
        "export_profile": args.export_profile,
        "source_catalog_sha256": sha256(catalog_path),
        "source_selection_sha256": sha256(selection_path),
    }
    render_plan_path = output / "render-plan.json"
    if render_plan_path.is_file():
        prior_plan = json.loads(render_plan_path.read_text(encoding="utf-8"))
        if prior_plan != render_plan:
            raise ValueError(f"existing incomplete output has a different render plan: {output}")
    else:
        render_plan_path.write_text(json.dumps(render_plan, indent=2) + "\n", encoding="utf-8")
    render_frames(
        frames=frames,
        bands=bands,
        orientation=orientation,
        spec=spec,
        workers=args.workers,
    )
    shutil.copy2(frames / "frame-0000.png", output / "preview.png")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the MP4 export")
    stem = f"{args.phase}-{args.axis}-axis-rotation"
    if args.export_profile == "artist-master":
        exports = encode_artist_master_exports(
            ffmpeg=ffmpeg,
            frames_pattern=frames / "frame-%04d.png",
            output=output,
            stem=stem,
            fps=args.fps,
            size=args.size,
        )
    else:
        exports = encode_standard_exports(
            ffmpeg=ffmpeg, frames=frames, output=output, stem=stem, fps=args.fps
        )
    manifest = {
        "schema_version": 1,
        "phase": args.phase,
        "source_bundle": str(source.relative_to(ROOT)),
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
            "axis_name": args.axis,
            "axis_sample_proportional": list(AXES[args.axis]),
            "axis_sample_unit": spec.unit_axis_sample.tolist(),
            "base_bunge_zxz_deg": list(orientation.euler_bunge_deg),
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
        "export_profile": args.export_profile,
        "exports": exports,
        "claim_boundary": (
            "Idealized direct-reflector science art from crystallographically sourced plane "
            "traces; not a dynamical EBSD intensity simulation or detector acquisition."
        ),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"rotation-animation output={output} frames={spec.frame_count} fps={args.fps}")


if __name__ == "__main__":
    main()

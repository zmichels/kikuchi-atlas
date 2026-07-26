"""Deterministic, decode-checked video exports for retained science-art frames."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    """Hash one retained export without loading the whole file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encode_and_validate(command: list[str], partial: Path, movie: Path) -> None:
    """Atomically publish one movie only after ffmpeg decodes the entire output."""
    partial.unlink(missing_ok=True)
    subprocess.run([*command, str(partial)], check=True)
    subprocess.run(
        [command[0], "-v", "error", "-i", str(partial), "-f", "null", "-"],
        check=True,
    )
    partial.replace(movie)


def probe_movie(path: Path) -> dict[str, Any]:
    """Return bounded media facts suitable for a product manifest."""
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            (
                "stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,"
                "nb_frames,color_range,color_space,color_transfer,color_primaries:"
                "format=duration,size,bit_rate"
            ),
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def encode_artist_master_exports(
    *,
    ffmpeg: str,
    frames_pattern: Path,
    output: Path,
    stem: str,
    fps: int,
    size: int,
    viewing_size: int | None = None,
) -> dict[str, dict[str, object]]:
    """Write a full-resolution 10-bit ProRes master and an H.264 copy."""
    resolved_viewing_size = (
        viewing_size if viewing_size is not None else max(128, size // 2)
    )
    if resolved_viewing_size < 128 or resolved_viewing_size > size:
        raise ValueError("viewing size must be between 128 and the master size")
    master = output / f"{stem}-artist-master.mov"
    encode_and_validate(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(frames_pattern),
            "-map_metadata",
            "-1",
            "-an",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "3",
            "-pix_fmt",
            "yuv422p10le",
            "-vendor",
            "apl0",
            "-movflags",
            "+write_colr",
            "-color_range",
            "tv",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
        ],
        output / f"{stem}-artist-master.partial.mov",
        master,
    )
    viewing = output / f"{stem}-viewing-copy.mp4"
    encode_and_validate(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(frames_pattern),
            "-map_metadata",
            "-1",
            "-an",
            "-vf",
            (
                f"scale={resolved_viewing_size}:{resolved_viewing_size}:"
                "flags=lanczos,format=yuv420p"
            ),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-tune",
            "animation",
            "-crf",
            "12",
            "-movflags",
            "+faststart",
            "-color_range",
            "tv",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-x264-params",
            "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited",
        ],
        output / f"{stem}-viewing-copy.partial.mp4",
        viewing,
    )
    return {
        "artist_master": {
            "file": master.name,
            "role": "editing-master",
            "sha256": file_sha256(master),
            "ffprobe": probe_movie(master),
        },
        "viewing_copy": {
            "file": viewing.name,
            "role": "viewing-copy",
            "sha256": file_sha256(viewing),
            "ffprobe": probe_movie(viewing),
        },
    }


def encode_artist_master_stream(
    *,
    ffmpeg: str,
    rgb24_frames: Iterable[bytes],
    output: Path,
    stem: str,
    fps: int,
    size: int,
    frame_count: int,
    viewing_size: int | None = None,
) -> dict[str, dict[str, object]]:
    """Stream ordered RGB frames into ProRes, then derive the viewing copy."""
    resolved_viewing_size = (
        viewing_size if viewing_size is not None else max(128, size // 2)
    )
    if resolved_viewing_size < 128 or resolved_viewing_size > size:
        raise ValueError("viewing size must be between 128 and the master size")
    master = output / f"{stem}-artist-master.mov"
    partial_master = output / f"{stem}-artist-master.partial.mov"
    partial_master.unlink(missing_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-video_size",
        f"{size}x{size}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-frames:v",
        str(frame_count),
        "-map_metadata",
        "-1",
        "-an",
        "-c:v",
        "prores_ks",
        "-profile:v",
        "3",
        "-pix_fmt",
        "yuv422p10le",
        "-vendor",
        "apl0",
        "-movflags",
        "+write_colr",
        "-color_range",
        "tv",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        str(partial_master),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    expected_bytes = size * size * 3
    written = 0
    try:
        if process.stdin is None:
            raise RuntimeError("ffmpeg streaming encoder has no stdin")
        for payload in rgb24_frames:
            if written >= frame_count:
                raise ValueError("stream yielded more frames than the declared frame count")
            if len(payload) != expected_bytes:
                raise ValueError("streamed RGB frame byte count does not match the declared size")
            process.stdin.write(payload)
            written += 1
        process.stdin.close()
        return_code = process.wait()
    except BaseException:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
        process.wait()
        raise
    if written != frame_count:
        raise ValueError(f"stream yielded {written} frames; expected {frame_count}")
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(partial_master), "-f", "null", "-"],
        check=True,
    )
    partial_master.replace(master)

    viewing = output / f"{stem}-viewing-copy.mp4"
    encode_and_validate(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(master),
            "-map_metadata",
            "-1",
            "-an",
            "-vf",
            (
                f"scale={resolved_viewing_size}:{resolved_viewing_size}:"
                "flags=lanczos,format=yuv420p"
            ),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-tune",
            "animation",
            "-crf",
            "12",
            "-movflags",
            "+faststart",
            "-color_range",
            "tv",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-x264-params",
            "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited",
        ],
        output / f"{stem}-viewing-copy.partial.mp4",
        viewing,
    )
    return {
        "artist_master": {
            "file": master.name,
            "role": "editing-master",
            "sha256": file_sha256(master),
            "ffprobe": probe_movie(master),
        },
        "viewing_copy": {
            "file": viewing.name,
            "role": "viewing-copy",
            "sha256": file_sha256(viewing),
            "ffprobe": probe_movie(viewing),
        },
    }


__all__ = [
    "encode_and_validate",
    "encode_artist_master_exports",
    "encode_artist_master_stream",
    "file_sha256",
    "probe_movie",
]

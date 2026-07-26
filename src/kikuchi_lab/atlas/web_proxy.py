"""Build and validate the single heavyweight Atlas web-proxy profile."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

from .packages import sha256_file


WEB_PROXY_PROFILE = "h264-square-1280-6500k"
MAX_WEB_PROXY_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class WebProxyResult:
    """Verified identity and stream properties for one web proxy."""

    destination: Path
    byte_count: int
    sha256: str
    codec_name: str
    pixel_format: str
    width: int
    height: int
    frame_rate: float
    frame_count: int
    duration_seconds: float


def _regular_file(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")
    try:
        metadata = path.stat()
    except OSError as error:
        raise ValueError(f"{label} is missing: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label} must be a regular file: {path}")
    if metadata.st_nlink != 1:
        raise ValueError(f"{label} must not be a hard link: {path}")


def _run(command: list[str], label: str) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise ValueError(f"{label} failed{suffix}")
    return result


def _probe(path: Path) -> tuple[dict[str, Any], int]:
    probe_command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames:format=duration,size",
        "-of",
        "json",
        str(path),
    ]
    result = _run(probe_command, "web proxy probe")
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("web proxy probe did not return valid JSON") from error
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("streams"), list)
        or len(payload["streams"]) != 1
        or not isinstance(payload["streams"][0], dict)
        or not isinstance(payload.get("format"), dict)
    ):
        raise ValueError("web proxy probe returned an invalid video-stream inventory")
    return payload, int(payload["format"]["size"])


def _validate_profile(path: Path, *, full_decode: bool) -> WebProxyResult:
    _regular_file(path, "web proxy")
    payload, probed_size = _probe(path)
    stream = payload["streams"][0]
    format_record = payload["format"]
    try:
        codec = str(stream["codec_name"])
        pixel_format = str(stream["pix_fmt"])
        width = int(stream["width"])
        height = int(stream["height"])
        frame_rate = float(Fraction(str(stream["avg_frame_rate"])))
        frame_count = int(stream["nb_frames"])
        duration = float(format_record["duration"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError("web proxy probe omitted required stream metadata") from error

    if codec != "h264":
        raise ValueError("web proxy must use H.264")
    if pixel_format != "yuv420p":
        raise ValueError("web proxy must use yuv420p")
    if (width, height) != (1280, 1280):
        raise ValueError("web proxy must be 1280 by 1280 pixels")
    if frame_rate != 60.0:
        raise ValueError("web proxy must be 60 fps")
    if frame_count != 1_440:
        raise ValueError("web proxy must contain 1,440 frames")
    if abs(duration - 24.0) > 0.01:
        raise ValueError("web proxy must be 24.000 seconds within 0.01 seconds")

    actual_size = path.stat().st_size
    if max(actual_size, probed_size) > MAX_WEB_PROXY_BYTES:
        raise ValueError("web proxy must be no larger than 25 MiB")
    if actual_size != probed_size:
        raise ValueError("web proxy byte count differs from ffprobe")

    if full_decode:
        decode_command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-f",
            "null",
            "-",
        ]
        try:
            _run(decode_command, "web proxy full decode")
        except ValueError as error:
            raise ValueError("web proxy full decode failed") from error

    return WebProxyResult(
        destination=path,
        byte_count=actual_size,
        sha256=sha256_file(path),
        codec_name=codec,
        pixel_format=pixel_format,
        width=width,
        height=height,
        frame_rate=frame_rate,
        frame_count=frame_count,
        duration_seconds=duration,
    )


def validate_web_proxy(
    path: str | Path,
    profile: str = WEB_PROXY_PROFILE,
) -> WebProxyResult:
    """Validate a complete web proxy, including a full decode."""
    if profile != WEB_PROXY_PROFILE:
        raise ValueError(f"unsupported web proxy profile: {profile}")
    return _validate_profile(Path(path), full_decode=True)


def build_web_proxy(
    source: str | Path,
    destination: str | Path,
    profile: str,
) -> WebProxyResult:
    """Encode, fully validate, and atomically publish one Atlas web proxy."""
    if profile != WEB_PROXY_PROFILE:
        raise ValueError(f"unsupported web proxy profile: {profile}")
    source_path = Path(source)
    destination_path = Path(destination)
    _regular_file(source_path, "web proxy source")

    if destination_path.exists() or destination_path.is_symlink():
        return validate_web_proxy(destination_path, profile)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    partial = destination_path.with_name(destination_path.name + ".partial")
    if partial.exists() or partial.is_symlink():
        if partial.is_symlink() or not partial.is_file():
            raise ValueError(f"web proxy partial path is unsafe: {partial}")
        partial.unlink()

    encode_command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-vf",
        "scale=1280:1280:flags=lanczos",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-b:v",
        "6500k",
        "-maxrate",
        "7000k",
        "-bufsize",
        "14000k",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        "-f",
        "mp4",
        str(partial),
    ]
    try:
        _run(encode_command, "web proxy encode")
        result = _validate_profile(partial, full_decode=True)
        os.replace(partial, destination_path)
    except Exception:
        if partial.exists() and partial.is_file() and not partial.is_symlink():
            partial.unlink()
        raise
    return WebProxyResult(
        destination=destination_path,
        byte_count=result.byte_count,
        sha256=result.sha256,
        codec_name=result.codec_name,
        pixel_format=result.pixel_format,
        width=result.width,
        height=result.height,
        frame_rate=result.frame_rate,
        frame_count=result.frame_count,
        duration_seconds=result.duration_seconds,
    )


__all__ = [
    "MAX_WEB_PROXY_BYTES",
    "WEB_PROXY_PROFILE",
    "WebProxyResult",
    "build_web_proxy",
    "validate_web_proxy",
]

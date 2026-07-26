from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from kikuchi_lab.atlas.web_proxy import build_web_proxy


PROFILE = "h264-square-1280-6500k"


def _valid_probe(*, size: int = len(b"proxy"), **stream_overrides: object) -> bytes:
    stream = {
        "codec_name": "h264",
        "pix_fmt": "yuv420p",
        "width": 1280,
        "height": 1280,
        "avg_frame_rate": "60/1",
        "nb_frames": "1440",
    }
    stream.update(stream_overrides)
    return json.dumps(
        {
            "streams": [stream],
            "format": {"duration": "24.000000", "size": str(size)},
        }
    ).encode()


def _fake_runner(
    commands: list[list[str]],
    *,
    probe: bytes | None = None,
    decode_returncode: int = 0,
):
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=probe or _valid_probe(),
                stderr=b"",
            )
        if "-y" in command:
            Path(command[-1]).write_bytes(b"proxy")
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")
        return subprocess.CompletedProcess(
            command,
            decode_returncode,
            stdout=b"",
            stderr=b"decode failed" if decode_returncode else b"",
        )

    return run


def test_build_web_proxy_uses_pinned_ffmpeg_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.mov"
    destination = tmp_path / "web" / "proxy.mp4"
    partial = destination.with_name(destination.name + ".partial")
    source.write_bytes(b"source")
    commands: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _fake_runner(commands))

    result = build_web_proxy(source, destination, PROFILE)

    assert commands == [
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(source),
            "-vf", "scale=1280:1280:flags=lanczos",
            "-c:v", "libx264", "-preset", "slow",
            "-b:v", "6500k", "-maxrate", "7000k", "-bufsize", "14000k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
            "-f", "mp4", str(partial),
        ],
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries",
            (
                "stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames:"
                "format=duration,size"
            ),
            "-of", "json", str(partial),
        ],
        [
            "ffmpeg", "-v", "error", "-i", str(partial), "-f", "null", "-",
        ],
    ]
    assert result.frame_count == 1440
    assert result.frame_rate == 60
    assert result.duration_seconds == 24.0
    assert result.byte_count == len(b"proxy")
    assert destination.read_bytes() == b"proxy"
    assert not partial.exists()


@pytest.mark.parametrize(
    ("probe", "message"),
    [
        (_valid_probe(codec_name="hevc"), "H.264"),
        (_valid_probe(pix_fmt="yuv444p"), "yuv420p"),
        (_valid_probe(width=1279), "1280 by 1280"),
        (_valid_probe(avg_frame_rate="30000/1001"), "60 fps"),
        (_valid_probe(nb_frames="1439"), "1,440 frames"),
        (
            json.dumps({
                "streams": [{
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "width": 1280,
                    "height": 1280,
                    "avg_frame_rate": "60/1",
                    "nb_frames": "1440",
                }],
                "format": {"duration": "24.02", "size": "1024"},
            }).encode(),
            "24.000 seconds",
        ),
    ],
)
def test_build_web_proxy_rejects_wrong_stream_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: bytes,
    message: str,
) -> None:
    source = tmp_path / "source.mov"
    destination = tmp_path / "proxy.mp4"
    source.write_bytes(b"source")
    monkeypatch.setattr(subprocess, "run", _fake_runner([], probe=probe))

    with pytest.raises(ValueError, match=message):
        build_web_proxy(source, destination, PROFILE)

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".partial").exists()


def test_build_web_proxy_requires_full_decode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.mov"
    destination = tmp_path / "proxy.mp4"
    source.write_bytes(b"source")
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_runner([], decode_returncode=1),
    )

    with pytest.raises(ValueError, match="full decode"):
        build_web_proxy(source, destination, PROFILE)


def test_build_web_proxy_rejects_file_larger_than_25_mib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.mov"
    destination = tmp_path / "proxy.mp4"
    source.write_bytes(b"source")
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_runner([], probe=_valid_probe(size=26_214_401)),
    )

    with pytest.raises(ValueError, match="25 MiB"):
        build_web_proxy(source, destination, PROFILE)


def test_build_web_proxy_refuses_unknown_profile(tmp_path: Path) -> None:
    source = tmp_path / "source.mov"
    source.write_bytes(b"source")

    with pytest.raises(ValueError, match="unsupported web proxy profile"):
        build_web_proxy(source, tmp_path / "proxy.mp4", "unknown")

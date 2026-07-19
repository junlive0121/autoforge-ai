"""Validated FFmpeg assembly using real narration durations."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.core.media_integrity import (
    publish_media_atomically,
    unique_media_temp_path,
    validate_audio_file,
    validate_image_file,
    validate_video_file,
)


class FFmpegError(RuntimeError):
    """Raised when FFmpeg or ffprobe cannot produce valid media."""


@dataclass(slots=True)
class AssemblyResult:
    output_path: Path
    shot_durations: dict[int, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


async def run_ffmpeg(
    args: list[str],
    *,
    ffmpeg_binary: str = "ffmpeg",
) -> None:
    process = await asyncio.create_subprocess_exec(
        ffmpeg_binary,
        "-y",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-4000:]
        raise FFmpegError(
            f"FFmpeg exited with code {process.returncode}: {detail}"
        )


async def probe_duration(
    path: str | Path,
    *,
    ffprobe_binary: str = "ffprobe",
) -> float:
    process = await asyncio.create_subprocess_exec(
        ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-2000:]
        raise FFmpegError(f"ffprobe failed for {Path(path).name}: {detail}")
    try:
        payload = json.loads(stdout.decode("utf-8"))
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FFmpegError(f"ffprobe returned no valid duration for {path}") from exc
    if duration <= 0:
        raise FFmpegError(f"Audio duration must be positive: {path}")
    return duration


async def assemble_video(
    shots: list[dict[str, Any]],
    output_path: str | Path,
    *,
    ffmpeg_binary: str = "ffmpeg",
    ffprobe_binary: str = "ffprobe",
    padding_seconds: float = 0.2,
) -> AssemblyResult:
    """Render every still/audio pair and atomically publish a verified MP4."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    generation_id = uuid4().hex
    concat_path = destination.parent / f".concat-{generation_id}.txt"
    part_paths: list[Path] = []
    shot_durations: dict[int, float] = {}
    temporary_final = unique_media_temp_path(destination, generation_id)

    try:
        for shot in shots:
            shot_id = int(shot["shot_id"])
            image_path = Path(str(shot["image_path"]))
            audio_path = Path(str(shot["voice_path"]))
            validate_image_file(image_path)
            validate_audio_file(audio_path)
            audio_duration = await probe_duration(
                audio_path,
                ffprobe_binary=ffprobe_binary,
            )
            render_duration = round(audio_duration + padding_seconds, 3)
            shot_durations[shot_id] = render_duration
            part_path = destination.parent / f".part-{generation_id}-{shot_id}.mp4"
            await run_ffmpeg(
                [
                    "-loop",
                    "1",
                    "-i",
                    str(image_path),
                    "-i",
                    str(audio_path),
                    "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-af",
                    f"apad=pad_dur={padding_seconds}",
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(render_duration),
                    str(part_path),
                ],
                ffmpeg_binary=ffmpeg_binary,
            )
            await asyncio.to_thread(
                validate_video_file,
                part_path,
                ffprobe_binary=ffprobe_binary,
            )
            part_paths.append(part_path)

        concat_path.write_text(
            "".join(f"file '{_concat_escape(path.resolve())}'\n" for path in part_paths),
            encoding="utf-8",
        )
        await run_ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c",
                "copy",
                str(temporary_final),
            ],
            ffmpeg_binary=ffmpeg_binary,
        )

        def validator(path: Path) -> dict[str, Any]:
            return validate_video_file(path, ffprobe_binary=ffprobe_binary)

        metadata = await asyncio.to_thread(
            publish_media_atomically,
            temporary_final,
            destination,
            validator,
        )
        return AssemblyResult(destination, shot_durations, metadata)
    finally:
        concat_path.unlink(missing_ok=True)
        temporary_final.unlink(missing_ok=True)
        for path in part_paths:
            path.unlink(missing_ok=True)


def _concat_escape(path: Path) -> str:
    return str(path).replace("'", "'\\''")

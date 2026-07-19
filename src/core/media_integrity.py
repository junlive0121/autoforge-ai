"""Provider-neutral validation and atomic publication for generated media."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True, slots=True)
class MediaIssue:
    severity: Literal["fatal", "warning"]
    stage: str
    shot_id: int | None
    error_type: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "stage": self.stage,
            "shot_id": self.shot_id,
            "error_type": self.error_type,
            "message": self.message,
        }


class ShotValidationError(ValueError):
    def __init__(self, issues: Sequence[MediaIssue]) -> None:
        self.issues = list(issues)
        super().__init__("; ".join(issue.message for issue in self.issues))


def validate_shots(shots: object) -> list[dict[str, Any]]:
    """Validate the minimum contract required before paid media generation."""
    if not isinstance(shots, list) or not shots:
        raise ShotValidationError(
            [MediaIssue("fatal", "storyboard", None, "EmptyShots", "Storyboard has no shots.")]
        )

    issues: list[MediaIssue] = []
    validated: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, raw in enumerate(shots, start=1):
        if not isinstance(raw, Mapping):
            issues.append(
                MediaIssue(
                    "fatal",
                    "storyboard",
                    None,
                    "InvalidShotType",
                    f"Shot at position {index} must be an object.",
                )
            )
            continue
        shot = dict(raw)
        shot_id = shot.get("shot_id")
        if type(shot_id) is not int or shot_id <= 0:
            issues.append(
                MediaIssue(
                    "fatal",
                    "storyboard",
                    shot_id if type(shot_id) is int else None,
                    "InvalidShotId",
                    f"Shot at position {index} requires a positive integer shot_id.",
                )
            )
            continue
        if shot_id in seen:
            issues.append(
                MediaIssue(
                    "fatal",
                    "storyboard",
                    shot_id,
                    "DuplicateShotId",
                    f"Duplicate shot_id is not allowed: {shot_id}.",
                )
            )
            continue
        seen.add(shot_id)
        for field, label in (
            ("voiceover", "voiceover"),
            ("image_prompt", "image prompt"),
        ):
            value = shot.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    MediaIssue(
                        "fatal",
                        "storyboard",
                        shot_id,
                        f"Missing{field.title().replace('_', '')}",
                        f"Shot {shot_id} requires non-empty {label}.",
                    )
                )
        validated.append(shot)

    if issues:
        raise ShotValidationError(issues)
    return sorted(validated, key=lambda shot: int(shot["shot_id"]))


def validate_regular_nonempty(path: str | Path, *, minimum_bytes: int = 1) -> int:
    candidate = Path(path)
    metadata = candidate.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"Media file must not be a symlink: {candidate.name}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"Media path must be a regular file: {candidate.name}")
    if metadata.st_size < minimum_bytes:
        raise ValueError(f"Media file is empty or incomplete: {candidate.name}")
    return metadata.st_size


def validate_audio_file(path: str | Path) -> dict[str, Any]:
    return {"size_bytes": validate_regular_nonempty(path, minimum_bytes=128)}


def validate_image_file(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    size = validate_regular_nonempty(candidate, minimum_bytes=128)
    try:
        with Image.open(candidate) as image:
            image.verify()
        with Image.open(candidate) as image:
            image.load()
            width, height = image.size
            mode = image.mode
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Image is not decodable: {candidate.name}") from exc
    if width <= 0 or height <= 0:
        raise ValueError(f"Image has invalid dimensions: {candidate.name}")
    return {
        "size_bytes": size,
        "width": width,
        "height": height,
        "mode": mode,
    }


def probe_media_file(
    path: str | Path,
    *,
    ffprobe_binary: str = "ffprobe",
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    candidate = Path(path)
    size = validate_regular_nonempty(candidate, minimum_bytes=128)
    completed = subprocess.run(
        [
            ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_name,codec_type",
            "-of",
            "json",
            str(candidate),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise ValueError(f"Media container validation failed: {candidate.name}")
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned invalid data for: {candidate.name}") from exc
    streams = payload.get("streams", []) if isinstance(payload, Mapping) else []
    format_data = payload.get("format", {}) if isinstance(payload, Mapping) else {}
    try:
        duration = float(format_data.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    if not isinstance(streams, list) or duration <= 0:
        raise ValueError(f"Media has no valid duration or streams: {candidate.name}")
    metadata = candidate.stat()
    return {
        "size_bytes": size,
        "mtime_ns": metadata.st_mtime_ns,
        "duration_seconds": duration,
        "streams": streams,
    }


def validate_video_file(
    path: str | Path,
    *,
    ffprobe_binary: str = "ffprobe",
    require_audio: bool = True,
) -> dict[str, Any]:
    metadata = probe_media_file(path, ffprobe_binary=ffprobe_binary)
    streams = metadata["streams"]
    if not any(
        isinstance(stream, Mapping) and stream.get("codec_type") == "video"
        for stream in streams
    ):
        raise ValueError(f"Video has no video stream: {Path(path).name}")
    if require_audio and not any(
        isinstance(stream, Mapping) and stream.get("codec_type") == "audio"
        for stream in streams
    ):
        raise ValueError(f"Video has no audio stream: {Path(path).name}")
    return metadata


def unique_media_temp_path(
    target: str | Path,
    generation_id: str | None = None,
) -> Path:
    destination = Path(target)
    raw = generation_id or uuid4().hex
    generation = re.sub(r"[^A-Za-z0-9_-]", "", raw)[:80] or uuid4().hex
    return destination.with_name(
        f".{destination.stem}.{generation}.{uuid4().hex}.part{destination.suffix}"
    )


def publish_media_atomically(
    temporary_path: str | Path,
    destination_path: str | Path,
    validator: Callable[[Path], Mapping[str, Any] | None],
) -> dict[str, Any]:
    temporary = Path(temporary_path)
    destination = Path(destination_path)
    metadata = dict(validator(temporary) or {})
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary, destination)
    return metadata


def safe_error_message(error: BaseException, *, maximum_length: int = 500) -> str:
    text = str(error).strip() or type(error).__name__
    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)((?:api[_-]?key|token|password)\s*[=:]\s*)[^\s,;]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(r"(https?://[^\s?#]+)\?[^\s]+", r"\1?[REDACTED]", text)
    text = re.sub(
        r"(?i)(?:/Users|/Volumes|/home|/private|/tmp)/[^\s,;:'\"]+",
        "[LOCAL_PATH]",
        text,
    )
    text = re.sub(r"(?i)[A-Z]:\\[^\s,;:'\"]+", "[LOCAL_PATH]", text)
    return text[:maximum_length]

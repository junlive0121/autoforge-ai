"""Reusable safety and media-integrity primitives."""

from src.core.file_protocol import (
    CorruptJsonError,
    InterProcessFileLock,
    UnsafePathError,
    atomic_write_json,
    ensure_path_within,
    lock_path_for,
    read_json_object,
)
from src.core.media_integrity import (
    MediaIssue,
    publish_media_atomically,
    safe_error_message,
    unique_media_temp_path,
    validate_audio_file,
    validate_image_file,
    validate_regular_nonempty,
    validate_shots,
    validate_video_file,
)

__all__ = [
    "CorruptJsonError",
    "InterProcessFileLock",
    "MediaIssue",
    "UnsafePathError",
    "atomic_write_json",
    "ensure_path_within",
    "lock_path_for",
    "publish_media_atomically",
    "read_json_object",
    "safe_error_message",
    "unique_media_temp_path",
    "validate_audio_file",
    "validate_image_file",
    "validate_regular_nonempty",
    "validate_shots",
    "validate_video_file",
]

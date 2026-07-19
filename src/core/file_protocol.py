"""Safe local-file primitives for durable standalone project state."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any
from uuid import uuid4

if os.name == "nt":  # pragma: no cover - Windows only.
    import msvcrt
else:
    import fcntl


class UnsafePathError(ValueError):
    """Raised when a resolved path leaves its trusted root."""


class CorruptJsonError(ValueError):
    """A malformed JSON file that has been quarantined."""

    def __init__(self, path: Path, quarantined_path: Path, reason: str) -> None:
        self.path = path
        self.quarantined_path = quarantined_path
        super().__init__(
            f"Malformed JSON was quarantined: {path.name} -> "
            f"{quarantined_path.name} ({reason})"
        )


class InterProcessFileLock:
    """Advisory exclusive lock backed by a neighbouring lock file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._handle: Any | None = None

    def __enter__(self) -> "InterProcessFileLock":
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    def acquire(self) -> None:
        if self._handle is not None:
            raise RuntimeError(f"Lock is already acquired: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.path, flags, 0o600)
        handle = os.fdopen(descriptor, "r+b", buffering=0)
        try:
            if os.name == "nt":  # pragma: no cover - Windows only.
                if os.fstat(descriptor).st_size == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
        except BaseException:
            handle.close()
            raise
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        descriptor = self._handle.fileno()
        try:
            if os.name == "nt":  # pragma: no cover - Windows only.
                self._handle.seek(0)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


def ensure_path_within(root: str | Path, candidate: str | Path) -> Path:
    """Resolve a child path and prove it remains below ``root``."""
    trusted_root = Path(root).expanduser().resolve(strict=False)
    resolved = Path(candidate).expanduser().resolve(strict=False)
    if resolved == trusted_root or not resolved.is_relative_to(trusted_root):
        raise UnsafePathError(f"Path escapes its trusted root: {candidate}")
    return resolved


def lock_path_for(path: str | Path) -> Path:
    state_path = Path(path)
    return state_path.with_name(f".{state_path.name}.lock")


def read_json_object(
    path: str | Path,
    *,
    default: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read a JSON object and quarantine malformed content."""
    json_path = Path(path)
    if not json_path.exists():
        return dict(default or {})
    if json_path.is_symlink():
        raise UnsafePathError(f"JSON state file must not be a symlink: {json_path}")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON root must be an object")
        return payload
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        quarantined = quarantine_file(json_path)
        raise CorruptJsonError(json_path, quarantined, str(exc)) from exc


def quarantine_file(path: str | Path) -> Path:
    source = Path(path)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = source.with_name(
        f"{source.name}.corrupt-{timestamp}-{uuid4().hex}"
    )
    os.replace(source, destination)
    _fsync_directory(source.parent)
    return destination


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Durably publish one JSON object through a unique sibling temp file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":  # pragma: no cover - Windows has no directory fsync.
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)

"""Durable, process-safe project state stored beside generated assets."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.file_protocol import (
    CorruptJsonError,
    InterProcessFileLock,
    UnsafePathError,
    atomic_write_json,
    ensure_path_within,
    lock_path_for,
    read_json_object,
)


class ProjectRepository:
    """Persist the public demo's project lifecycle without a database server."""

    _PROJECT_ID = re.compile(r"^[0-9a-f]{12}$")
    _TERMINAL = frozenset({"completed", "failed", "interrupted"})

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root).expanduser().resolve(strict=False)

    def create(
        self,
        project_id: str,
        idea: str,
        *,
        demo: bool = False,
    ) -> dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)
        project_path = self.project_path(project_id)
        project_path.mkdir(parents=False, exist_ok=False)
        state = {
            "project_id": project_id,
            "status": "pending",
            "idea": idea,
            "demo": demo,
            "created_at": self._now(),
            "updated_at": self._now(),
            "plan": None,
            "shots": None,
            "video_path": None,
            "error": None,
        }
        self._write(project_id, state)
        return state

    def get(self, project_id: str) -> dict[str, Any]:
        state_path = self.state_path(project_id, require_exists=True)
        with InterProcessFileLock(lock_path_for(state_path)):
            try:
                state = read_json_object(state_path)
            except CorruptJsonError as exc:
                state = {
                    "project_id": project_id,
                    "status": "failed",
                    "created_at": self._now(),
                    "updated_at": self._now(),
                    "error": str(exc),
                }
                atomic_write_json(state_path, state)
        if not state:
            raise FileNotFoundError(project_id)
        return state

    def update(
        self,
        project_id: str,
        status: str,
        **details: Any,
    ) -> dict[str, Any]:
        state_path = self.state_path(project_id, require_exists=True)
        with InterProcessFileLock(lock_path_for(state_path)):
            try:
                state = read_json_object(state_path)
            except CorruptJsonError as exc:
                state = {
                    "project_id": project_id,
                    "created_at": self._now(),
                    "error": str(exc),
                }
                status = "failed"
            state.update(details)
            state["project_id"] = project_id
            state["status"] = status
            state["updated_at"] = self._now()
            atomic_write_json(state_path, state)
            return state

    def reconcile_interrupted(self) -> list[str]:
        """Mark projects left active by a previous process as interrupted."""
        if not self.output_root.is_dir():
            return []
        interrupted: list[str] = []
        for candidate in self.output_root.iterdir():
            if not candidate.is_dir() or not self._PROJECT_ID.fullmatch(candidate.name):
                continue
            try:
                state = self.get(candidate.name)
                if state.get("status") not in self._TERMINAL:
                    self.update(
                        candidate.name,
                        "interrupted",
                        error="Service restarted before the project completed.",
                    )
                    interrupted.append(candidate.name)
            except (FileNotFoundError, OSError, UnsafePathError):
                continue
        return interrupted

    def project_path(
        self,
        project_id: str,
        *,
        require_exists: bool = False,
    ) -> Path:
        if not self._PROJECT_ID.fullmatch(project_id):
            raise ValueError("project_id must be 12 lowercase hexadecimal characters")
        candidate = self.output_root / project_id
        ensure_path_within(self.output_root, candidate)
        if candidate.is_symlink():
            raise UnsafePathError(f"Project directory must not be a symlink: {project_id}")
        if require_exists and not candidate.is_dir():
            raise FileNotFoundError(project_id)
        return candidate

    def project_file(
        self,
        project_id: str,
        filename: str,
        *,
        require_exists: bool = False,
    ) -> Path:
        if Path(filename).name != filename:
            raise UnsafePathError(f"Nested asset paths are not allowed: {filename}")
        project = self.project_path(project_id, require_exists=True)
        candidate = ensure_path_within(project, project / filename)
        if candidate.is_symlink():
            raise UnsafePathError(f"Project file must not be a symlink: {filename}")
        if require_exists and not candidate.is_file():
            raise FileNotFoundError(filename)
        return candidate

    def state_path(self, project_id: str, *, require_exists: bool = False) -> Path:
        project = self.project_path(project_id, require_exists=require_exists)
        state_path = ensure_path_within(project, project / "project.json")
        if require_exists and not state_path.is_file():
            raise FileNotFoundError(project_id)
        return state_path

    def _write(self, project_id: str, state: dict[str, Any]) -> None:
        state_path = self.state_path(project_id, require_exists=False)
        with InterProcessFileLock(lock_path_for(state_path)):
            atomic_write_json(state_path, state)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

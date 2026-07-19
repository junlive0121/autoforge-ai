"""Integration tests for durable background project state and safe failures."""

import asyncio
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from src.api import routes
from src.repositories.project_repository import ProjectRepository


PROJECT_ID = "abcdef012345"


def test_background_success_is_persisted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = ProjectRepository(tmp_path)
    repository.create(PROJECT_ID, "Explain photosynthesis")

    async def fake_pipeline(idea: str, project_id: str) -> dict:
        assert idea == "Explain photosynthesis"
        assert project_id == PROJECT_ID
        return {
            "plan": {"title": "Photosynthesis"},
            "shots": [{"shot_id": 1}],
            "video_path": "final.mp4",
            "video_metadata": {"duration_seconds": 12.0},
        }

    monkeypatch.setattr(routes, "project_repository", repository)
    monkeypatch.setattr(routes, "run_pipeline", fake_pipeline)

    asyncio.run(routes._run_background(PROJECT_ID, "Explain photosynthesis"))

    state = repository.get(PROJECT_ID)
    assert state["status"] == "completed"
    assert state["video_path"] == "final.mp4"
    assert state["error"] is None


def test_background_failure_is_persisted_broadcast_and_redacted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = ProjectRepository(tmp_path)
    repository.create(PROJECT_ID, "Explain gravity")
    events: list[dict] = []

    async def failing_pipeline(idea: str, project_id: str) -> dict:
        raise RuntimeError(
            "token=private-value /Volumes/private-lab/source/failed.mp4"
        )

    async def capture_broadcast(project_id: str, event: dict) -> None:
        events.append(event)

    monkeypatch.setattr(routes, "project_repository", repository)
    monkeypatch.setattr(routes, "run_pipeline", failing_pipeline)
    monkeypatch.setattr(routes, "broadcast", capture_broadcast)

    asyncio.run(routes._run_background(PROJECT_ID, "Explain gravity"))

    state = repository.get(PROJECT_ID)
    assert state["status"] == "failed"
    assert "private-value" not in state["error"]
    assert "private-lab" not in state["error"]
    assert events == [{"stage": "error", "message": state["error"]}]

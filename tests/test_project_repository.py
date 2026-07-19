"""Durable public project lifecycle tests."""

from pathlib import Path

import pytest

from src.core.file_protocol import UnsafePathError
from src.repositories.project_repository import ProjectRepository


PROJECT_ID = "012345abcdef"


def test_project_state_survives_repository_recreation(tmp_path: Path) -> None:
    repository = ProjectRepository(tmp_path)
    repository.create(PROJECT_ID, "Explain gravity with a classroom animation")
    repository.update(PROJECT_ID, "running", plan={"title": "Gravity"})

    reloaded = ProjectRepository(tmp_path).get(PROJECT_ID)

    assert reloaded["status"] == "running"
    assert reloaded["plan"] == {"title": "Gravity"}
    assert reloaded["idea"].startswith("Explain gravity")


def test_reconcile_marks_unfinished_work_as_interrupted(tmp_path: Path) -> None:
    repository = ProjectRepository(tmp_path)
    repository.create(PROJECT_ID, "A lesson")

    assert repository.reconcile_interrupted() == [PROJECT_ID]
    assert repository.get(PROJECT_ID)["status"] == "interrupted"


def test_completed_project_is_not_reconciled(tmp_path: Path) -> None:
    repository = ProjectRepository(tmp_path)
    repository.create(PROJECT_ID, "A lesson")
    repository.update(PROJECT_ID, "completed", video_path="final.mp4")

    assert repository.reconcile_interrupted() == []
    assert repository.get(PROJECT_ID)["status"] == "completed"


def test_repository_rejects_invalid_ids_and_nested_assets(tmp_path: Path) -> None:
    repository = ProjectRepository(tmp_path)

    with pytest.raises(ValueError):
        repository.create("../../private", "A lesson")

    repository.create(PROJECT_ID, "A lesson")
    with pytest.raises(UnsafePathError):
        repository.project_file(PROJECT_ID, "../secret.env")

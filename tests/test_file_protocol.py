"""Durability and containment tests for public project state."""

import json
from pathlib import Path

import pytest

from src.core.file_protocol import (
    CorruptJsonError,
    UnsafePathError,
    atomic_write_json,
    ensure_path_within,
    read_json_object,
)


def test_atomic_json_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "project.json"

    atomic_write_json(state_path, {"status": "running", "title": "课堂短片"})

    assert read_json_object(state_path) == {
        "status": "running",
        "title": "课堂短片",
    }


def test_corrupt_json_is_quarantined(tmp_path: Path) -> None:
    state_path = tmp_path / "project.json"
    state_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(CorruptJsonError) as raised:
        read_json_object(state_path)

    assert not state_path.exists()
    assert raised.value.quarantined_path.is_file()
    assert raised.value.quarantined_path.read_text(encoding="utf-8") == "{not-json"


def test_path_containment_rejects_escape_and_root(tmp_path: Path) -> None:
    assert ensure_path_within(tmp_path, tmp_path / "child") == tmp_path / "child"

    with pytest.raises(UnsafePathError):
        ensure_path_within(tmp_path, tmp_path)
    with pytest.raises(UnsafePathError):
        ensure_path_within(tmp_path, tmp_path / ".." / "outside")


def test_atomic_json_never_leaves_temp_file(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    atomic_write_json(state_path, {"version": 1})
    atomic_write_json(state_path, {"version": 2})

    assert json.loads(state_path.read_text(encoding="utf-8")) == {"version": 2}
    assert list(tmp_path.glob(".state.json.*.tmp")) == []

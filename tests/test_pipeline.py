"""Pipeline integration without external provider calls."""

import asyncio
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from src import pipeline
from src.services.ffmpeg_service import AssemblyResult


def test_pipeline_returns_only_public_asset_names(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events: list[dict] = []

    class FakeDirector:
        async def plan(self, idea: str) -> dict:
            return {"title": "Gravity", "tone": "educational"}

    class FakeWriter:
        async def generate(self, plan: dict) -> dict:
            return {"scenes": [{"narration": "Objects attract each other."}]}

    class FakeStoryboard:
        async def generate(self, script: dict) -> list[dict]:
            return [
                {
                    "shot_id": 1,
                    "voiceover": "Objects attract each other.",
                    "image_prompt": "A clear classroom gravity diagram",
                    "duration_seconds": 3,
                }
            ]

    class FakeVoice:
        async def generate(
            self,
            text: str,
            shot_id: int,
            output_dir: Path,
            voice: str,
        ) -> Path:
            path = output_dir / f"voice_{shot_id}.mp3"
            path.write_bytes(b"voice")
            return path

    class FakeImage:
        async def generate(
            self,
            prompt: str,
            shot_id: int,
            output_dir: Path,
        ) -> Path:
            path = output_dir / f"image_{shot_id}.png"
            path.write_bytes(b"image")
            return path

    async def fake_assemble(
        shots: list[dict],
        output_path: Path,
        **kwargs,
    ) -> AssemblyResult:
        output_path.write_bytes(b"video")
        return AssemblyResult(
            output_path=output_path,
            shot_durations={1: 2.4},
            metadata={"duration_seconds": 2.4, "streams": []},
        )

    async def capture(project_id: str, event: dict) -> None:
        events.append(event)

    monkeypatch.setattr(pipeline.settings, "output_dir", str(tmp_path))
    monkeypatch.setattr(pipeline, "DirectorAgent", FakeDirector)
    monkeypatch.setattr(pipeline, "WriterAgent", FakeWriter)
    monkeypatch.setattr(pipeline, "StoryboardAgent", FakeStoryboard)
    monkeypatch.setattr(pipeline, "VoiceAgent", FakeVoice)
    monkeypatch.setattr(pipeline, "ImageAgent", FakeImage)
    monkeypatch.setattr(pipeline, "assemble_video", fake_assemble)
    monkeypatch.setattr(pipeline, "broadcast", capture)

    result = asyncio.run(
        pipeline.run_pipeline(
            "Explain gravity to a middle-school class",
            "123456abcdef",
        )
    )

    shot = result["shots"][0]
    assert result["video_path"] == "final.mp4"
    assert shot["voice_path"] == "voice_1.mp3"
    assert shot["image_path"] == "image_1.png"
    assert shot["render_duration_seconds"] == 2.4
    assert str(tmp_path) not in str(result)
    assert [event["stage"] for event in events] == [
        "director",
        "plan",
        "writer",
        "script",
        "storyboard_start",
        "storyboard",
        "media",
        "media_progress",
        "assembly",
        "done",
    ]

"""End-to-end FFmpeg validation for one generated shot."""

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from src.services.ffmpeg_service import assemble_video


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe are required",
)
def test_assembly_uses_audio_duration_and_publishes_valid_video(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "image_1.png"
    audio_path = tmp_path / "voice_1.mp3"
    output_path = tmp_path / "final.mp4"
    Image.new("RGB", (640, 360), color=(40, 80, 140)).save(image_path)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.6",
            "-q:a",
            "4",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
    )

    result = asyncio.run(
        assemble_video(
            [
                {
                    "shot_id": 1,
                    "image_path": str(image_path),
                    "voice_path": str(audio_path),
                }
            ],
            output_path,
        )
    )

    assert result.output_path == output_path
    assert output_path.is_file()
    assert 0.7 <= result.shot_durations[1] <= 1.1
    stream_types = {stream["codec_type"] for stream in result.metadata["streams"]}
    assert stream_types == {"audio", "video"}
    assert result.metadata["duration_seconds"] >= 0.6
    assert list(tmp_path.glob(".*.part.mp4")) == []

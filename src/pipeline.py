"""Pipeline — orchestrates all agents into a complete video production run."""

import asyncio
import subprocess
import uuid
from pathlib import Path

from src.agents.director import DirectorAgent
from src.agents.writer import WriterAgent
from src.agents.storyboard import StoryboardAgent
from src.agents.media import VoiceAgent, ImageAgent
from src.config import settings


async def run_pipeline(idea: str) -> dict:
    """Execute the full video production pipeline.

    Returns:
        A dict with project metadata and the path to the final video.
    """
    project_id = uuid.uuid4().hex[:12]
    output_dir = Path(settings.output_dir) / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Stage 1: Planning ---
    director = DirectorAgent()
    plan = await director.plan(idea)

    # --- Stage 2: Script ---
    writer = WriterAgent()
    script = await writer.generate(plan)

    # --- Stage 3: Storyboard ---
    storyboard = StoryboardAgent()
    shots = await storyboard.generate(script)

    # --- Stage 4: Media generation (parallel per shot) ---
    voice_agent = VoiceAgent()
    image_agent = ImageAgent()

    async def _produce_shot(shot: dict) -> dict:
        voice_path, image_path = await asyncio.gather(
            voice_agent.generate(shot["voiceover"], shot["shot_id"], output_dir),
            image_agent.generate(shot["image_prompt"], shot["shot_id"], output_dir),
        )
        return {**shot, "voice_path": str(voice_path), "image_path": str(image_path)}

    results = await asyncio.gather(*[_produce_shot(s) for s in shots])

    # --- Stage 5: FFmpeg assembly ---
    video_path = output_dir / "final.mp4"
    _assemble_video(results, video_path)

    return {
        "project_id": project_id,
        "status": "completed",
        "plan": plan,
        "shots": results,
        "video_path": str(video_path),
    }


def _assemble_video(shots: list[dict], output_path: Path) -> None:
    """Combine images + audio into a single video using FFmpeg."""
    concat_file = output_path.parent / "concat.txt"
    parts: list[str] = []

    for i, shot in enumerate(shots):
        part_path = output_path.parent / f"part_{i}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", shot["image_path"],
            "-i", shot["voice_path"],
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(part_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        parts.append(str(part_path))

    # Write concat list
    concat_file.write_text("\n".join(f"file '{p}'" for p in parts))

    # Concat all parts
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )

    # Cleanup temp parts
    for p in parts:
        Path(p).unlink(missing_ok=True)
    concat_file.unlink(missing_ok=True)

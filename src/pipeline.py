"""Pipeline — orchestrates all agents into a complete video production run."""

import asyncio
import logging
import uuid
from pathlib import Path

from src.agents.director import DirectorAgent
from src.agents.writer import WriterAgent
from src.agents.storyboard import StoryboardAgent
from src.agents.media import VoiceAgent, ImageAgent, select_voice
from src.config import settings

logger = logging.getLogger("autoforge.pipeline")


async def run_pipeline(idea: str, project_id: str | None = None) -> dict:
    """Execute the full video production pipeline.

    Returns:
        A dict with project metadata and the path to the final video.
    """
    project_id = project_id or uuid.uuid4().hex[:12]
    output_dir = Path(settings.output_dir) / project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("[%s] Pipeline started", project_id)

    # --- Stage 1: Planning ---
    logger.info("[%s] Stage 1/5 — Director", project_id)
    director = DirectorAgent()
    plan = await director.plan(idea)
    voice = select_voice(plan.get("tone"))

    # --- Stage 2: Script ---
    logger.info("[%s] Stage 2/5 — Writer", project_id)
    writer = WriterAgent()
    script = await writer.generate(plan)

    # --- Stage 3: Storyboard ---
    logger.info("[%s] Stage 3/5 — Storyboard", project_id)
    storyboard = StoryboardAgent()
    shots = await storyboard.generate(script)

    # --- Stage 4: Media generation (parallel per shot) ---
    logger.info("[%s] Stage 4/5 — Media generation (%d shots)", project_id, len(shots))
    voice_agent = VoiceAgent()
    image_agent = ImageAgent()

    async def _produce_shot(shot: dict) -> dict:
        voice_path, image_path = await asyncio.gather(
            voice_agent.generate(shot["voiceover"], shot["shot_id"], output_dir, voice),
            image_agent.generate(shot["image_prompt"], shot["shot_id"], output_dir),
        )
        return {
            **shot,
            "voice_path": str(voice_path),
            "image_path": str(image_path),
        }

    results = await asyncio.gather(*[_produce_shot(s) for s in shots])

    # --- Stage 5: FFmpeg assembly ---
    logger.info("[%s] Stage 5/5 — FFmpeg assembly", project_id)
    video_path = output_dir / "final.mp4"
    await _assemble_video(results, video_path)

    logger.info("[%s] Pipeline complete → %s", project_id, video_path)
    return {
        "project_id": project_id,
        "status": "completed",
        "plan": plan,
        "shots": results,
        "video_path": str(video_path),
    }


async def _assemble_video(shots: list[dict], output_path: Path) -> None:
    """Combine images + audio into a single video using FFmpeg (async)."""
    output_dir = output_path.parent
    concat_file = output_dir / "concat.txt"
    parts: list[str] = []

    for i, shot in enumerate(shots):
        part_path = output_dir / f"part_{i}.mp4"
        proc = await asyncio.create_subprocess_exec(
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
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        parts.append(str(part_path))

    # Write concat list
    concat_file.write_text(
        "\n".join(f"file '{p}'" for p in parts)
    )

    # Concat all parts
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()

    # Cleanup temp parts
    for p in parts:
        Path(p).unlink(missing_ok=True)
    concat_file.unlink(missing_ok=True)

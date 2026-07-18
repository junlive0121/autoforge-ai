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
from src.ws import broadcast

logger = logging.getLogger("autoforge.pipeline")


async def _emit(project_id: str, event: dict) -> None:
    """Broadcast a progress event to connected WebSocket clients."""
    await broadcast(project_id, event)


async def run_pipeline(idea: str, project_id: str | None = None) -> dict:
    """Execute the full video production pipeline."""
    project_id = project_id or uuid.uuid4().hex[:12]
    output_dir = Path(settings.output_dir) / project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("[%s] Pipeline started", project_id)

    # --- Stage 1: Planning ---
    await _emit(project_id, {"stage": "director"})
    director = DirectorAgent()
    plan = await director.plan(idea)
    voice = select_voice(plan.get("tone"))
    await _emit(project_id, {"stage": "plan", "data": plan})

    # --- Stage 2: Script ---
    await _emit(project_id, {"stage": "writer"})
    writer = WriterAgent()
    script = await writer.generate(plan)
    await _emit(project_id, {"stage": "script", "data": script})

    # --- Stage 3: Storyboard ---
    await _emit(project_id, {"stage": "storyboard_start"})
    storyboard = StoryboardAgent()
    shots = await storyboard.generate(script)
    await _emit(project_id, {"stage": "storyboard", "data": shots, "count": len(shots)})

    # --- Stage 4: Media generation (parallel per shot) ---
    await _emit(project_id, {"stage": "media"})
    voice_agent = VoiceAgent()
    image_agent = ImageAgent()
    image_urls = []

    async def _produce_shot(shot: dict) -> dict:
        voice_path, image_path = await asyncio.gather(
            voice_agent.generate(shot["voiceover"], shot["shot_id"], output_dir, voice),
            image_agent.generate(shot["image_prompt"], shot["shot_id"], output_dir),
        )
        image_urls.append(f"/api/projects/{project_id}/assets/{image_path.name}")
        await _emit(project_id, {
            "stage": "media_progress",
            "shot_id": shot["shot_id"],
            "image_url": image_urls[-1],
        })
        return {**shot, "voice_path": str(voice_path), "image_path": str(image_path)}

    results = await asyncio.gather(*[_produce_shot(s) for s in shots])

    # --- Stage 5: FFmpeg assembly ---
    await _emit(project_id, {"stage": "assembly", "images": image_urls})
    video_path = output_dir / "final.mp4"
    await _assemble_video(results, video_path)

    await _emit(project_id, {
        "stage": "done",
        "plan": plan,
        "shots": results,
        "video_path": str(video_path),
    })

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
        duration = shot.get("duration_seconds", 5)
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
            "-t", str(duration),
            str(part_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        parts.append(str(part_path))

    concat_file.write_text(
        "\n".join(f"file '{p}'" for p in parts)
    )

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

    for p in parts:
        Path(p).unlink(missing_ok=True)
    concat_file.unlink(missing_ok=True)

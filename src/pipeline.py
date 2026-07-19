"""Pipeline — orchestrates all agents into a complete video production run."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from src.agents.director import DirectorAgent
from src.agents.writer import WriterAgent
from src.agents.storyboard import StoryboardAgent
from src.agents.media import VoiceAgent, ImageAgent, select_voice
from src.config import settings
from src.core.media_integrity import safe_error_message, validate_shots
from src.services.ffmpeg_service import assemble_video
from src.ws import broadcast

logger = logging.getLogger("autoforge.pipeline")


class MediaGenerationError(RuntimeError):
    """One or more shots could not produce complete image/audio assets."""


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
    shots = validate_shots(await storyboard.generate(script))
    await _emit(project_id, {"stage": "storyboard", "data": shots, "count": len(shots)})

    # --- Stage 4: Media generation (parallel per shot) ---
    await _emit(project_id, {"stage": "media"})
    voice_agent = VoiceAgent()
    image_agent = ImageAgent()
    semaphore = asyncio.Semaphore(settings.max_parallel_shots)

    async def _produce_shot(shot: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            voice_outcome, image_outcome = await asyncio.gather(
                voice_agent.generate(
                    shot["voiceover"],
                    shot["shot_id"],
                    output_dir,
                    voice,
                ),
                image_agent.generate(
                    shot["image_prompt"],
                    shot["shot_id"],
                    output_dir,
                ),
                return_exceptions=True,
            )
            shot_failures = [
                safe_error_message(outcome)
                for outcome in (voice_outcome, image_outcome)
                if isinstance(outcome, BaseException)
            ]
            if shot_failures:
                raise MediaGenerationError(
                    f"Shot {shot['shot_id']} failed media generation: "
                    f"{shot_failures[0]}"
                )
            voice_path = Path(str(voice_outcome))
            image_path = Path(str(image_outcome))
            image_url = f"/api/projects/{project_id}/assets/{image_path.name}"
            await _emit(
                project_id,
                {
                    "stage": "media_progress",
                    "shot_id": shot["shot_id"],
                    "image_url": image_url,
                },
            )
            return {
                **shot,
                "voice_path": str(voice_path),
                "image_path": str(image_path),
                "image_url": image_url,
            }

    outcomes = await asyncio.gather(
        *[_produce_shot(shot) for shot in shots],
        return_exceptions=True,
    )
    failures = [
        safe_error_message(outcome)
        for outcome in outcomes
        if isinstance(outcome, BaseException)
    ]
    if failures:
        raise MediaGenerationError(
            f"{len(failures)} of {len(shots)} shots failed media generation. "
            f"First failure: {failures[0]}"
        )
    results = [
        outcome
        for outcome in outcomes
        if isinstance(outcome, dict)
    ]
    image_urls = [str(result["image_url"]) for result in results]

    # --- Stage 5: FFmpeg assembly ---
    await _emit(project_id, {"stage": "assembly", "images": image_urls})
    video_path = output_dir / "final.mp4"
    assembly = await assemble_video(
        results,
        video_path,
        ffmpeg_binary=settings.ffmpeg_binary,
        ffprobe_binary=settings.ffprobe_binary,
    )
    public_results: list[dict[str, Any]] = []
    for shot in results:
        shot_id = int(shot["shot_id"])
        public_results.append(
            {
                **shot,
                "voice_path": Path(str(shot["voice_path"])).name,
                "image_path": Path(str(shot["image_path"])).name,
                "render_duration_seconds": assembly.shot_durations[shot_id],
            }
        )

    await _emit(project_id, {
        "stage": "done",
        "plan": plan,
        "shots": public_results,
        "video_path": "final.mp4",
    })

    logger.info("[%s] Pipeline complete → %s", project_id, video_path)
    return {
        "project_id": project_id,
        "status": "completed",
        "plan": plan,
        "shots": public_results,
        "video_path": "final.mp4",
        "video_metadata": assembly.metadata,
    }

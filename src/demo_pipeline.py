"""Deterministic classroom sample that exercises the public media pipeline."""

from __future__ import annotations

import asyncio
import logging
import shutil
import textwrap
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from src.config import settings
from src.core.media_integrity import (
    publish_media_atomically,
    unique_media_temp_path,
    validate_audio_file,
    validate_image_file,
)
from src.services.ffmpeg_service import (
    AssemblyResult,
    assemble_video,
    probe_duration,
    run_ffmpeg,
)
from src.ws import broadcast

logger = logging.getLogger("autoforge.demo")


async def _emit(project_id: str, event: dict[str, Any]) -> None:
    await broadcast(project_id, event)


async def run_demo_pipeline(idea: str, project_id: str) -> dict[str, Any]:
    """Generate a transparent, provider-free sample lesson for judge testing."""
    output_dir = Path(settings.output_dir) / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = {
        "title": "Photosynthesis in 30 Seconds",
        "tone": "educational",
        "audience": "middle-school science students",
        "learning_objective": (
            "Explain how plants convert sunlight, water, and carbon dioxide "
            "into glucose and oxygen."
        ),
        "style": "clean classroom infographic",
        "source_idea": idea,
        "mode": "deterministic sample",
    }
    script = {
        "scenes": [
            {
                "scene_number": 1,
                "description": "Sunlight reaches a leaf.",
                "narration": (
                    "Photosynthesis begins when chlorophyll in a leaf captures "
                    "energy from sunlight."
                ),
            },
            {
                "scene_number": 2,
                "description": "Water and carbon dioxide enter the process.",
                "narration": (
                    "The plant combines that energy with water from its roots "
                    "and carbon dioxide from the air."
                ),
            },
            {
                "scene_number": 3,
                "description": "The plant produces glucose and oxygen.",
                "narration": (
                    "The result is glucose, which stores chemical energy, and "
                    "oxygen, which is released back into the atmosphere."
                ),
            },
        ]
    }
    shots = [
        {
            "shot_id": 1,
            "scene_number": 1,
            "title": "Capture sunlight",
            "voiceover": script["scenes"][0]["narration"],
            "image_prompt": "Classroom infographic: sunlight entering a green leaf.",
            "duration_seconds": 6,
            "accent": "#F9C74F",
        },
        {
            "shot_id": 2,
            "scene_number": 2,
            "title": "Combine inputs",
            "voiceover": script["scenes"][1]["narration"],
            "image_prompt": "Classroom infographic: water and carbon dioxide enter a leaf.",
            "duration_seconds": 7,
            "accent": "#4CC9F0",
        },
        {
            "shot_id": 3,
            "scene_number": 3,
            "title": "Store energy",
            "voiceover": script["scenes"][2]["narration"],
            "image_prompt": "Classroom infographic: glucose and oxygen leave a leaf.",
            "duration_seconds": 7,
            "accent": "#80ED99",
        },
    ]

    await _emit(project_id, {"stage": "director"})
    await asyncio.sleep(0.35)
    await _emit(project_id, {"stage": "plan", "data": plan})
    await _emit(project_id, {"stage": "writer"})
    await asyncio.sleep(0.35)
    await _emit(project_id, {"stage": "script", "data": script})
    await _emit(project_id, {"stage": "storyboard_start"})
    await asyncio.sleep(0.35)
    await _emit(
        project_id,
        {"stage": "storyboard", "data": shots, "count": len(shots)},
    )
    await _emit(project_id, {"stage": "media"})

    results: list[dict[str, Any]] = []
    for shot in shots:
        shot_id = int(shot["shot_id"])
        image_path = output_dir / f"image_{shot_id}.png"
        voice_path = output_dir / f"voice_{shot_id}.mp3"
        await asyncio.gather(
            asyncio.to_thread(_create_lesson_frame, shot, image_path),
            _create_demo_voice(str(shot["voiceover"]), voice_path),
        )
        image_url = f"/api/projects/{project_id}/assets/{image_path.name}"
        results.append(
            {
                **shot,
                "image_path": str(image_path),
                "voice_path": str(voice_path),
                "image_url": image_url,
            }
        )
        await _emit(
            project_id,
            {
                "stage": "media_progress",
                "shot_id": shot_id,
                "image_url": image_url,
            },
        )
        await asyncio.sleep(0.25)

    await _emit(
        project_id,
        {
            "stage": "assembly",
            "images": [str(result["image_url"]) for result in results],
        },
    )
    video_path = output_dir / "final.mp4"
    assembly = await assemble_video(
        results,
        video_path,
        ffmpeg_binary=settings.ffmpeg_binary,
        ffprobe_binary=settings.ffprobe_binary,
    )
    public_results = _public_results(results, assembly)
    await _emit(
        project_id,
        {
            "stage": "done",
            "plan": plan,
            "shots": public_results,
            "video_path": "final.mp4",
        },
    )
    logger.info("[%s] Sample lesson complete", project_id)
    return {
        "project_id": project_id,
        "status": "completed",
        "plan": plan,
        "shots": public_results,
        "video_path": "final.mp4",
        "video_metadata": assembly.metadata,
    }


def _public_results(
    results: list[dict[str, Any]],
    assembly: AssemblyResult,
) -> list[dict[str, Any]]:
    return [
        {
            **shot,
            "image_path": Path(str(shot["image_path"])).name,
            "voice_path": Path(str(shot["voice_path"])).name,
            "render_duration_seconds": assembly.shot_durations[int(shot["shot_id"])],
        }
        for shot in results
    ]


def _create_lesson_frame(shot: dict[str, Any], output_path: Path) -> None:
    temporary = unique_media_temp_path(output_path)
    try:
        image = Image.new("RGB", (1280, 720), "#07130F")
        draw = ImageDraw.Draw(image)
        title_font = _font(54, bold=True)
        body_font = _font(30)
        label_font = _font(24, bold=True)
        accent = str(shot["accent"])

        draw.rounded_rectangle((54, 48, 1226, 672), radius=36, fill="#10251D")
        draw.text((96, 82), "AUTOFORGE CLASSROOM", font=label_font, fill=accent)
        draw.text((96, 132), str(shot["title"]), font=title_font, fill="#F5FFF8")
        _draw_process_diagram(draw, int(shot["shot_id"]), accent, label_font)

        narration = textwrap.wrap(str(shot["voiceover"]), width=55)
        draw.multiline_text(
            (96, 530),
            "\n".join(narration),
            font=body_font,
            fill="#D4EADF",
            spacing=10,
        )
        image.save(temporary, "PNG")
        publish_media_atomically(temporary, output_path, validate_image_file)
    finally:
        temporary.unlink(missing_ok=True)


def _draw_process_diagram(
    draw: ImageDraw.ImageDraw,
    shot_id: int,
    accent: str,
    font: ImageFont.ImageFont,
) -> None:
    leaf_box = (520, 250, 760, 455)
    draw.ellipse(leaf_box, fill="#2D6A4F", outline="#80ED99", width=8)
    draw.line((640, 455, 640, 495), fill="#80ED99", width=14)
    if shot_id == 1:
        draw.ellipse((160, 250, 290, 380), fill="#F9C74F")
        draw.line((300, 315, 490, 340), fill=accent, width=12)
        draw.text((150, 400), "SUNLIGHT", font=font, fill="#F5FFF8")
    elif shot_id == 2:
        draw.text((120, 270), "H₂O", font=font, fill="#4CC9F0")
        draw.text((955, 270), "CO₂", font=font, fill="#F5FFF8")
        draw.line((220, 325, 490, 350), fill="#4CC9F0", width=12)
        draw.line((940, 325, 790, 350), fill="#F5FFF8", width=12)
    else:
        draw.text((105, 285), "GLUCOSE", font=font, fill="#80ED99")
        draw.text((985, 285), "O₂", font=font, fill="#4CC9F0")
        draw.line((490, 350, 300, 325), fill="#80ED99", width=12)
        draw.line((790, 350, 960, 325), fill="#4CC9F0", width=12)


async def _create_demo_voice(text: str, output_path: Path) -> None:
    source_path = output_path.with_name(f".voice-source-{uuid4().hex}.aiff")
    temporary = unique_media_temp_path(output_path)
    narration_created = False
    try:
        if shutil.which("say"):
            try:
                await _run_checked_command(
                    [
                        "say",
                        "-v",
                        "Samantha",
                        "-r",
                        "170",
                        "-o",
                        str(source_path),
                        text,
                    ]
                )
                await probe_duration(
                    source_path,
                    ffprobe_binary=settings.ffprobe_binary,
                )
                await _convert_voice_source(source_path, temporary)
                narration_created = True
            except Exception as exc:
                logger.warning("System narration unavailable; using silent sample: %s", exc)
        if not narration_created and shutil.which("espeak"):
            source_path.unlink(missing_ok=True)
            source_path = source_path.with_suffix(".wav")
            try:
                await _run_checked_command(["espeak", "-w", str(source_path), text])
                await probe_duration(
                    source_path,
                    ffprobe_binary=settings.ffprobe_binary,
                )
                await _convert_voice_source(source_path, temporary)
                narration_created = True
            except Exception as exc:
                logger.warning("espeak narration unavailable; using silent sample: %s", exc)
        if not narration_created:
            estimated_duration = max(3.0, len(text.split()) / 2.4)
            await run_ffmpeg(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=44100:cl=mono",
                    "-t",
                    str(estimated_duration),
                    "-codec:a",
                    "libmp3lame",
                    str(temporary),
                ],
                ffmpeg_binary=settings.ffmpeg_binary,
            )
        publish_media_atomically(temporary, output_path, validate_audio_file)
    finally:
        source_path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


async def _convert_voice_source(source_path: Path, temporary: Path) -> None:
    await run_ffmpeg(
        [
            "-i",
            str(source_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(temporary),
        ],
        ffmpeg_binary=settings.ffmpeg_binary,
    )


async def _run_checked_command(args: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"Sample narration command failed: {detail}")


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()

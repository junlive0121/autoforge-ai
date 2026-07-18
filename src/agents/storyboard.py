"""Storyboard Agent — Generates scene and shot breakdowns."""

import logging

from src.openai_client import client
from src.config import settings
from src.utils import parse_llm_json, retry

logger = logging.getLogger("autoforge.storyboard")

SYSTEM_PROMPT = """You are the Storyboard Agent of an AI video production pipeline.
Given a script (JSON), break it into individual shots ready for image and voice generation.

For each shot, produce:
- "shot_id": sequential int (1, 2, 3...)
- "scene_number": which scene this belongs to
- "image_prompt": a detailed DALL-E-style prompt describing the visual (style, composition, lighting, mood). Be specific and vivid.
- "voiceover": the exact narration text for this shot
- "dialogue": optional list of {"character": "...", "line": "..."} if this shot has character speech
- "duration_seconds": how long this shot should last (3-10)

Keep total shots between 6-12. Return ONLY valid JSON, no markdown fences."""


class StoryboardAgent:
    """Converts a script into detailed scene/shot specifications."""

    @retry()
    async def generate(self, script: dict) -> list[dict]:
        logger.info("Storyboard: breaking script into shots")
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": __import__("json").dumps(script, ensure_ascii=False)},
            ],
            temperature=0.7,
        )
        shots = parse_llm_json(response.choices[0].message.content)
        if isinstance(shots, dict):
            shots = shots.get("shots", shots.get("scenes", []))
        logger.info("Storyboard: %d shots planned", len(shots))
        return shots

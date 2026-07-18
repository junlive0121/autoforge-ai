"""Writer Agent — Drafts scripts and narrative content from a production plan."""

import logging

from src.openai_client import client
from src.config import settings
from src.utils import parse_llm_json, retry

logger = logging.getLogger("autoforge.writer")

SYSTEM_PROMPT = """You are the Writer Agent of an AI video production pipeline.
Given a production plan (JSON), write a complete script.

Output a JSON object with:
- "scenes": a list of scene objects, each containing:
  - "scene_number": int
  - "description": what happens in this scene
  - "narration": the voiceover text for this scene (engaging, 2-4 sentences)
  - "dialogue": optional list of {"character": "...", "line": "..."} if characters speak

Return ONLY valid JSON, no markdown fences."""


class WriterAgent:
    """Converts a production plan into a detailed script with dialogue and narration."""

    @retry()
    async def generate(self, plan: dict) -> dict:
        logger.info("Writer: generating script for '%s'", plan.get("title", "untitled"))
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": __import__("json").dumps(plan, ensure_ascii=False)},
            ],
            temperature=0.8,
        )
        script = parse_llm_json(response.choices[0].message.content)
        scene_count = len(script.get("scenes", []))
        logger.info("Writer: script done — %d scenes", scene_count)
        return script

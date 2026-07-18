"""Writer Agent — Drafts scripts and narrative content from a production plan."""

import json

from src.openai_client import client
from src.config import settings

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

    async def generate(self, plan: dict) -> dict:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(plan, ensure_ascii=False)},
            ],
            temperature=0.8,
        )
        return json.loads(response.choices[0].message.content)

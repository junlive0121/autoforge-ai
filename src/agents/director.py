"""Director Agent — Plans and delegates video production tasks."""

import json

from src.openai_client import client
from src.config import settings

SYSTEM_PROMPT = """You are the Director Agent of an AI video production pipeline.
Given a raw story idea, produce a JSON production plan with these fields:
- "title": short video title
- "tone": narrative tone (e.g. dramatic, comedic, educational)
- "characters": list of character names and brief descriptions
- "scenes": list of scene summaries (3-6 scenes)
- "target_duration_seconds": estimated total length (30-120)
- "style": visual style (e.g. photorealistic, anime, watercolor)

Return ONLY valid JSON, no markdown fences."""


class DirectorAgent:
    """Decomposes a story idea into a structured production plan."""

    async def plan(self, idea: str) -> dict:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": idea},
            ],
            temperature=0.7,
        )
        return json.loads(response.choices[0].message.content)

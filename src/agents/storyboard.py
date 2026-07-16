"""Storyboard Agent — Generates scene and shot breakdowns."""


class StoryboardAgent:
    """Converts a script into detailed scene/shot specifications."""

    async def generate(self, script: dict) -> list[dict]:
        raise NotImplementedError

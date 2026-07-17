"""Storyboard Agent — Generates scene and shot breakdowns."""


class StoryboardAgent:
    """Converts a script into detailed scene/shot specifications."""

    async def generate(self, script: dict) -> list[dict]:
        """Break a script down into individual shots with visual prompts.

        Args:
            script: Structured script from WriterAgent.

        Returns:
            A list of shot dicts, each containing image_prompt, voiceover, and duration.
        """
        raise NotImplementedError

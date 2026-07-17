"""Writer Agent — Drafts scripts and narrative content from a production plan."""


class WriterAgent:
    """Converts a production plan into a detailed script with dialogue and narration."""

    async def generate(self, plan: dict) -> dict:
        """Turn a production plan into a full script.

        Args:
            plan: Structured production plan from DirectorAgent.

        Returns:
            A dict containing scenes, narration, and dialogue.
        """
        raise NotImplementedError

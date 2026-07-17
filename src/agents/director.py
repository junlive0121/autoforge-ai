"""Director Agent — Plans and delegates video production tasks."""


class DirectorAgent:
    """Decomposes a story idea into a structured production plan."""

    async def plan(self, idea: str) -> dict:
        """Parse a raw story idea and produce a structured production plan.

        Args:
            idea: A natural-language story idea from the user.

        Returns:
            A dict outlining scenes, characters, tone, and asset requirements.
        """
        raise NotImplementedError

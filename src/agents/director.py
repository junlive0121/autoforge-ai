"""Director Agent — Plans and delegates video production tasks."""


class DirectorAgent:
    """Decomposes a story idea into a structured production plan."""

    async def plan(self, idea: str) -> dict:
        raise NotImplementedError

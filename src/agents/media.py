"""Media Agents — Voice and image generation."""


class VoiceAgent:
    """Generates narration and dialogue audio."""

    async def generate(self, text: str) -> str:
        raise NotImplementedError


class ImageAgent:
    """Generates scene images from prompts."""

    async def generate(self, prompt: str) -> str:
        raise NotImplementedError

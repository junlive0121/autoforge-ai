"""Media Agents — Voice and image generation."""


class VoiceAgent:
    """Generates narration and dialogue audio via TTS."""

    async def generate(self, text: str) -> str:
        """Synthesize speech from text.

        Args:
            text: The narration or dialogue content.

        Returns:
            File path to the generated audio file.
        """
        raise NotImplementedError


class ImageAgent:
    """Generates scene images from text prompts."""

    async def generate(self, prompt: str) -> str:
        """Generate an image from a scene description.

        Args:
            prompt: A detailed visual prompt for the scene.

        Returns:
            File path to the generated image file.
        """
        raise NotImplementedError

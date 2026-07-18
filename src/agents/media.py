"""Media Agents — Voice and image generation."""

import logging
from pathlib import Path

from src.openai_client import client
from src.config import settings
from src.utils import retry

logger = logging.getLogger("autoforge.media")

# Tone → voice mapping
VOICE_MAP = {
    "dramatic": "onyx",
    "comedic": "nova",
    "educational": "fable",
    "neutral": "alloy",
    "default": "alloy",
}


def select_voice(tone: str | None = None) -> str:
    if not tone:
        return VOICE_MAP["default"]
    return VOICE_MAP.get(tone.lower(), VOICE_MAP["default"])


class VoiceAgent:
    """Generates narration and dialogue audio via OpenAI TTS."""

    @retry()
    async def generate(
        self, text: str, shot_id: int, output_dir: Path, voice: str = "alloy"
    ) -> Path:
        output_path = output_dir / f"voice_{shot_id}.mp3"
        logger.info("Voice: generating audio for shot %d (voice=%s)", shot_id, voice)
        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )
        output_path.write_bytes(response.content)
        logger.info("Voice: shot %d saved to %s", shot_id, output_path)
        return output_path


class ImageAgent:
    """Generates scene images from text prompts via DALL-E."""

    @retry()
    async def generate(self, prompt: str, shot_id: int, output_dir: Path) -> Path:
        import httpx

        output_path = output_dir / f"image_{shot_id}.png"
        logger.info("Image: generating for shot %d", shot_id)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        async with httpx.AsyncClient() as http:
            img_resp = await http.get(image_url)
            output_path.write_bytes(img_resp.content)
        logger.info("Image: shot %d saved to %s", shot_id, output_path)
        return output_path

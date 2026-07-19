"""Media Agents — Voice and image generation."""

import logging
from pathlib import Path

from src.openai_client import client
from src.core.media_integrity import (
    publish_media_atomically,
    unique_media_temp_path,
    validate_audio_file,
    validate_image_file,
)
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
        temporary_path = unique_media_temp_path(output_path)
        logger.info("Voice: generating audio for shot %d (voice=%s)", shot_id, voice)
        try:
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
            )
            temporary_path.write_bytes(response.content)
            publish_media_atomically(
                temporary_path,
                output_path,
                validate_audio_file,
            )
        finally:
            temporary_path.unlink(missing_ok=True)
        logger.info("Voice: shot %d saved to %s", shot_id, output_path)
        return output_path


class ImageAgent:
    """Generates scene images from text prompts via DALL-E."""

    @retry()
    async def generate(self, prompt: str, shot_id: int, output_dir: Path) -> Path:
        import httpx

        output_path = output_dir / f"image_{shot_id}.png"
        temporary_path = unique_media_temp_path(output_path)
        logger.info("Image: generating for shot %d", shot_id)
        try:
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            if not image_url:
                raise ValueError("Image provider returned no downloadable URL.")
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                follow_redirects=True,
            ) as http:
                img_resp = await http.get(image_url)
                img_resp.raise_for_status()
                content_type = img_resp.headers.get("content-type", "").lower()
                if not content_type.startswith("image/"):
                    raise ValueError(
                        f"Image download returned unexpected content type: {content_type or 'missing'}"
                    )
                temporary_path.write_bytes(img_resp.content)
            publish_media_atomically(
                temporary_path,
                output_path,
                validate_image_file,
            )
        finally:
            temporary_path.unlink(missing_ok=True)
        logger.info("Image: shot %d saved to %s", shot_id, output_path)
        return output_path

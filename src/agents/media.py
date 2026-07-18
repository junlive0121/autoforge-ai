"""Media Agents — Voice and image generation."""

import asyncio
from pathlib import Path

from openai import APIStatusError

from src.openai_client import client
from src.config import settings


class VoiceAgent:
    """Generates narration and dialogue audio via OpenAI TTS."""

    async def generate(self, text: str, shot_id: int, output_dir: Path) -> Path:
        output_path = output_dir / f"voice_{shot_id}.mp3"

        response = await client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        response.stream_to_file(str(output_path))
        return output_path


class ImageAgent:
    """Generates scene images from text prompts via DALL-E."""

    async def generate(self, prompt: str, shot_id: int, output_dir: Path) -> Path:
        output_path = output_dir / f"image_{shot_id}.png"

        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
        import httpx

        image_url = response.data[0].url
        async with httpx.AsyncClient() as http:
            img_resp = await http.get(image_url)
            output_path.write_bytes(img_resp.content)
        return output_path

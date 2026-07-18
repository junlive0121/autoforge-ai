"""Shared OpenAI client singleton."""

from openai import AsyncOpenAI

from src.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

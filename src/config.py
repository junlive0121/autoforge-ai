"""Centralized configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = Field(..., min_length=1, description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-5.6-terra",
        description="OpenAI model for planning, writing, and storyboarding",
    )
    output_dir: str = Field(
        default="./output", description="Directory for generated video assets"
    )
    max_parallel_shots: int = Field(
        default=2,
        ge=1,
        le=8,
        description="Maximum number of shots generating media concurrently",
    )
    ffmpeg_binary: str = Field(default="ffmpeg", min_length=1)
    ffprobe_binary: str = Field(default="ffprobe", min_length=1)


settings = Settings()

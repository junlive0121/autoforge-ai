"""Centralized configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = Field(..., min_length=1, description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4o", description="OpenAI model for text generation"
    )
    output_dir: str = Field(
        default="./output", description="Directory for generated video assets"
    )


settings = Settings()

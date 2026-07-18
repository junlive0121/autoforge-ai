"""Shared utilities — JSON parsing, retry, logging helpers."""

import json
import logging
import re
import asyncio
from functools import wraps
from typing import Any, Callable

from openai import APIStatusError, RateLimitError, APITimeoutError

logger = logging.getLogger("autoforge")


def parse_llm_json(raw: str) -> Any:
    """Safely parse JSON from an LLM response, stripping markdown fences."""
    if not raw:
        raise json.JSONDecodeError("Empty LLM response", "", 0)
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed, attempting recovery: %s", e.msg)
        # Try to extract first JSON object or array
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return json.loads(match.group())
        raise


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (RateLimitError, APITimeoutError, APIStatusError),
):
    """Decorator: exponential backoff retry on transient API errors."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        break
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s attempt %d/%d failed (%s), retrying in %.1fs...",
                        func.__qualname__, attempt, max_retries, type(e).__name__, delay,
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator

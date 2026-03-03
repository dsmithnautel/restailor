"""Gemini API client wrapper."""

import asyncio
import json
import re
from typing import Any

from google import genai

from app.config import get_settings

_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    """Get configured Gemini client instance."""
    global _client

    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)

    return _client


def _extract_retry_delay(error_message: str) -> float:
    """Extract retry delay from error message if present."""
    match = re.search(r"retry.*?(\d+\.?\d*)s", str(error_message), re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 60.0


async def generate_json(
    prompt: str,
    max_retries: int = 5,
    temperature: float | None = None,
    model: str = "gemini-2.0-flash",
) -> Any:
    """Generate JSON response from Gemini with retry logic."""
    client = get_gemini_client()
    assert client is not None

    full_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, just the JSON object/array."""

    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            config = {}
            if temperature is not None:
                config["temperature"] = temperature

            response = await client.aio.models.generate_content(
                model=model,
                contents=full_prompt,
                config=config if config else None,
            )
            if not response.text:
                raise ValueError("Gemini returned an empty response.")
            text = response.text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```"):
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1).strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                raise

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(base_delay)
                continue
            raise ValueError(
                f"Failed to parse Gemini response as JSON after {max_retries} attempts: {e}"
            )

        except Exception as e:
            error_str = str(e)

            if (
                "429" in error_str
                or "RESOURCE_EXHAUSTED" in error_str
                or "quota" in error_str.lower()
            ):
                retry_delay = _extract_retry_delay(error_str)
                if attempt < max_retries - 1:
                    print(
                        f"Rate limited. Waiting {retry_delay:.1f}s before retry {attempt + 2}/{max_retries}..."
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise ValueError(
                        f"Rate limit exceeded after {max_retries} attempts. "
                        f"Please wait a few minutes or check your Gemini API quota."
                    )

            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                print(f"Error: {e}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                continue
            raise

    raise RuntimeError("Failed to generate JSON from Gemini.")


async def generate_json_parallel(
    prompts: list[str],
    temperature: float | None = None,
    model: str = "gemini-2.0-flash",
) -> list[Any]:
    """Generate multiple JSON responses in parallel."""
    tasks = [
        generate_json(p, temperature=temperature, model=model)
        for p in prompts
    ]
    return await asyncio.gather(*tasks)


async def generate_text(
    prompt: str,
    max_retries: int = 3,
    temperature: float | None = None,
    model: str = "gemini-2.0-flash",
) -> str:
    """Generate text response from Gemini."""
    client = get_gemini_client()
    assert client is not None

    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            config = {}
            if temperature is not None:
                config["temperature"] = temperature

            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config if config else None,
            )
            if not response.text:
                raise ValueError("Gemini returned an empty response.")
            return response.text

        except Exception as e:
            error_str = str(e)

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                retry_delay = _extract_retry_delay(error_str)
                if attempt < max_retries - 1:
                    print(f"Rate limited. Waiting {retry_delay:.1f}s before retry...")
                    await asyncio.sleep(retry_delay)
                    continue

            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)
                continue
            raise

    raise RuntimeError("Failed to generate text from Gemini.")

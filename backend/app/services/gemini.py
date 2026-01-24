"""Gemini API client wrapper."""

import json
import google.generativeai as genai
from app.config import get_settings

_model = None


def get_gemini_model():
    """Get configured Gemini model instance."""
    global _model
    
    if _model is None:
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel("gemini-1.5-flash")
    
    return _model


async def generate_json(prompt: str, max_retries: int = 3) -> dict | list:
    """
    Generate JSON response from Gemini.
    
    Includes retry logic for parsing failures.
    """
    model = get_gemini_model()
    
    # Add JSON instruction to prompt
    full_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, just the JSON object/array."""
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(full_prompt)
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                continue
            raise ValueError(f"Failed to parse Gemini response as JSON after {max_retries} attempts: {e}")
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            raise


async def generate_text(prompt: str) -> str:
    """Generate text response from Gemini."""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    return response.text

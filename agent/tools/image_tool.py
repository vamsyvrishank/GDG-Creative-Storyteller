"""
Image Generation Tool for StoryForge
Primary: Gemini 2.0 Flash interleaved output (AI Studio key only)
Fast fallback: Pollinations.ai (free, no API key, instant URL)
Optional: Imagen 3 via Vertex AI (set USE_IMAGEN=true)
"""

import os
import base64
import logging
import urllib.parse
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

USE_IMAGEN = os.getenv("USE_IMAGEN", "false").lower() == "true"
USE_GEMINI_IMAGES = os.getenv("USE_GEMINI_IMAGES", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

TONE_STYLE_MAP = {
    "cinematic": "cinematic photography, anamorphic lens, golden hour lighting, movie still",
    "dramatic": "dramatic oil painting, chiaroscuro lighting, dark shadows, high contrast",
    "whimsical": "whimsical digital illustration, bright pastel colors, friendly characters, soft lighting",
    "educational": "clean infographic style, bright colors, clear composition, modern flat design",
    "poetic": "impressionist painting, soft dreamlike colors, ethereal atmosphere, artistic",
}


def generate_image(image_prompt: str, tone: str = "cinematic") -> dict:
    """
    Generate an image for a story scene.

    Args:
        image_prompt: Detailed visual description for the scene
        tone: Story tone (cinematic|dramatic|whimsical|educational|poetic)

    Returns:
        dict with keys: url (str), source (str), base64_data (optional str)
    """
    style_modifier = TONE_STYLE_MAP.get(tone, TONE_STYLE_MAP["cinematic"])
    full_prompt = f"{image_prompt}, {style_modifier}"

    # Gemini interleaved output uses the AI Studio API key directly.
    # Works alongside Vertex AI — both can be configured at the same time.
    # _api_key = os.getenv("GOOGLE_API_KEY", "")
    # if USE_GEMINI_IMAGES and _api_key:
    #     result = _generate_with_gemini(full_prompt, _api_key)
    #     if result:
    #         return result

    # Imagen 3 via Vertex AI (optional, costs money)
    if USE_IMAGEN and GOOGLE_CLOUD_PROJECT:
        result = _generate_with_imagen(full_prompt)
        if result:
            return result

    # Pollinations.ai — free, fast, reliable fallback
    return _generate_with_pollinations(full_prompt)


def _generate_with_gemini(prompt: str, api_key: str) -> Optional[dict]:
    """Gemini 2.0 Flash interleaved output — AI Studio only."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Generate a single high-quality image for this scene: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime_type = part.inline_data.mime_type or "image/png"
                return {
                    "url": f"data:{mime_type};base64,{image_b64}",
                    "source": "gemini-interleaved",
                    "base64_data": image_b64,
                    "mime_type": mime_type,
                }

        logger.warning("Gemini returned no image parts, falling back to Pollinations")
        return None

    except Exception as e:
        logger.warning(f"Gemini image generation failed: {e}")
        return None


def _generate_with_imagen(prompt: str) -> Optional[dict]:
    """Imagen 3 via Vertex AI."""
    try:
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel

        vertexai.init(
            project=GOOGLE_CLOUD_PROJECT,
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )

        if images:
            img_bytes = images[0]._image_bytes
            image_b64 = base64.b64encode(img_bytes).decode("utf-8")
            return {
                "url": f"data:image/png;base64,{image_b64}",
                "source": "imagen-3",
                "base64_data": image_b64,
                "mime_type": "image/png",
            }
        return None

    except Exception as e:
        logger.warning(f"Imagen generation failed: {e}")
        return None


def _generate_with_pollinations(prompt: str) -> dict:
    """Pollinations.ai — fetch server-side and return as base64 for reliable display."""
    import time
    encoded = urllib.parse.quote(prompt)
    seed = int(time.time() * 1000) % 999983
    url = f"{POLLINATIONS_BASE}/{encoded}?width=1024&height=576&nologo=true&seed={seed}"

    # Retry up to 3 times: handles 429 rate limits with backoff
    delays = [0, 8, 16]
    for attempt, delay in enumerate(delays):
        if delay:
            logger.info(f"Pollinations rate limited, retrying in {delay}s (attempt {attempt+1})")
            time.sleep(delay)
        try:
            with httpx.Client(timeout=25.0, follow_redirects=True) as client:
                response = client.get(url)
                if response.status_code == 200 and response.content:
                    mime_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
                    if not mime_type.startswith("image/"):
                        mime_type = "image/jpeg"
                    image_b64 = base64.b64encode(response.content).decode("utf-8")
                    logger.info(f"Pollinations image fetched: {len(response.content)} bytes")
                    return {
                        "url": f"data:{mime_type};base64,{image_b64}",
                        "source": "pollinations",
                        "base64_data": image_b64,
                        "mime_type": mime_type,
                    }
                elif response.status_code == 429:
                    logger.warning(f"Pollinations 429 rate limit (attempt {attempt+1})")
                    continue  # retry with backoff
                else:
                    logger.warning(f"Pollinations returned {response.status_code}")
                    break
        except Exception as e:
            logger.warning(f"Pollinations fetch failed: {e}")
            break

    # URL fallback — browser will attempt to load directly
    logger.warning("All Pollinations attempts failed, using URL fallback")
    return {
        "url": url,
        "source": "pollinations-url",
        "base64_data": None,
        "mime_type": "image/jpeg",
    }

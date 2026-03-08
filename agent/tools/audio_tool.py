"""
Audio Generation Tool for StoryForge
Primary: Google Cloud Text-to-Speech API (Neural2 / Standard voices)
Fallback: Returns None gracefully (frontend silently skips audio)
"""

import os
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

USE_NEURAL2 = os.getenv("USE_NEURAL2_TTS", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")

# Voice selection per tone (Neural2 for premium, Standard as fallback)
TONE_VOICE_MAP = {
    "cinematic": {
        "neural2": "en-US-Neural2-D",   # Deep, authoritative male
        "standard": "en-US-Standard-D",
        "pitch": -1.0,
        "speaking_rate": 0.9,
    },
    "dramatic": {
        "neural2": "en-US-Neural2-J",   # Strong, emotive male
        "standard": "en-US-Standard-J",
        "pitch": -2.0,
        "speaking_rate": 0.85,
    },
    "whimsical": {
        "neural2": "en-US-Neural2-F",   # Bright, friendly female
        "standard": "en-US-Standard-F",
        "pitch": 2.0,
        "speaking_rate": 1.05,
    },
    "educational": {
        "neural2": "en-US-Neural2-C",   # Clear, warm female
        "standard": "en-US-Standard-C",
        "pitch": 0.0,
        "speaking_rate": 0.95,
    },
    "poetic": {
        "neural2": "en-US-Neural2-E",   # Soft, contemplative female
        "standard": "en-US-Standard-E",
        "pitch": 1.0,
        "speaking_rate": 0.88,
    },
}


def generate_audio(narration_text: str, tone: str = "cinematic") -> dict:
    """
    Generate speech audio from narration text using Google Cloud TTS.

    Args:
        narration_text: The scene narration to convert to speech
        tone: Story tone to select appropriate voice

    Returns:
        dict with keys: base64_audio (str), mime_type (str), duration_estimate (float)
    """
    if not narration_text or not narration_text.strip():
        return {"base64_audio": None, "mime_type": "audio/mp3", "duration_estimate": 0}

    # Try Google Cloud TTS
    result = _generate_with_google_tts(narration_text, tone)
    if result:
        return result

    # Fallback: return empty (frontend handles gracefully)
    logger.warning("TTS generation failed, returning empty audio")
    return {
        "base64_audio": None,
        "mime_type": "audio/mp3",
        "duration_estimate": len(narration_text) / 15,  # rough estimate
        "error": "TTS unavailable",
    }


def _generate_with_google_tts(text: str, tone: str) -> Optional[dict]:
    """Generate audio using Google Cloud Text-to-Speech API."""
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()

        voice_config = TONE_VOICE_MAP.get(tone, TONE_VOICE_MAP["cinematic"])

        # Use Neural2 if enabled, otherwise Standard (cheaper)
        voice_name = voice_config["neural2"] if USE_NEURAL2 else voice_config["standard"]

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=voice_config["pitch"],
            speaking_rate=voice_config["speaking_rate"],
            effects_profile_id=["large-home-entertainment-class-device"],
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_b64 = base64.b64encode(response.audio_content).decode("utf-8")

        # Estimate duration: ~150 words per minute at 0.9x = ~135 wpm
        word_count = len(text.split())
        wpm = 135 * voice_config["speaking_rate"]
        duration_estimate = (word_count / wpm) * 60

        return {
            "base64_audio": audio_b64,
            "mime_type": "audio/mp3",
            "duration_estimate": round(duration_estimate, 1),
            "voice_used": voice_name,
        }

    except Exception as e:
        logger.warning(f"Google TTS failed: {e}")
        return None

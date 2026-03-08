"""
StoryForge Agent Pipeline — Google ADK SequentialAgent
GDG Gemini Live Agent Challenge: Creative Storyteller Track

Architecture:
  IntentClassifierAgent → NarrativeArchitectAgent → MediaOrchestratorAgent
"""

import json
import logging
from google.adk.agents import Agent, SequentialAgent

# ADK 0.5.0 uses Agent; alias to LlmAgent for clarity in the rest of the file
LlmAgent = Agent

from agent.tools.image_tool import generate_image
from agent.tools.audio_tool import generate_audio

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1: Intent Classifier
# Turns raw user input into a structured story brief
# ─────────────────────────────────────────────────────────────────────────────
intent_classifier = LlmAgent(
    name="IntentClassifierAgent",
    model="gemini-2.0-flash",
    description="Analyzes user input and classifies it into a structured story intent.",
    instruction="""You are a creative story analyst. The user gives you any topic, question,
concept, or idea. You output ONLY a valid JSON object (no markdown, no explanation) with this
exact structure:

{
  "topic": "<cleaned, concise topic name>",
  "tone": "<one of: cinematic | educational | whimsical | dramatic | poetic>",
  "audience": "<one of: general | children | professional>",
  "story_structure": "<one of: chronological | hero_journey | problem_solution | poetic>",
  "emotional_arc": "<one sentence describing the emotional journey of this story>",
  "scene_count": 5
}

Rules:
- "French Revolution" → tone: dramatic, structure: chronological
- "Explain photosynthesis to kids" → tone: whimsical, audience: children
- "Why do we dream?" → tone: poetic, structure: poetic
- "Our startup reduces food waste" → tone: cinematic, structure: problem_solution
- "Why do stars die?" → tone: poetic, structure: chronological
- Default audience: general. Default tone: cinematic.
- ONLY output valid JSON. No extra text.""",
    output_key="intent",
)

# ─────────────────────────────────────────────────────────────────────────────
# AGENT 2: Narrative Architect
# Turns the story brief into 5 cinematic scenes
# ─────────────────────────────────────────────────────────────────────────────
narrative_architect = LlmAgent(
    name="NarrativeArchitectAgent",
    model="gemini-2.0-flash",
    description="Creates a structured 5-scene narrative from the story intent.",
    instruction="""You are a world-class screenwriter and narrative designer. You receive a JSON
story intent and generate a complete 5-scene story as a JSON object.

Output ONLY valid JSON (no markdown, no explanation):

{
  "title": "<Compelling story title>",
  "scenes": [
    {
      "scene_number": 1,
      "title": "<Scene title>",
      "narration": "<2-3 vivid sentences. Present tense. Optimized for text-to-speech. Avoid jargon. Engaging and emotional.>",
      "image_prompt": "<Detailed visual description for image generation. Include: art style, mood/lighting, colors, composition, specific subjects. NO text in image. Example: 'A majestic golden sunrise over Paris rooftops, oil painting style, warm amber and deep purple tones, wide establishing shot, cinematic composition'>",
      "emotional_beat": "<one of: wonder | tension | revelation | climax | resolution>",
      "duration_seconds": 8
    }
  ]
}

Rules:
- Scenes must follow the emotional arc from the intent (build tension, peak at scene 4, resolve at scene 5)
- Narration: short, punchy sentences. Avoid "Furthermore", "Moreover", "In conclusion".
- Image prompts: be specific about style (oil painting / photorealistic / watercolor / digital art)
- Match tone: whimsical→bright colors, pastel; dramatic→dark shadows, high contrast; cinematic→golden hour, anamorphic lens
- For children: simple language, friendly characters, bright colors in image prompts
- Scene 1: establish the world. Scene 5: emotional resolution.
- ONLY output valid JSON. No extra text.""",
    output_key="narrative",
)

# ─────────────────────────────────────────────────────────────────────────────
# AGENT 3: Media Orchestrator
# Takes narrative and generates images + audio per scene
# Uses Gemini interleaved output for the mandatory judging criterion
# ─────────────────────────────────────────────────────────────────────────────
media_orchestrator = LlmAgent(
    name="MediaOrchestratorAgent",
    model="gemini-2.0-flash",
    description="Orchestrates image and audio generation for each scene using tools.",
    instruction="""You are a media production coordinator. You receive a story narrative JSON and
must generate images and audio for each of the 5 scenes.

For EACH scene, call the tools in this order:
1. Call generate_image with the scene's image_prompt and the story tone
2. Call generate_audio with the scene's narration text and the story tone

After processing all 5 scenes, output a JSON summary:
{
  "status": "complete",
  "scenes_processed": 5,
  "media_generated": true
}

Process scenes in order (1 through 5). Call the tools for each scene before moving to the next.
ONLY output valid JSON after all tools are called.""",
    tools=[generate_image, generate_audio],
    output_key="media",
)

# ─────────────────────────────────────────────────────────────────────────────
# ROOT AGENT: Sequential Pipeline
# ADK convention: exported as root_agent
# ─────────────────────────────────────────────────────────────────────────────
root_agent = SequentialAgent(
    name="StoryForgeAgent",
    description="End-to-end storytelling pipeline: topic → intent → narrative → media",
    sub_agents=[
        intent_classifier,
        narrative_architect,
        media_orchestrator,
    ],
)

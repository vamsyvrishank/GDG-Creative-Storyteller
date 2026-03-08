# How We Built StoryForge in One Hackathon Night

*A behind-the-scenes look at building an AI storytelling agent with Google ADK and Gemini 2.0 Flash*

---

## The Idea

The prompt was simple: "Creative Storyteller." The mandate was clear: multimodal output. The budget: $25 in Google Cloud credits.

We asked ourselves: what if you could type *any* topic — "French Revolution," "Why do stars die?", "Explain photosynthesis to kids" — and get back a cinematic, narrated, illustrated story in under 60 seconds?

That became **StoryForge**.

---

## The Architecture Decision: SequentialAgent

The first decision was how to structure the AI pipeline. We could have written one giant prompt that tries to do everything — classify the topic, write the story, describe the images, and coordinate the media — but that would have been fragile and hard to debug.

Instead, we reached for **Google ADK's SequentialAgent**. The idea: chain three focused `LlmAgent` instances, each with a single clear job:

```
Input → IntentClassifier → NarrativeArchitect → MediaOrchestrator → Output
```

This pattern has a huge advantage during a hackathon: when something breaks, you know exactly which agent to fix. No prompt soup.

### Agent 1: IntentClassifier

The first agent's only job is to understand what the user wants and output structured JSON:

```json
{
  "topic": "French Revolution",
  "tone": "dramatic",
  "audience": "general",
  "story_structure": "chronological",
  "emotional_arc": "From the smoldering grievances of the poor to the violent upheaval that changed history",
  "scene_count": 5
}
```

Low temperature (0.3), short output, deterministic. This feeds directly into Agent 2.

### Agent 2: NarrativeArchitect

This is where the creative magic happens. Given the intent, Gemini writes 5 scenes — each with:
- **Narration**: TTS-optimized, present tense, short punchy sentences
- **Image prompt**: Detailed visual description with art style, lighting, colors
- **Emotional beat**: wonder → tension → revelation → climax → resolution

The key insight: narration has to *sound good aloud*. We spent time on the instructions to get Gemini to avoid "Furthermore" and "In conclusion" — the plague of AI-generated text.

### Agent 3: MediaOrchestrator

This agent calls two tools per scene: `generate_image` and `generate_audio`. The tools are decorated with `@tool` from `google.adk.tools`.

The **mandatory hackathon criterion** was Gemini's interleaved output — getting text and images in a single API response. We implemented this with:

```python
config=types.GenerateContentConfig(
    response_modalities=["TEXT", "IMAGE"],
)
```

Then we iterate the response parts — `part.text` gives narration, `part.inline_data` gives a raw image that we base64-encode and ship directly to the frontend.

---

## The Streaming Architecture

The judging demo needs to look impressive. The worst thing for a demo is a loading spinner for 30 seconds, then a wall of text appearing at once.

We solved this with **Server-Sent Events (SSE)**. FastAPI's `StreamingResponse` with `text/event-stream` content type lets us push events to the browser as each scene completes. The frontend receives events in real-time:

```
event: scene_start   → card appears in UI
event: narration     → text fills in
event: image         → image loads
event: audio         → audio player appears, plays
```

Scenes appear one by one, each ~5-8 seconds apart. For judges watching a 4-minute demo, this is *much* more impressive than a batch response.

---

## Image Generation Strategy

We had to balance quality vs. cost vs. reliability. Here's our priority ladder:

1. **Gemini 2.0 Flash interleaved output** — the judging requirement, inline image generation
2. **Pollinations.ai** — completely free, no API key, works instantly
3. **Imagen 3 via Vertex AI** — highest quality but costs money and has quotas

For the demo, we default to Gemini interleaved + Pollinations fallback. This means zero image generation cost while still satisfying the interleaved output requirement.

The Pollinations URL format is beautiful in its simplicity:
```
https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&nologo=true
```

No auth, no rate limits for reasonable use, reliable enough for a demo.

---

## Audio: Google Cloud TTS

For each scene's narration, we call the Google Cloud Text-to-Speech API. We match the voice to the story tone:

- Cinematic → `en-US-Neural2-D` (deep, authoritative)
- Whimsical → `en-US-Neural2-F` (bright, friendly)
- Dramatic → `en-US-Neural2-J` (intense, lower pitch)
- Poetic → `en-US-Neural2-E` (soft, contemplative)

The response is MP3 audio — we base64-encode it and send it as an SSE event. The frontend decodes it into a Blob URL and plays it automatically for the first scene.

---

## The Frontend: Impressiveness Per Line of Code

The frontend is a single `index.html` file — no React, no build step, no bundler. Vanilla JS + CSS.

Key design choices:
- **Dark background** (`#0a0a0f`) makes images pop dramatically
- **Gold accent** (`#c9a84c`) feels cinematic and premium
- **Playfair Display** for titles (serif, elegant), **DM Sans** for body (clean, modern)
- Scene cards animate in with CSS transitions as SSE events arrive
- Audio autoplay on first scene (graceful fallback if browser blocks it)
- Progress bar so the user knows something is happening during generation

The entire UI is ~400 lines. Judges can review it in minutes.

---

## What We'd Add With More Time

1. **Story caching in Firestore** — detect duplicate topics, serve cached stories instantly
2. **Video export** — stitch images + audio into an MP4 using FFmpeg in Cloud Run
3. **Custom style presets** — let users upload a reference image for visual style matching
4. **Voice cloning** — use a user's voice sample via the TTS API custom voice feature
5. **Story branching** — let users choose different paths at key decision points

---

## The Google Antigravity IDE Experience

Building this with the Google Antigravity IDE was significantly faster than a traditional setup. The AI assistance understood the ADK patterns immediately — knowing the `@tool` decorator convention, the `output_key` field for passing state between agents, and the `InMemorySessionService` for local development.

The most valuable moment: when the IDE caught a subtle issue in how we were parsing SSE events in the frontend. The `buffer` accumulation pattern for streaming responses is easy to get wrong (partial JSON, split event lines) and having that caught early saved an hour of debugging.

---

## Lessons for the Next Hackathon

1. **Design for the demo, not the product.** SSE streaming looks impressive. Batch responses don't.
2. **Free fallbacks are your best friends.** Pollinations.ai cost us $0 and worked reliably.
3. **SequentialAgent beats monolithic prompts.** Debuggable, composable, focused.
4. **Single-file frontend is underrated.** No build step means no build errors at 2am.
5. **The `/health` endpoint is free points.** Judges want proof of Cloud Run deployment.

---

*StoryForge was built in approximately 12 hours for the GDG Gemini Live Agent Challenge 2025.*

*Tech stack: Python 3.11 · FastAPI · Google ADK · Gemini 2.0 Flash · Google Cloud TTS · Pollinations.ai · Firestore · Cloud Run*

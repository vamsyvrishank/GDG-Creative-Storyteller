# StoryForge — AI Storytelling Agent

> **Any topic or question → a 5-scene multimedia story with narration, images, and audio in one seamless flow.**

Built for the **GDG Gemini Live Agent Challenge** · Creative Storyteller Track

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-4285F4?style=flat&logo=google&logoColor=white)
![Google ADK](https://img.shields.io/badge/Google%20ADK-0.5.0-34A853?style=flat&logo=google&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Deployed-4285F4?style=flat&logo=google-cloud&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        StoryForge Pipeline                      │
│                    Google ADK SequentialAgent                   │
└─────────────────────────────────────────────────────────────────┘

  User Input: "French Revolution"
       │
       ▼
┌─────────────────────┐
│ IntentClassifier    │  gemini-2.0-flash
│ Agent               │  ─────────────────────────────────────────
│                     │  Input:  raw topic / question / idea
│                     │  Output: { tone, audience, structure,
│                     │           emotional_arc, scene_count }
└────────┬────────────┘
         │ intent JSON
         ▼
┌─────────────────────┐
│ NarrativeArchitect  │  gemini-2.0-flash
│ Agent               │  ─────────────────────────────────────────
│                     │  Input:  intent JSON
│                     │  Output: { title, scenes[5] }
│                     │          each scene: title, narration,
│                     │          image_prompt, emotional_beat
└────────┬────────────┘
         │ narrative JSON
         ▼
┌─────────────────────┐
│ MediaOrchestrator   │  gemini-2.0-flash + tools
│ Agent               │  ─────────────────────────────────────────
│                     │  For each scene:
│                     │  ├── generate_image(prompt, tone)
│                     │  │     -> Gemini interleaved output (primary)
│                     │  │     -> Pollinations.ai (fallback)
│                     │  │     -> Imagen 3 (optional)
│                     │  └── generate_audio(narration, tone)
│                     │        -> Google Cloud TTS Neural2
└────────┬────────────┘
         │ SSE stream
         ▼
┌─────────────────────┐
│ FastAPI SSE          │  POST /story/stream
│ Endpoint             │  ─────────────────────────────────────────
│                     │  Events: intent -> scene_start ->
│                     │          narration -> image -> audio ->
│                     │          complete
└────────┬────────────┘
         │
         ├──> Firestore (story persistence + share links)
         │
         ▼
┌─────────────────────┐
│ Frontend            │  Single HTML file
│ Story Player        │  ─────────────────────────────────────────
│                     │  * Cinematic dark UI (dark + gold)
│                     │  * Scenes stream in one by one
│                     │  * Image + narration + audio per scene
│                     │  * 6 lens buttons (tone selector)
│                     │  * Share link via Firestore
└─────────────────────┘
```

## Key Technical Features

| Feature | Implementation |
|---|---|
| **Gemini Interleaved Output** | `response_modalities=["TEXT", "IMAGE"]` in one API call |
| **ADK SequentialAgent** | 3 LlmAgents chained: Classify → Narrate → Orchestrate |
| **SSE Streaming** | FastAPI `StreamingResponse` — scenes appear as they generate |
| **Image Generation** | Gemini 2.0 Flash interleaved → Pollinations.ai fallback (free) |
| **Audio Generation** | Google Cloud TTS Neural2, tone-matched voice per story |
| **Storage** | Firestore — shareable `/story/{id}` links |
| **Deployment** | Cloud Run (min=0, max=2 instances, 1Gi RAM) |

---

## One-Command Local Setup

```bash
# 1. Clone and enter
git clone <repo-url> && cd GDG-Creative-Storyteller

# 2. Create virtual env
python -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set GOOGLE_CLOUD_PROJECT to your GCP project ID

# 5. Authenticate with Google Cloud
gcloud auth application-default login

# 6. Run the app
python main.py

# Open http://localhost:8080
```

**Test with ADK dev UI:**
```bash
adk web   # Opens ADK agent inspector at http://localhost:8000
```

---

## Demo Inputs

| Input | Expected Tone | Structure |
|---|---|---|
| "French Revolution" | Dramatic | Chronological |
| "Explain photosynthesis to 8 year olds" | Whimsical | Problem-Solution |
| "Why do stars die?" | Poetic | Poetic |
| "The rise of social media" | Cinematic | Hero's Journey |

---

## Google Cloud Deployment

### Prerequisites
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  texttospeech.googleapis.com firestore.googleapis.com aiplatform.googleapis.com
```

### Automated deploy (Cloud Build)
```bash
gcloud builds submit --config cloudbuild.yaml
```

### Manual deploy
```bash
docker build -t gcr.io/$PROJECT_ID/storyforge .
docker push gcr.io/$PROJECT_ID/storyforge

gcloud run deploy storyforge \
  --image gcr.io/$PROJECT_ID/storyforge \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID
```

### Verify deployment
```bash
curl https://storyforge-xxxx-uc.a.run.app/health
```

---

## API Reference

### `POST /story/stream`
SSE endpoint — streams a complete 5-scene story as it generates.

**Request:**
```json
{ "input": "French Revolution", "lens": "auto" }
```

**SSE Event sequence:**
```
event: status        → "Analyzing your topic..."
event: intent        → { tone, audience, story_structure, emotional_arc }
event: narrative_ready → { title, scene_count }
event: scene_start   → { scene_number, title, emotional_beat }
event: narration     → { text, scene_number }
event: image         → { url, source, scene_number }
event: audio         → { base64_audio, mime_type, scene_number }
... (repeats for all 5 scenes)
event: complete      → { story_id, share_url, title }
```

### `GET /story/{story_id}`
Returns saved story JSON from Firestore.

### `GET /health`
Returns deployment proof + agent pipeline details for judges.

---

## File Structure

```
storyforge/
├── main.py                           # FastAPI app + SSE endpoint + pipeline
├── agent/
│   ├── __init__.py                   # exports root_agent (ADK convention)
│   ├── agent.py                      # SequentialAgent (3 LlmAgents)
│   └── tools/
│       ├── image_tool.py             # Gemini interleaved -> Pollinations
│       └── audio_tool.py             # Google Cloud TTS Neural2
│   └── skills/
│       ├── narrative_skill/SKILL.md  # Story structure patterns
│       └── tone_skill/SKILL.md       # Tone & voice reference guide
├── frontend/
│   └── index.html                    # Single-file cinematic story player
├── Dockerfile                        # python:3.11-slim, port 8080
├── cloudbuild.yaml                   # Cloud Build -> Cloud Run auto-deploy
├── requirements.txt
└── .env.example
```

---

## Cost Optimization (staying within $25 credit)

- **Gemini 2.0 Flash** — 10x cheaper than 1.5 Pro
- **Pollinations.ai** — completely free image fallback (no API key needed)
- **Standard TTS** — set `USE_NEURAL2_TTS=false` to halve TTS costs
- **Cloud Run min=0** — no idle compute costs
- **Firestore caching** — same topic never regenerated twice

---

## Team Members List:

- Vamsy Vrishank
- Mridhul Subash
- Manan Pandey

## Built With

- [Google ADK](https://google.github.io/adk-docs/) — Agent Development Kit
- [Gemini 2.0 Flash](https://deepmind.google/technologies/gemini/) — LLM + interleaved image generation
- [Google Cloud TTS](https://cloud.google.com/text-to-speech) — Neural2 voice synthesis
- [Pollinations.ai](https://pollinations.ai) — Free image generation fallback
- [FastAPI](https://fastapi.tiangolo.com) — Async Python web framework
- [Cloud Run](https://cloud.google.com/run) — Serverless container deployment
- [Firestore](https://cloud.google.com/firestore) — Story persistence + sharing

---

*Built for the GDG Gemini Live Agent Challenge 2025 — Creative Storyteller Track*

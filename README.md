# Raksha MVP

Raksha is a simple AI voice assistant for basic healthcare advice (non-diagnostic), built with:

- Backend: Google ADK (Python) + FastAPI + uv
- Frontend: React + Bun

## Folder Layout

- `back end` - FastAPI websocket server and ADK live integration
- `front end` - React UI with microphone/audio playback

## Quick Start Scripts

From project root:

```bash
./sb   # start backend
./sf   # start frontend
```

## 1) Backend Setup

```bash
cd "back end"
uv sync
```

Update API key in `back end/.env`:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
```

Run backend:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2) Frontend Setup

```bash
cd "front end"
bun install
bun run dev
```

Open the local Vite URL (usually `http://localhost:5173`).

## Safety Behavior

Raksha is explicitly instructed to:

- provide general health and wellness guidance only
- avoid diagnosis statements
- advise emergency care for urgent symptom patterns

## Notes on Gemini Live Model

- Pinned default model: `gemini-2.5-flash-native-audio-preview-12-2025`
- Deprecated/blocked in config: `gemini-2.0-flash-live-001` (shutdown on 2025-12-09)
- Verify latest model updates in Google docs before changing defaults.

## References

- Gemini Live API docs: https://ai.google.dev/gemini-api/docs/live
- Gemini changelog: https://ai.google.dev/gemini-api/docs/changelog
- ADK FastAPI streaming guide: https://google.github.io/adk-docs/streaming/fastapi/
- ADK custom websocket streaming: https://google.github.io/adk-docs/streaming/custom-streaming-ws/

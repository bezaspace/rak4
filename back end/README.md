# Raksha Backend

FastAPI + Google ADK backend for live Gemini voice interaction.

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Notes

- Set `GEMINI_API_KEY` in `.env`.
- Default model is pinned to `gemini-2.5-flash-native-audio-preview-12-2025`.
- Deprecated model `gemini-2.0-flash-live-001` is blocked at startup.

## WebSocket API

Endpoint: `ws://localhost:8000/ws/live`

Client -> Server text frames:

- `{"type":"text_input","text":"..."}`
- `{"type":"end_turn"}`
- `{"type":"stop_session"}`

Client -> Server binary frames:

- raw PCM16 mono audio bytes at 16 kHz

Server -> Client text frames:

- `{"type":"session_ready","sessionId":"..."}`
- `{"type":"partial_transcript","text":"..."}`
- `{"type":"assistant_text","text":"..."}`
- `{"type":"warning","message":"..."}`

Server -> Client binary frames:

- assistant audio chunks as raw PCM16 mono bytes at 16 kHz

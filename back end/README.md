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
- Live websocket tracing logs are enabled in terminal with session-scoped IDs.
- Use `LOG_LEVEL=debug` (or `info`) in `.env` to control verbosity.

## WebSocket API

Endpoint: `ws://localhost:8000/ws/live`

Client -> Server text frames:

- `{"type":"text_input","text":"..."}`
- `{"type":"ptt_start"}` (strict turn start: backend calls `send_activity_start`)
- `{"type":"ptt_end"}` (strict turn end: backend calls `send_activity_end`)
- `{"type":"end_turn"}` (legacy alias for strict turn end)
- `{"type":"stop_session"}`

Client -> Server binary frames:

- raw PCM16 mono audio bytes at 16 kHz (frontend sends ~50ms packetized chunks)

PTT behavior:

- Response generation is expected after `ptt_end`/`end_turn`.
- Automatic activity detection is disabled for deterministic turn boundaries.

Server -> Client text frames:

- `{"type":"session_ready","sessionId":"..."}`
- `{"type":"partial_transcript","text":"..."}`
- `{"type":"assistant_text","text":"..."}`
- `{"type":"warning","message":"..."}`
- `{"type":"fallback_started","reason":"live_tool_unsupported","turnId":"..."}`
- `{"type":"fallback_completed","turnId":"...","result":"ok|failed"}`
- `{"type":"session_recovering","mode":"reconnect_live"}`
- `{"type":"doctor_recommendations","requestId":"...","symptomsSummary":"...","doctors":[...]}`  
  Includes 2-3 recommended doctors and their slot availability.
- `{"type":"booking_update","status":"confirmed|failed|unavailable|needs_confirmation","message":"...","booking":{...}}`

Server -> Client binary frames:

- assistant audio chunks as raw PCM16 mono bytes (usually 24 kHz from Gemini Live)

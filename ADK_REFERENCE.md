# ADK Components Reference Guide

## Package Imports

### `google.adk`

| Component | Import Path | File Used |
|-----------|-------------|-----------|
| `Agent` | `google.adk.agents` | `/home/harsha/rak4/back end/app/agent.py:5` |
| `LiveRequestQueue` | `google.adk.agents.live_request_queue` | `/home/harsha/rak4/back end/app/live_bridge.py:12` |
| `RunConfig` | `google.adk.agents.run_config` | `/home/harsha/rak4/back end/app/live_bridge.py:13` |
| `Runner` | `google.adk.runners` | `/home/harsha/rak4/back end/app/live_bridge.py:14` |
| `InMemorySessionService` | `google.adk.sessions` | `/home/harsha/rak4/back end/app/live_bridge.py:15` |

### `google.genai`

| Component | Import Path | File Used |
|-----------|-------------|-----------|
| `errors` | `google.genai` | `/home/harsha/rak4/back end/app/live_bridge.py:16` |
| `types` | `google.genai` | `/home/harsha/rak4/back end/app/live_bridge.py:17` |

---

## Classes

### Agent Classes

| Class | Module | Instantiation Location |
|-------|--------|----------------------|
| `Agent` | `google.adk.agents.Agent` | `/home/harsha/rak4/back end/app/agent.py:25` |

### Runner Classes

| Class | Module | Instantiation Location |
|-------|--------|----------------------|
| `Runner` | `google.adk.runners.Runner` | `/home/harsha/rak4/back end/app/live_bridge.py:48-52` |

### Session Classes

| Class | Module | Instantiation Location |
|-------|--------|----------------------|
| `InMemorySessionService` | `google.adk.sessions.InMemorySessionService` | `/home/harsha/rak4/back end/app/live_bridge.py:37` |

### Live Streaming Classes

| Class | Module | Instantiation Location |
|-------|--------|----------------------|
| `LiveRequestQueue` | `google.adk.agents.live_request_queue.LiveRequestQueue` | `/home/harsha/rak4/back end/app/live_bridge.py:57` |
| `RunConfig` | `google.adk.agents.run_config.RunConfig` | `/home/harsha/rak4/back end/app/live_bridge.py:224-239` |

### Custom Dataclasses

| Class | File | Purpose |
|-------|------|---------|
| `LiveSessionContext` | `/home/harsha/rak4/back end/app/live_bridge.py:25-30` | Container for runner, session, queue |
| `LiveBridge` | `/home/harsha/rak4/back end/app/live_bridge.py:32-239` | WebSocket bridge class |

---

## Methods

### Agent Methods

| Method | Class | Called In |
|--------|-------|-----------|
| `__init__` | `Agent` | `/home/harsha/rak4/back end/app/agent.py:25-31` |

### Runner Methods

| Method | Class | Called In |
|--------|-------|-----------|
| `__init__` | `Runner` | `/home/harsha/rak4/back end/app/live_bridge.py:48-52` |
| `run_live` | `Runner` | `/home/harsha/rak4/back end/app/live_bridge.py:68-72` |
| `session_service.create_session` | `Runner` | `/home/harsha/rak4/back end/app/live_bridge.py:53-56` |

### SessionService Methods

| Method | Class | Called In |
|--------|-------|-----------|
| `__init__` | `InMemorySessionService` | `/home/harsha/rak4/back end/app/live_bridge.py:37` |
| `create_session` | `InMemorySessionService` | `/home/harsha/rak4/back end/app/live_bridge.py:53-56` |

### LiveRequestQueue Methods

| Method | Class | Called In |
|--------|-------|-----------|
| `__init__` | `LiveRequestQueue` | `/home/harsha/rak4/back end/app/live_bridge.py:57` |
| `send_realtime` | `LiveRequestQueue` | `/home/harsha/rak4/back end/app/live_bridge.py:109` |
| `send_content` | `LiveRequestQueue` | `/home/harsha/rak4/back end/app/live_bridge.py:125` |
| `close` | `LiveRequestQueue` | `/home/harsha/rak4/back end/app/live_bridge.py:130` |
| `send_activity_start` | `LiveRequestQueue` | Referenced in `_route_control_event` |
| `send_activity_end` | `LiveRequestQueue` | Referenced in `_route_control_event` |

### LiveBridge Methods

| Method | Location |
|--------|----------|
| `__init__` | `/home/harsha/rak4/back end/app/live_bridge.py:33-39` |
| `build_context` | `/home/harsha/rak4/back end/app/live_bridge.py:41-58` |
| `run_websocket` | `/home/harsha/rak4/back end/app/live_bridge.py:60-101` |
| `_recv_events_from_client` | `/home/harsha/rak4/back end/app/live_bridge.py:103-131` |
| `_send_events_to_client` | `/home/harsha/rak4/back end/app/live_bridge.py:133-173` |
| `_get_function_responses` | `/home/harsha/rak4/back end/app/live_bridge.py:175-180` |
| `_route_control_event` | `/home/harsha/rak4/back end/app/live_bridge.py:182-191` |
| `_extract_ui_payload_from_function_response` | `/home/harsha/rak4/back end/app/live_bridge.py:193-209` |
| `_extract_sample_rate` | `/home/harsha/rak4/back end/app/live_bridge.py:211-221` |
| `_build_run_config` | `/home/harsha/rak4/back end/app/live_bridge.py:223-239` |

### Agent Creation Functions

| Function | Location |
|----------|----------|
| `create_agent` | `/home/harsha/rak4/back end/app/agent.py:24-31` |
| `build_instruction` | `/home/harsha/rak4/back end/app/agent.py:8-21` |

---

## Google GenAI Types

### Content Types

| Type | Module | Usage Location |
|------|--------|---------------|
| `types.Blob` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:108` |
| `types.Content` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:124` |
| `types.Part` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:124` |

### Configuration Types

| Type | Module | Usage Location |
|------|--------|---------------|
| `types.Modality` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:226` |
| `types.AudioTranscriptionConfig` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:227-228` |
| `types.RealtimeInputConfig` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:229` |
| `types.ActivityHandling` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:230` |
| `types.AutomaticActivityDetection` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:231` |
| `types.StartSensitivity` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:233` |
| `types.EndSensitivity` | `google.genai.types` | `/home/harsha/rak4/back end/app/live_bridge.py:234` |

### Error Types

| Type | Module | Usage Location |
|------|--------|---------------|
| `genai_errors.APIError` | `google.genai.errors` | `/home/harsha/rak4/back end/app/live_bridge.py:88` |

---

## Agent Configuration Parameters

### Agent Constructor Parameters

| Parameter | Type | Location |
|-----------|------|----------|
| `name` | `str` | `/home/harsha/rak4/back end/app/agent.py:26` |
| `model` | `str` | `/home/harsha/rak4/back end/app/agent.py:27` |
| `instruction` | `str` | `/home/harsha/rak4/back end/app/agent.py:28` |
| `description` | `str` | `/home/harsha/rak4/back end/app/agent.py:29` |
| `tools` | `list[Any]` | `/home/harsha/rak4/back end/app/agent.py:30` |

### Runner Constructor Parameters

| Parameter | Type | Location |
|-----------|------|----------|
| `app_name` | `str` | `/home/harsha/rak4/back end/app/live_bridge.py:49` |
| `agent` | `Agent` | `/home/harsha/rak4/back end/app/live_bridge.py:50` |
| `session_service` | `InMemorySessionService` | `/home/harsha/rak4/back end/app/live_bridge.py:51` |

### RunConfig Constructor Parameters

| Parameter | Type | Location |
|-----------|------|----------|
| `response_modalities` | `list[types.Modality]` | `/home/harsha/rak4/back end/app/live_bridge.py:226` |
| `output_audio_transcription` | `types.AudioTranscriptionConfig` | `/home/harsha/rak4/back end/app/live_bridge.py:227` |
| `input_audio_transcription` | `types.AudioTranscriptionConfig` | `/home/harsha/rak4/back end/app/live_bridge.py:228` |
| `realtime_input_config` | `types.RealtimeInputConfig` | `/home/harsha/rak4/back end/app/live_bridge.py:229` |

### AutomaticActivityDetection Parameters

| Parameter | Type | Location |
|-----------|------|----------|
| `disabled` | `bool` | `/home/harsha/rak4/back end/app/live_bridge.py:232` |
| `start_of_speech_sensitivity` | `types.StartSensitivity` | `/home/harsha/rak4/back end/app/live_bridge.py:233` |
| `end_of_speech_sensitivity` | `types.EndSensitivity` | `/home/harsha/rak4/back end/app/live_bridge.py:234` |
| `prefix_padding_ms` | `int` | `/home/harsha/rak4/back end/app/live_bridge.py:235` |
| `silence_duration_ms` | `int` | `/home/harsha/rak4/back end/app/live_bridge.py:236` |

---

## Function Tools

### Tool Functions

| Function | File | Line |
|----------|------|------|
| `get_doctor_catalog` | `/home/harsha/rak4/back end/app/doctor_tools.py` | 13-23 |
| `publish_recommendations` | `/home/harsha/rak4/back end/app/doctor_tools.py` | 25-70 |
| `book_doctor_slot` | `/home/harsha/rak4/back end/app/doctor_tools.py` | 72-141 |

### Tool Builder Function

| Function | File | Line |
|----------|------|------|
| `build_doctor_tools` | `/home/harsha/rak4/back end/app/doctor_tools.py` | 10-143 |

---

## Event Attributes Accessed

### Event Processing (in `_send_events_to_client`)

| Attribute | Line |
|-----------|------|
| `event.interrupted` | `/home/harsha/rak4/back end/app/live_bridge.py:136` |
| `event.get_function_responses` | `/home/harsha/rak4/back end/app/live_bridge.py:177` |
| `event.output_transcription` | `/home/harsha/rak4/back end/app/live_bridge.py:145` |
| `event.output_transcription.text` | `/home/harsha/rak4/back end/app/live_bridge.py:146` |
| `event.input_transcription` | `/home/harsha/rak4/back end/app/live_bridge.py:149` |
| `event.input_transcription.text` | `/home/harsha/rak4/back end/app/live_bridge.py:150` |
| `event.content` | `/home/harsha/rak4/back end/app/live_bridge.py:153` |
| `event.content.parts` | `/home/harsha/rak4/back end/app/live_bridge.py:157` |
| `part.text` | `/home/harsha/rak4/back end/app/live_bridge.py:158` |
| `part.inline_data` | `/home/harsha/rak4/back end/app/live_bridge.py:160` |
| `part.inline_data.data` | `/home/harsha/rak4/back end/app/live_bridge.py:160` |
| `part.inline_data.mime_type` | `/home/harsha/rak4/back end/app/live_bridge.py:162` |

### Function Response Processing

| Attribute | Line |
|-----------|------|
| `function_response.response` | `/home/harsha/rak4/back end/app/live_bridge.py:195` |

---

## Async Patterns

### Async Methods

| Method | File | Line |
|--------|------|------|
| `build_context` | `/home/harsha/rak4/back end/app/live_bridge.py` | 41 |
| `run_websocket` | `/home/harsha/rak4/back end/app/live_bridge.py` | 60 |
| `_recv_events_from_client` | `/home/harsha/rak4/back end/app/live_bridge.py` | 103 |
| `_send_events_to_client` | `/home/harsha/rak4/back end/app/live_bridge.py` | 133 |

### Async Iterators

| Iterator | File | Line |
|----------|------|------|
| `live_events` (from `run_live`) | `/home/harsha/rak4/back end/app/live_bridge.py` | 68 |

### Asyncio Usage

| Function | File | Line |
|----------|------|------|
| `asyncio.create_task` | `/home/harsha/rak4/back end/app/live_bridge.py` | 74-75 |
| `asyncio.wait` | `/home/harsha/rak4/back end/app/live_bridge.py` | 77 |

---

## WebSocket Integration

### WebSocket Methods

| Method | File | Line |
|--------|------|------|
| `websocket.accept` | `/home/harsha/rak4/back end/app/live_bridge.py` | 61 |
| `websocket.send_json` | `/home/harsha/rak4/back end/app/live_bridge.py` | 64, 137, 141, 147, 151, 159, 166 |
| `websocket.receive` | `/home/harsha/rak4/back end/app/live_bridge.py` | 106 |
| `websocket.send_bytes` | `/home/harsha/rak4/back end/app/live_bridge.py` | 173 |

---

## Environment Variables

| Variable | Set In | Line |
|----------|--------|------|
| `GOOGLE_API_KEY` | `/home/harsha/rak4/back end/app/live_bridge.py` | 42 |
| `GOOGLE_GENAI_USE_VERTEXAI` | `/home/harsha/rak4/back end/app/live_bridge.py` | 43 |

---

## Files Using ADK

| File | ADK Components |
|------|---------------|
| `/home/harsha/rak4/back end/app/agent.py` | `google.adk.agents.Agent` |
| `/home/harsha/rak4/back end/app/live_bridge.py` | `LiveRequestQueue`, `RunConfig`, `Runner`, `InMemorySessionService`, `google.genai.types`, `google.genai.errors` |
| `/home/harsha/rak4/back end/app/doctor_tools.py` | Tools passed to Agent |

---

## Dependencies

From `/home/harsha/rak4/back end/pyproject.toml`:

```toml
dependencies = [
  "fastapi>=0.116.0",
  "uvicorn[standard]>=0.35.0",
  "google-adk>=1.8.0",
  "google-genai>=1.33.0",
  "pydantic-settings>=2.10.0",
  "python-dotenv>=1.1.1",
]
```

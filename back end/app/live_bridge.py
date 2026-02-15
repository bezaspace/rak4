from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator

from fastapi import WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import contains_urgent_risk_hint, create_agent


@dataclass
class LiveSessionContext:
    runner: Runner
    session: Any
    live_request_queue: LiveRequestQueue


class LiveBridge:
    def __init__(self, app_name: str, model: str, gemini_api_key: str) -> None:
        self._app_name = app_name
        self._model = model
        self._gemini_api_key = gemini_api_key
        self._session_service = InMemorySessionService()

    async def build_context(self, user_id: str) -> LiveSessionContext:
        os.environ["GOOGLE_API_KEY"] = self._gemini_api_key
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

        agent = create_agent(self._model)
        runner = Runner(
            app_name=self._app_name,
            agent=agent,
            session_service=self._session_service,
        )
        session = await runner.session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
        )
        queue = LiveRequestQueue()
        return LiveSessionContext(runner=runner, session=session, live_request_queue=queue)

    async def run_websocket(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()

        context = await self.build_context(user_id=user_id)
        await websocket.send_json({"type": "session_ready", "sessionId": context.session.id})

        run_config = RunConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                activityHandling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                automaticActivityDetection=types.AutomaticActivityDetection(
                    startOfSpeechSensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    endOfSpeechSensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefixPaddingMs=80,
                    silenceDurationMs=400,
                ),
            ),
        )

        live_events = context.runner.run_live(
            session=context.session,
            live_request_queue=context.live_request_queue,
            run_config=run_config,
        )

        send_task = asyncio.create_task(self._send_events_to_client(websocket, live_events))
        recv_task = asyncio.create_task(self._recv_events_from_client(websocket, context.live_request_queue))

        done, pending = await asyncio.wait({send_task, recv_task}, return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()

        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc

    async def _recv_events_from_client(self, websocket: WebSocket, queue: LiveRequestQueue) -> None:
        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"] is not None:
                    audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=message["bytes"])
                    queue.send_realtime(audio_blob)
                    continue

                text_payload = message.get("text")
                if not text_payload:
                    continue

                data = json.loads(text_payload)
                event_type = data.get("type")

                if event_type == "text_input":
                    text = str(data.get("text", "")).strip()
                    if not text:
                        continue

                    if contains_urgent_risk_hint(text):
                        await websocket.send_json(
                            {
                                "type": "warning",
                                "message": "This sounds urgent. Please seek immediate emergency care or call local emergency services now.",
                            }
                        )

                    content = types.Content(role="user", parts=[types.Part(text=text)])
                    queue.send_content(content)
                elif event_type == "end_turn":
                    queue.send_activity_end()
                elif event_type == "stop_session":
                    queue.close()
                    break
        except WebSocketDisconnect:
            queue.close()
            raise

    async def _send_events_to_client(self, websocket: WebSocket, live_events: AsyncIterator[Any]) -> None:
        announced_sample_rate: int | None = None
        async for event in live_events:
            if getattr(event, "interrupted", None):
                await websocket.send_json({"type": "assistant_interrupted"})

            # Forward output transcription when available.
            output_t = getattr(event, "output_transcription", None)
            if output_t and getattr(output_t, "text", None):
                await websocket.send_json({"type": "assistant_text", "text": output_t.text})

            input_t = getattr(event, "input_transcription", None)
            if input_t and getattr(input_t, "text", None):
                await websocket.send_json({"type": "partial_transcript", "text": input_t.text})

            content = getattr(event, "content", None)
            if not content:
                continue

            for part in getattr(content, "parts", []) or []:
                if getattr(part, "text", None):
                    await websocket.send_json({"type": "assistant_text", "text": part.text})
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    sample_rate = self._extract_sample_rate(getattr(inline_data, "mime_type", None))
                    if sample_rate and sample_rate != announced_sample_rate:
                        announced_sample_rate = sample_rate
                        await websocket.send_json(
                            {"type": "assistant_audio_format", "sampleRate": sample_rate}
                        )
                    payload = inline_data.data
                    if isinstance(payload, str):
                        payload_bytes = base64.b64decode(payload)
                    else:
                        payload_bytes = payload
                    await websocket.send_bytes(payload_bytes)

    @staticmethod
    def _extract_sample_rate(mime_type: str | None) -> int | None:
        if not mime_type:
            return None
        for token in mime_type.split(";"):
            token = token.strip().lower()
            if token.startswith("rate="):
                value = token.split("=", 1)[1].strip()
                if value.isdigit():
                    return int(value)
        return None

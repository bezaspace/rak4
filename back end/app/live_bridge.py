from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

from fastapi import WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import errors as genai_errors
from google.genai import types

from app.agent import create_agent
from app.booking_state import SessionBookingState
from app.doctor_repository import DoctorRepository
from app.doctor_tools import build_doctor_tools
from app.patient_profile_service import PatientProfileService
from app.patient_profile_service import ProfileContextResult
from app.patient_tools import build_patient_tools
from app.schedule_service import SCHEDULE_TIMEZONE_STATE_KEY
from app.schedule_service import SCHEDULE_USER_ID_STATE_KEY
from app.schedule_service import ScheduleService
from app.schedule_tools import build_schedule_tools

logger = logging.getLogger("raksha.live")


@dataclass
class LiveSessionContext:
    runner: Runner
    session: Any
    live_request_queue: LiveRequestQueue
    profile_status_event: dict[str, Any]


@dataclass
class SessionMetrics:
    started_at: float
    incoming_audio_chunks: int = 0
    incoming_audio_bytes: int = 0
    outgoing_audio_chunks: int = 0
    outgoing_audio_bytes: int = 0
    incoming_text_events: int = 0
    outgoing_text_events: int = 0
    parse_errors: int = 0


@dataclass
class TurnState:
    active: bool = False
    turn_id: int = 0
    current_turn_audio_chunks: int = 0
    current_turn_started_at: float | None = None
    awaiting_response_turn_id: int | None = None
    current_turn_transcript: str = ""
    last_closed_turn_transcript: str = ""
    last_input_transcript: str = ""
    fallback_attempted_turn_id: int | None = None


class LiveBridge:
    def __init__(
        self,
        app_name: str,
        model: str,
        gemini_api_key: str,
        patient_profile_service: PatientProfileService | None = None,
        schedule_service: ScheduleService | None = None,
    ) -> None:
        self._app_name = app_name
        self._model = model
        self._gemini_api_key = gemini_api_key
        self._patient_profile_service = patient_profile_service
        self._schedule_service = schedule_service
        self._session_service = InMemorySessionService()
        data_path = Path(__file__).resolve().parent / "data" / "mock_doctors.json"
        self._doctor_repository = DoctorRepository.from_json_file(data_path)

    async def build_context(self, user_id: str, timezone_name: str | None = None) -> LiveSessionContext:
        os.environ["GOOGLE_API_KEY"] = self._gemini_api_key
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

        profile_context = self._load_profile_context(user_id)
        booking_state = SessionBookingState(self._doctor_repository.list_doctors())
        state = {
            **profile_context.state,
            SCHEDULE_USER_ID_STATE_KEY: user_id,
        }
        if timezone_name and timezone_name.strip():
            state[SCHEDULE_TIMEZONE_STATE_KEY] = timezone_name.strip()
        tools = (
            build_doctor_tools(self._doctor_repository, booking_state)
            + build_patient_tools()
            + build_schedule_tools(self._schedule_service)
        )
        agent = create_agent(
            self._model,
            tools=tools,
            profile_summary=profile_context.profile_summary,
        )
        runner = Runner(
            app_name=self._app_name,
            agent=agent,
            session_service=self._session_service,
        )
        session = await runner.session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
            state=state,
        )
        queue = LiveRequestQueue()
        return LiveSessionContext(
            runner=runner,
            session=session,
            live_request_queue=queue,
            profile_status_event={
                "type": "profile_status",
                "loaded": profile_context.loaded,
                "source": profile_context.source,
                "message": profile_context.message,
            },
        )

    async def run_websocket(self, websocket: WebSocket, user_id: str, timezone_name: str | None = None) -> None:
        trace_id = uuid.uuid4().hex[:8]
        metrics = SessionMetrics(started_at=perf_counter())
        turn_state = TurnState()
        logger.info("[%s] websocket_connect user_id=%s", trace_id, user_id)

        await websocket.accept()
        logger.info("[%s] websocket_accepted", trace_id)

        try:
            while True:
                context = await self.build_context(user_id=user_id, timezone_name=timezone_name)
                logger.info(
                    "[%s] live_context_ready session_id=%s model=%s",
                    trace_id,
                    context.session.id,
                    self._model,
                )

                await websocket.send_json({"type": "session_ready", "sessionId": context.session.id})
                metrics.outgoing_text_events += 1
                logger.info("[%s] tx_event type=session_ready session_id=%s", trace_id, context.session.id)
                await websocket.send_json(context.profile_status_event)
                metrics.outgoing_text_events += 1
                logger.info(
                    "[%s] tx_event type=profile_status loaded=%s source=%s",
                    trace_id,
                    context.profile_status_event.get("loaded"),
                    context.profile_status_event.get("source"),
                )

                run_config = self._build_run_config()
                logger.info("[%s] ptt_mode mode=strict aad_disabled=true", trace_id)

                live_events = context.runner.run_live(
                    session=context.session,
                    live_request_queue=context.live_request_queue,
                    run_config=run_config,
                )

                send_task = asyncio.create_task(
                    self._send_events_to_client(
                        websocket,
                        live_events,
                        trace_id=trace_id,
                        metrics=metrics,
                        turn_state=turn_state,
                    )
                )
                recv_task = asyncio.create_task(
                    self._recv_events_from_client(
                        websocket,
                        context.live_request_queue,
                        trace_id=trace_id,
                        metrics=metrics,
                        turn_state=turn_state,
                    )
                )

                done, pending = await asyncio.wait(
                    {send_task, recv_task},
                    return_when=asyncio.FIRST_EXCEPTION,
                )

                for task in pending:
                    task.cancel()

                should_end_websocket = False
                recoverable_api_error: genai_errors.APIError | None = None

                for task in done:
                    exc = task.exception()
                    if not exc:
                        should_end_websocket = True
                        continue
                    if isinstance(exc, WebSocketDisconnect):
                        logger.info("[%s] websocket_disconnected", trace_id)
                        should_end_websocket = True
                        continue
                    if isinstance(exc, genai_errors.APIError) and getattr(exc, "code", None) in {1007, 1008}:
                        recoverable_api_error = exc
                        continue
                    logger.exception("[%s] websocket_task_failed", trace_id, exc_info=exc)
                    raise exc

                if recoverable_api_error:
                    recovered = await self._recover_from_live_api_error(
                        websocket=websocket,
                        context=context,
                        user_id=user_id,
                        trace_id=trace_id,
                        metrics=metrics,
                        turn_state=turn_state,
                        error=recoverable_api_error,
                    )
                    context.live_request_queue.close()
                    if not recovered:
                        return
                    turn_state.active = False
                    turn_state.current_turn_audio_chunks = 0
                    turn_state.current_turn_started_at = None
                    continue

                context.live_request_queue.close()
                if should_end_websocket:
                    return
        finally:
            elapsed_ms = int((perf_counter() - metrics.started_at) * 1000)
            logger.info(
                "[%s] session_summary duration_ms=%s rx_audio_chunks=%s rx_audio_bytes=%s tx_audio_chunks=%s tx_audio_bytes=%s rx_text=%s tx_text=%s parse_errors=%s",
                trace_id,
                elapsed_ms,
                metrics.incoming_audio_chunks,
                metrics.incoming_audio_bytes,
                metrics.outgoing_audio_chunks,
                metrics.outgoing_audio_bytes,
                metrics.incoming_text_events,
                metrics.outgoing_text_events,
                metrics.parse_errors,
            )

    async def _recv_events_from_client(
        self,
        websocket: WebSocket,
        queue: LiveRequestQueue,
        *,
        trace_id: str,
        metrics: SessionMetrics,
        turn_state: TurnState,
    ) -> None:
        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"] is not None:
                    raw_bytes = message["bytes"]
                    metrics.incoming_audio_chunks += 1
                    metrics.incoming_audio_bytes += len(raw_bytes)
                    logger.info(
                        "[%s] rx_audio_chunk seq=%s bytes=%s",
                        trace_id,
                        metrics.incoming_audio_chunks,
                        len(raw_bytes),
                    )
                    if turn_state.active:
                        turn_state.current_turn_audio_chunks += 1
                    audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=raw_bytes)
                    queue.send_realtime(audio_blob)
                    logger.info(
                        "[%s] queue_send_realtime seq=%s bytes=%s",
                        trace_id,
                        metrics.incoming_audio_chunks,
                        len(raw_bytes),
                    )
                    continue

                text_payload = message.get("text")
                if not text_payload:
                    logger.info("[%s] rx_non_text_non_binary_message keys=%s", trace_id, list(message.keys()))
                    continue

                try:
                    data = json.loads(text_payload)
                except json.JSONDecodeError:
                    metrics.parse_errors += 1
                    logger.warning(
                        "[%s] rx_text_parse_error payload_preview=%r",
                        trace_id,
                        text_payload[:200],
                    )
                    continue

                metrics.incoming_text_events += 1
                event_type = data.get("type")
                logger.info(
                    "[%s] rx_event seq=%s type=%s payload=%s",
                    trace_id,
                    metrics.incoming_text_events,
                    event_type,
                    data,
                )

                if event_type == "text_input":
                    text = str(data.get("text", "")).strip()
                    if not text:
                        logger.info("[%s] rx_text_input_ignored reason=empty_text", trace_id)
                        continue

                    content = types.Content(role="user", parts=[types.Part(text=text)])
                    queue.send_content(content)
                    logger.info("[%s] queue_send_content chars=%s", trace_id, len(text))
                    continue

                handled, next_active, action = self._route_control_event(
                    event_type=event_type,
                    queue=queue,
                    ptt_active=turn_state.active,
                )
                if not handled:
                    logger.info("[%s] rx_event_ignored type=%s", trace_id, event_type)
                    continue

                turn_state.active = next_active
                logger.info("[%s] control_event_handled type=%s action=%s", trace_id, event_type, action)

                if action == "start":
                    turn_state.turn_id += 1
                    turn_state.current_turn_audio_chunks = 0
                    turn_state.current_turn_started_at = perf_counter()
                    turn_state.current_turn_transcript = ""
                    logger.info("[%s] turn_open turn_id=%s", trace_id, turn_state.turn_id)
                    continue

                if action == "end":
                    duration_ms = 0
                    if turn_state.current_turn_started_at is not None:
                        duration_ms = int((perf_counter() - turn_state.current_turn_started_at) * 1000)
                    logger.info(
                        "[%s] turn_close turn_id=%s duration_ms=%s rx_audio_chunks=%s",
                        trace_id,
                        turn_state.turn_id,
                        duration_ms,
                        turn_state.current_turn_audio_chunks,
                    )
                    if turn_state.current_turn_audio_chunks < 3:
                        logger.warning(
                            "[%s] turn_short_audio turn_id=%s rx_audio_chunks=%s",
                            trace_id,
                            turn_state.turn_id,
                            turn_state.current_turn_audio_chunks,
                        )
                    turn_state.last_closed_turn_transcript = turn_state.current_turn_transcript.strip()
                    turn_state.awaiting_response_turn_id = turn_state.turn_id
                    turn_state.current_turn_transcript = ""
                    turn_state.current_turn_audio_chunks = 0
                    turn_state.current_turn_started_at = None
                    continue

                if action in {"duplicate_start", "duplicate_end"}:
                    logger.info("[%s] control_event_ignored_duplicate type=%s", trace_id, event_type)
                    continue

                if action == "stop":
                    break
        except WebSocketDisconnect:
            logger.info("[%s] recv_websocket_disconnected closing_queue", trace_id)
            queue.close()
            raise

    async def _send_events_to_client(
        self,
        websocket: WebSocket,
        live_events: AsyncIterator[Any],
        *,
        trace_id: str,
        metrics: SessionMetrics,
        turn_state: TurnState,
    ) -> None:
        announced_sample_rate: int | None = None
        async for event in live_events:
            logger.info("[%s] live_event_received event_type=%s", trace_id, type(event).__name__)

            if getattr(event, "interrupted", None):
                await websocket.send_json({"type": "assistant_interrupted"})
                metrics.outgoing_text_events += 1
                logger.info("[%s] tx_event type=assistant_interrupted", trace_id)

            for function_response in self._get_function_responses(event):
                payload = self._extract_ui_payload_from_function_response(function_response)
                if payload:
                    await websocket.send_json(payload)
                    metrics.outgoing_text_events += 1
                    logger.info("[%s] tx_event type=%s payload=%s", trace_id, payload.get("type"), payload)

            output_t = getattr(event, "output_transcription", None)
            if output_t and getattr(output_t, "text", None):
                self._mark_turn_response_started_if_needed(
                    turn_state=turn_state,
                    trace_id=trace_id,
                    source="assistant_text_output_transcription",
                )
                await websocket.send_json({"type": "assistant_text", "text": output_t.text})
                metrics.outgoing_text_events += 1
                logger.info("[%s] tx_event type=assistant_text source=output_transcription text=%r", trace_id, output_t.text)

            input_t = getattr(event, "input_transcription", None)
            if input_t and getattr(input_t, "text", None):
                normalized_input_t = str(input_t.text).strip()
                if normalized_input_t:
                    turn_state.last_input_transcript = self._merge_partial_transcript(
                        turn_state.last_input_transcript,
                        normalized_input_t,
                    )
                    if turn_state.active:
                        turn_state.current_turn_transcript = self._merge_partial_transcript(
                            turn_state.current_turn_transcript,
                            normalized_input_t,
                        )
                    elif turn_state.awaiting_response_turn_id is not None:
                        turn_state.last_closed_turn_transcript = self._merge_partial_transcript(
                            turn_state.last_closed_turn_transcript,
                            normalized_input_t,
                        )
                await websocket.send_json({"type": "partial_transcript", "text": input_t.text})
                metrics.outgoing_text_events += 1
                logger.info("[%s] tx_event type=partial_transcript text=%r", trace_id, input_t.text)

            content = getattr(event, "content", None)
            if not content:
                continue

            for part in getattr(content, "parts", []) or []:
                if getattr(part, "text", None):
                    self._mark_turn_response_started_if_needed(
                        turn_state=turn_state,
                        trace_id=trace_id,
                        source="assistant_text_content_part",
                    )
                    await websocket.send_json({"type": "assistant_text", "text": part.text})
                    metrics.outgoing_text_events += 1
                    logger.info("[%s] tx_event type=assistant_text source=content_part text=%r", trace_id, part.text)
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    sample_rate = self._extract_sample_rate(getattr(inline_data, "mime_type", None))
                    if sample_rate and sample_rate != announced_sample_rate:
                        announced_sample_rate = sample_rate
                        await websocket.send_json({"type": "assistant_audio_format", "sampleRate": sample_rate})
                        metrics.outgoing_text_events += 1
                        logger.info("[%s] tx_event type=assistant_audio_format sample_rate=%s", trace_id, sample_rate)
                    payload = inline_data.data
                    payload_bytes = base64.b64decode(payload) if isinstance(payload, str) else payload

                    self._mark_turn_response_started_if_needed(
                        turn_state=turn_state,
                        trace_id=trace_id,
                        source="assistant_audio_chunk",
                    )
                    metrics.outgoing_audio_chunks += 1
                    metrics.outgoing_audio_bytes += len(payload_bytes)
                    await websocket.send_bytes(payload_bytes)
                    logger.info(
                        "[%s] tx_audio_chunk seq=%s bytes=%s announced_sample_rate=%s",
                        trace_id,
                        metrics.outgoing_audio_chunks,
                        len(payload_bytes),
                        announced_sample_rate,
                    )

    async def _recover_from_live_api_error(
        self,
        *,
        websocket: WebSocket,
        context: LiveSessionContext,
        user_id: str,
        trace_id: str,
        metrics: SessionMetrics,
        turn_state: TurnState,
        error: genai_errors.APIError,
    ) -> bool:
        logger.warning("[%s] gemini_api_error code=%s triggering_fallback", trace_id, error.code)

        fallback_text = self._select_fallback_text(turn_state)
        current_turn_id = turn_state.turn_id
        if turn_state.fallback_attempted_turn_id == current_turn_id:
            await websocket.send_json(
                {
                    "type": "warning",
                    "message": "Live session failed again while recovering. Please restart the session.",
                }
            )
            metrics.outgoing_text_events += 1
            return False

        turn_state.fallback_attempted_turn_id = current_turn_id
        await websocket.send_json(
            {
                "type": "warning",
                "message": (
                    "Live voice session hit an unsupported operation during a tool step. "
                    "Attempting automatic recovery for this turn."
                ),
            }
        )
        metrics.outgoing_text_events += 1
        await websocket.send_json(
            {
                "type": "fallback_started",
                "reason": "live_tool_unsupported",
                "turnId": str(current_turn_id),
            }
        )
        metrics.outgoing_text_events += 1

        fallback_ok = await self._execute_text_fallback_turn(
            websocket=websocket,
            runner=context.runner,
            session_id=context.session.id,
            user_id=user_id,
            trace_id=trace_id,
            metrics=metrics,
            fallback_text=fallback_text,
        )

        await websocket.send_json(
            {
                "type": "fallback_completed",
                "turnId": str(current_turn_id),
                "result": "ok" if fallback_ok else "failed",
            }
        )
        metrics.outgoing_text_events += 1
        await websocket.send_json({"type": "session_recovering", "mode": "reconnect_live"})
        metrics.outgoing_text_events += 1

        turn_state.awaiting_response_turn_id = None
        turn_state.current_turn_transcript = ""
        turn_state.last_closed_turn_transcript = ""
        if not fallback_ok:
            await websocket.send_json(
                {
                    "type": "warning",
                    "message": "Automatic recovery could not replay the failed turn. Please repeat your request.",
                }
            )
            metrics.outgoing_text_events += 1
        return True

    async def _execute_text_fallback_turn(
        self,
        *,
        websocket: WebSocket,
        runner: Runner,
        session_id: str,
        user_id: str,
        trace_id: str,
        metrics: SessionMetrics,
        fallback_text: str,
    ) -> bool:
        normalized = fallback_text.strip()
        if not normalized:
            logger.warning("[%s] fallback_skipped reason=missing_transcript", trace_id)
            return False

        logger.info("[%s] fallback_run_async_started chars=%s", trace_id, len(normalized))
        content = types.Content(role="user", parts=[types.Part(text=normalized)])
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
                run_config=self._build_text_fallback_run_config(),
            ):
                for function_response in self._get_function_responses(event):
                    payload = self._extract_ui_payload_from_function_response(function_response)
                    if not payload:
                        continue
                    await websocket.send_json(payload)
                    metrics.outgoing_text_events += 1
                    logger.info(
                        "[%s] fallback_tool_payload_emitted type=%s",
                        trace_id,
                        payload.get("type"),
                    )

                output_t = getattr(event, "output_transcription", None)
                if output_t and getattr(output_t, "text", None):
                    await websocket.send_json({"type": "assistant_text", "text": output_t.text})
                    metrics.outgoing_text_events += 1

                event_content = getattr(event, "content", None)
                if not event_content:
                    continue
                for part in getattr(event_content, "parts", []) or []:
                    if getattr(part, "text", None):
                        await websocket.send_json({"type": "assistant_text", "text": part.text})
                        metrics.outgoing_text_events += 1
            logger.info("[%s] fallback_run_async_completed status=ok", trace_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("[%s] fallback_run_async_failed", trace_id, exc_info=exc)
            return False

    def _load_profile_context(self, user_id: str) -> ProfileContextResult:
        if self._patient_profile_service is None:
            return ProfileContextResult(
                state={
                    "app:profile_available": False,
                    "app:patient_profile": {},
                    "app:biomarker_targets": [],
                    "app:profile_summary": "",
                },
                profile_summary=None,
                loaded=False,
                source="none",
                message="No profile service configured. Continuing with general guidance.",
            )
        return self._patient_profile_service.load_profile_context(user_id)

    @staticmethod
    def _get_function_responses(event: Any) -> list[Any]:
        getter = getattr(event, "get_function_responses", None)
        if callable(getter):
            return getter() or []
        return []

    @staticmethod
    def _route_control_event(
        event_type: str | None,
        queue: LiveRequestQueue,
        *,
        ptt_active: bool,
    ) -> tuple[bool, bool, str]:
        if event_type == "ptt_start":
            if ptt_active:
                return True, ptt_active, "duplicate_start"
            queue.send_activity_start()
            return True, True, "start"
        if event_type in {"ptt_end", "end_turn"}:
            if not ptt_active:
                return True, ptt_active, "duplicate_end"
            queue.send_activity_end()
            return True, False, "end"
        if event_type == "stop_session":
            queue.close()
            return True, False, "stop"
        return False, ptt_active, "ignored"

    @staticmethod
    def _extract_ui_payload_from_function_response(function_response: Any) -> dict[str, Any] | None:
        raw_response = getattr(function_response, "response", None)
        if isinstance(raw_response, str):
            try:
                parsed = json.loads(raw_response)
            except json.JSONDecodeError:
                return None
        elif isinstance(raw_response, dict):
            parsed = raw_response
        else:
            return None

        payload_type = parsed.get("type")
        if payload_type in {"doctor_recommendations", "booking_update", "schedule_snapshot", "adherence_report_saved"}:
            return parsed
        return None

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

    @staticmethod
    def _mark_turn_response_started_if_needed(
        *,
        turn_state: TurnState,
        trace_id: str,
        source: str,
    ) -> None:
        if turn_state.awaiting_response_turn_id is None:
            return
        logger.info(
            "[%s] turn_response_started turn_id=%s source=%s",
            trace_id,
            turn_state.awaiting_response_turn_id,
            source,
        )
        turn_state.awaiting_response_turn_id = None

    @staticmethod
    def _build_text_fallback_run_config() -> RunConfig:
        return RunConfig(response_modalities=[types.Modality.TEXT])

    @staticmethod
    def _merge_partial_transcript(current: str, incoming: str) -> str:
        current_clean = current.strip()
        incoming_clean = incoming.strip()
        if not current_clean:
            return incoming_clean
        if not incoming_clean:
            return current_clean
        if incoming_clean.startswith(current_clean):
            return incoming_clean
        if len(incoming_clean) >= len(current_clean):
            return incoming_clean
        return current_clean

    @staticmethod
    def _select_fallback_text(turn_state: TurnState) -> str:
        if turn_state.last_closed_turn_transcript.strip():
            return turn_state.last_closed_turn_transcript
        return turn_state.last_input_transcript

    @staticmethod
    def _build_run_config() -> RunConfig:
        return RunConfig(
            response_modalities=[types.Modality.AUDIO],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=80,
                    silence_duration_ms=300,
                ),
            ),
        )

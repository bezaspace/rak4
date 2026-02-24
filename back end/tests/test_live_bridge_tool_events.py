from __future__ import annotations

import json

from app.live_bridge import LiveBridge


class _Response:
    def __init__(self, response):
        self.response = response


def test_extract_ui_payload_accepts_structured_event() -> None:
    payload = {"type": "doctor_recommendations", "requestId": "rec_1", "symptomsSummary": "cough", "doctors": []}
    extracted = LiveBridge._extract_ui_payload_from_function_response(_Response(payload))
    assert extracted == payload


def test_extract_ui_payload_accepts_json_string() -> None:
    payload = {"type": "booking_update", "status": "confirmed", "message": "ok"}
    extracted = LiveBridge._extract_ui_payload_from_function_response(_Response(json.dumps(payload)))
    assert extracted == payload


def test_extract_ui_payload_rejects_unknown_payload() -> None:
    extracted = LiveBridge._extract_ui_payload_from_function_response(_Response({"type": "other"}))
    assert extracted is None


def test_extract_ui_payload_accepts_schedule_events() -> None:
    payload = {"type": "schedule_snapshot", "date": "2026-02-22", "timezone": "UTC", "items": [], "timeline": []}
    extracted = LiveBridge._extract_ui_payload_from_function_response(_Response(payload))
    assert extracted == payload

    report_payload = {
        "type": "adherence_report_saved",
        "reportId": "rep_1",
        "scheduleItemId": "sched_1",
        "status": "done",
        "alertLevel": "none",
    }
    extracted_report = LiveBridge._extract_ui_payload_from_function_response(_Response(report_payload))
    assert extracted_report == report_payload


def test_load_profile_context_without_service_returns_soft_default() -> None:
    bridge = LiveBridge(app_name="raksha", model="gemini-test", gemini_api_key="fake-key")

    result = bridge._load_profile_context("raksha-user")

    assert result.loaded is False
    assert result.source == "none"
    assert result.state["app:profile_available"] is False

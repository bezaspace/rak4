from __future__ import annotations

from app.live_bridge import LiveBridge


class _QueueStub:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_activity_start(self) -> None:
        self.calls.append("start")

    def send_activity_end(self) -> None:
        self.calls.append("end")

    def close(self) -> None:
        self.calls.append("close")


def test_route_control_event_handles_ptt_start_end() -> None:
    queue = _QueueStub()
    handled, active, action = LiveBridge._route_control_event("ptt_start", queue, ptt_active=False)
    assert handled is True
    assert active is True
    assert action == "start"
    handled, active, action = LiveBridge._route_control_event("ptt_end", queue, ptt_active=active)
    assert handled is True
    assert active is False
    assert action == "end"
    assert queue.calls == ["start", "end"]


def test_route_control_event_handles_duplicate_ptt_events() -> None:
    queue = _QueueStub()
    handled, active, action = LiveBridge._route_control_event("ptt_start", queue, ptt_active=False)
    assert handled is True
    assert active is True
    assert action == "start"
    handled, active, action = LiveBridge._route_control_event("ptt_start", queue, ptt_active=active)
    assert handled is True
    assert active is True
    assert action == "duplicate_start"
    handled, active, action = LiveBridge._route_control_event("ptt_end", queue, ptt_active=active)
    assert handled is True
    assert active is False
    assert action == "end"
    handled, active, action = LiveBridge._route_control_event("ptt_end", queue, ptt_active=active)
    assert handled is True
    assert active is False
    assert action == "duplicate_end"
    assert queue.calls == ["start", "end"]


def test_route_control_event_handles_stop_session() -> None:
    queue = _QueueStub()
    handled, active, action = LiveBridge._route_control_event("stop_session", queue, ptt_active=True)
    assert handled is True
    assert active is False
    assert action == "stop"
    assert queue.calls == ["close"]


def test_route_control_event_ignores_unknown_events() -> None:
    queue = _QueueStub()
    handled, active, action = LiveBridge._route_control_event("unknown", queue, ptt_active=False)
    assert handled is False
    assert active is False
    assert action == "ignored"
    assert queue.calls == []


def test_build_run_config_uses_enum_modality() -> None:
    config = LiveBridge._build_run_config()
    dumped = config.model_dump(mode="json")
    assert dumped["response_modalities"] == ["AUDIO"]
    assert dumped["realtime_input_config"]["automatic_activity_detection"]["disabled"] is True


def test_api_error_uses_code_attribute() -> None:
    err = __import__("google.genai.errors", fromlist=["APIError"]).APIError(1007, None, None)
    assert getattr(err, "code", None) == 1007

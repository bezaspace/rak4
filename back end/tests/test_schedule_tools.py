from __future__ import annotations

from app.schedule_tools import build_schedule_tools


class _ScheduleServiceStub:
    def get_today_schedule(self, **kwargs):
        return {"date": "2026-02-22", "timezone": kwargs.get("timezone_name") or "UTC", "items": [], "timeline": []}

    def get_current_schedule_item(self, **_kwargs):
        class _Result:
            timezone = "UTC"
            local_now_iso = "2026-02-22T13:20:00+00:00"
            in_window = True
            current_item = None
            upcoming_item = None
            message = "Lunch now."

        return _Result()

    def save_adherence_report(self, **kwargs):
        return {"type": "adherence_report_saved", "saved": True, "status": kwargs["status"]}


class _ToolContextStub:
    state = {
        "app:user_id": "patient-1",
        "app:timezone": "Asia/Kolkata",
    }
    invocation_id = "inv_1"


def test_schedule_tools_emit_expected_payloads() -> None:
    tools = build_schedule_tools(_ScheduleServiceStub())
    assert len(tools) == 3

    get_today_schedule = tools[0]
    save_adherence_report = tools[2]

    snapshot = get_today_schedule(tool_context=_ToolContextStub())
    assert snapshot["type"] == "schedule_snapshot"
    assert snapshot["timezone"] == "Asia/Kolkata"

    saved = save_adherence_report(
        schedule_item_id="sched_1",
        status="done",
        followed_plan=True,
        tool_context=_ToolContextStub(),
    )
    assert saved["type"] == "adherence_report_saved"
    assert saved["saved"] is True

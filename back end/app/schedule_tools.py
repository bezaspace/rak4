from __future__ import annotations

from typing import Any, Callable

from google.adk.tools import ToolContext

from app.schedule_service import SCHEDULE_TIMEZONE_STATE_KEY
from app.schedule_service import SCHEDULE_USER_ID_STATE_KEY
from app.schedule_service import ScheduleService


def build_schedule_tools(schedule_service: ScheduleService | None) -> list[Callable[..., dict[str, Any]]]:
    if schedule_service is None:
        return []

    def _resolve_user_id(tool_context: ToolContext | None) -> str:
        if tool_context is None:
            return "raksha-user"
        value = str(tool_context.state.get(SCHEDULE_USER_ID_STATE_KEY, "")).strip()
        return value or "raksha-user"

    def _resolve_timezone(tool_context: ToolContext | None, explicit_timezone: str | None) -> str | None:
        if explicit_timezone and explicit_timezone.strip():
            return explicit_timezone.strip()
        if tool_context is None:
            return None
        value = str(tool_context.state.get(SCHEDULE_TIMEZONE_STATE_KEY, "")).strip()
        return value or None

    def get_today_schedule(
        timezone: str | None = None,
        date: str | None = None,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """
        Returns today's schedule and adherence timeline.
        Call this when the user asks what they should do now or asks for their daily plan.
        """
        user_id = _resolve_user_id(tool_context)
        resolved_timezone = _resolve_timezone(tool_context, timezone)
        schedule = schedule_service.get_today_schedule(
            user_id=user_id,
            timezone_name=resolved_timezone,
            date_str=date,
        )
        return {"type": "schedule_snapshot", **schedule}

    def get_current_schedule_item(
        timezone: str | None = None,
        now_iso: str | None = None,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """
        Resolves the current schedule item for the local time window.
        Use this before answering questions like "what should I do now?"
        """
        user_id = _resolve_user_id(tool_context)
        resolved_timezone = _resolve_timezone(tool_context, timezone)
        result = schedule_service.get_current_schedule_item(
            user_id=user_id,
            timezone_name=resolved_timezone,
            now_iso=now_iso,
        )
        return {
            "timezone": result.timezone,
            "localNowIso": result.local_now_iso,
            "inWindow": result.in_window,
            "currentItem": _serialize_item(result.current_item),
            "upcomingItem": _serialize_item(result.upcoming_item),
            "message": result.message,
        }

    def save_adherence_report(
        schedule_item_id: str,
        status: str,
        followed_plan: bool,
        changes_made: str | None = None,
        felt_after: str | None = None,
        symptoms: str | None = None,
        notes: str | None = None,
        alert_level: str = "none",
        summary: str | None = None,
        timezone: str | None = None,
        reported_at_iso: str | None = None,
        conversation_turn_id: str | None = None,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """
        Saves a structured adherence report linked to a schedule item.
        Call this after collecting check-in responses from the user.
        """
        user_id = _resolve_user_id(tool_context)
        resolved_timezone = _resolve_timezone(tool_context, timezone)
        session_id = None
        if tool_context is not None:
            session_id = str(getattr(tool_context, "invocation_id", "")).strip() or None
        return schedule_service.save_adherence_report(
            user_id=user_id,
            schedule_item_id=schedule_item_id,
            status=status,
            followed_plan=followed_plan,
            changes_made=changes_made,
            felt_after=felt_after,
            symptoms=symptoms,
            notes=notes,
            alert_level=alert_level,
            reported_at_iso=reported_at_iso,
            timezone_name=resolved_timezone,
            summary=summary,
            conversation_turn_id=conversation_turn_id,
            session_id=session_id,
        )

    return [get_today_schedule, get_current_schedule_item, save_adherence_report]


def _serialize_item(item: Any) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "scheduleItemId": item.id,
        "activityType": item.activity_type.value,
        "title": item.title,
        "instructions": item.instructions,
        "windowStartLocal": item.window_start_local,
        "windowEndLocal": item.window_end_local,
        "displayOrder": item.display_order,
    }

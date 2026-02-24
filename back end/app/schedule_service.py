from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.schedule_models import AdherenceReport
from app.schedule_models import AdherenceReportRow
from app.schedule_models import AdherenceStatus
from app.schedule_models import AlertLevel
from app.schedule_models import ScheduleActivityType
from app.schedule_models import ScheduleItem
from app.schedule_repository import ScheduleRepository

SCHEDULE_USER_ID_STATE_KEY = "app:user_id"
SCHEDULE_TIMEZONE_STATE_KEY = "app:timezone"


@dataclass
class ScheduleTimeContext:
    timezone: str
    local_now: datetime
    report_date_local: str


@dataclass
class CurrentScheduleResolution:
    timezone: str
    local_now_iso: str
    in_window: bool
    current_item: ScheduleItem | None
    upcoming_item: ScheduleItem | None
    message: str


class ScheduleService:
    def __init__(self, repository: ScheduleRepository) -> None:
        self._repository = repository

    def get_today_schedule(
        self,
        *,
        user_id: str,
        timezone_name: str | None,
        date_str: str | None = None,
    ) -> dict[str, object]:
        ctx = self._build_time_context(timezone_name=timezone_name, reported_at_iso=None, date_str=date_str)
        items = self._repository.list_active_items(user_id)
        reports = self._repository.list_reports_by_date(user_id, ctx.report_date_local)
        latest_by_item = self._latest_report_by_item(reports)

        item_cards: list[dict[str, object]] = []
        for item in items:
            latest = latest_by_item.get(item.id)
            item_cards.append(
                {
                    "scheduleItemId": item.id,
                    "activityType": item.activity_type.value,
                    "title": item.title,
                    "instructions": item.instructions,
                    "windowStartLocal": item.window_start_local,
                    "windowEndLocal": item.window_end_local,
                    "displayOrder": item.display_order,
                    "latestReport": self._serialize_report_brief(latest),
                }
            )

        timeline = [self._serialize_report_detail(report) for report in reports]
        return {
            "date": ctx.report_date_local,
            "timezone": ctx.timezone,
            "items": item_cards,
            "timeline": timeline,
            "message": "Loaded daily schedule and adherence timeline.",
        }

    def get_current_schedule_item(
        self,
        *,
        user_id: str,
        timezone_name: str | None,
        now_iso: str | None = None,
    ) -> CurrentScheduleResolution:
        ctx = self._build_time_context(timezone_name=timezone_name, reported_at_iso=now_iso)
        local_now_time = ctx.local_now.time().replace(second=0, microsecond=0)
        items = self._repository.list_active_items(user_id)

        in_window_items = [item for item in items if self._is_time_in_window(local_now_time, item)]
        if in_window_items:
            chosen = sorted(in_window_items, key=lambda item: (item.display_order, item.window_start_local, item.id))[0]
            return CurrentScheduleResolution(
                timezone=ctx.timezone,
                local_now_iso=ctx.local_now.isoformat(),
                in_window=True,
                current_item=chosen,
                upcoming_item=None,
                message=f"It is currently time for '{chosen.title}'.",
            )

        upcoming = self._next_upcoming_item(local_now_time, items)
        if upcoming:
            return CurrentScheduleResolution(
                timezone=ctx.timezone,
                local_now_iso=ctx.local_now.isoformat(),
                in_window=False,
                current_item=None,
                upcoming_item=upcoming,
                message=f"No active item right now. Next up is '{upcoming.title}' at {upcoming.window_start_local}.",
            )

        return CurrentScheduleResolution(
            timezone=ctx.timezone,
            local_now_iso=ctx.local_now.isoformat(),
            in_window=False,
            current_item=None,
            upcoming_item=None,
            message="No more scheduled items remain for today.",
        )

    def save_adherence_report(
        self,
        *,
        user_id: str,
        schedule_item_id: str,
        status: str,
        followed_plan: bool,
        changes_made: str | None,
        felt_after: str | None,
        symptoms: str | None,
        notes: str | None,
        alert_level: str,
        reported_at_iso: str | None,
        timezone_name: str | None,
        summary: str | None = None,
        conversation_turn_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, object]:
        context = self._build_time_context(timezone_name=timezone_name, reported_at_iso=reported_at_iso)
        item, resolved_schedule_item_id = self._resolve_schedule_item(
            user_id=user_id,
            schedule_item_id=schedule_item_id,
            context=context,
        )
        if item is None:
            return self._build_failure_payload(
                message=(
                    f"Could not save adherence: schedule item '{schedule_item_id}' was not found. "
                    "Please use the exact schedule item id from get_today_schedule."
                ),
                reason_code="invalid_item_id",
            )
        try:
            normalized_status = AdherenceStatus(status.strip().lower())
        except ValueError:
            return self._build_failure_payload(
                message=f"Invalid status '{status}'. Use done, partial, skipped, or delayed.",
                reason_code="invalid_status",
            )
        try:
            normalized_alert = AlertLevel(alert_level.strip().lower())
        except ValueError:
            return self._build_failure_payload(
                message=f"Invalid alert_level '{alert_level}'. Use none, watch, or urgent.",
                reason_code="invalid_alert",
            )

        duplicate = self._repository.find_duplicate_report(
            user_id=user_id,
            schedule_item_id=item.id,
            session_id=session_id,
            conversation_turn_id=conversation_turn_id,
        )
        if duplicate is not None:
            return self._build_saved_payload(
                duplicate,
                saved=True,
                deduped=True,
                resolved_schedule_item_id=resolved_schedule_item_id,
            )

        final_summary = self._build_summary(
            title=item.title,
            status=normalized_status,
            followed_plan=followed_plan,
            felt_after=felt_after,
            symptoms=symptoms,
            notes=notes,
            summary=summary,
        )
        report_row = AdherenceReportRow(
            user_id=user_id.strip(),
            schedule_item_id=item.id,
            report_date_local=context.report_date_local,
            activity_type=item.activity_type.value,
            status=normalized_status.value,
            followed_plan=followed_plan,
            changes_made=(changes_made or "").strip() or None,
            felt_after=(felt_after or "").strip() or None,
            symptoms=(symptoms or "").strip() or None,
            notes=(notes or "").strip() or None,
            alert_level=normalized_alert.value,
            summary=final_summary,
            reported_at_iso=context.local_now.astimezone(UTC).isoformat(),
            conversation_turn_id=(conversation_turn_id or "").strip() or None,
            session_id=(session_id or "").strip() or None,
        )
        saved_report = self._repository.save_report(report_row)
        return self._build_saved_payload(
            saved_report,
            saved=True,
            deduped=False,
            resolved_schedule_item_id=resolved_schedule_item_id,
        )

    def list_reports_for_item(
        self,
        *,
        user_id: str,
        schedule_item_id: str,
        timezone_name: str | None,
        date_str: str | None,
    ) -> dict[str, object]:
        context = self._build_time_context(timezone_name=timezone_name, reported_at_iso=None, date_str=date_str)
        reports = self._repository.list_reports_for_item(
            user_id=user_id,
            schedule_item_id=schedule_item_id,
            report_date_local=context.report_date_local,
        )
        return {
            "scheduleItemId": schedule_item_id,
            "date": context.report_date_local,
            "timezone": context.timezone,
            "reports": [self._serialize_report_detail(report) for report in reports],
        }

    @staticmethod
    def _is_time_in_window(local_now: time, item: ScheduleItem) -> bool:
        start = time.fromisoformat(item.window_start_local)
        end = time.fromisoformat(item.window_end_local)
        return start <= local_now < end

    @staticmethod
    def _next_upcoming_item(local_now: time, items: list[ScheduleItem]) -> ScheduleItem | None:
        upcoming = [item for item in items if time.fromisoformat(item.window_start_local) > local_now]
        if not upcoming:
            return None
        return sorted(upcoming, key=lambda item: (item.window_start_local, item.display_order, item.id))[0]

    @staticmethod
    def _latest_report_by_item(reports: list[AdherenceReport]) -> dict[str, AdherenceReport]:
        latest: dict[str, AdherenceReport] = {}
        for report in reports:
            current = latest.get(report.schedule_item_id)
            if current is None or report.reported_at_iso >= current.reported_at_iso:
                latest[report.schedule_item_id] = report
        return latest

    @staticmethod
    def _serialize_report_brief(report: AdherenceReport | None) -> dict[str, object] | None:
        if report is None:
            return None
        return {
            "reportId": report.id,
            "status": report.status.value,
            "alertLevel": report.alert_level.value,
            "summary": report.summary,
            "reportedAtIso": report.reported_at_iso,
        }

    @staticmethod
    def _serialize_report_detail(report: AdherenceReport) -> dict[str, object]:
        return {
            "reportId": report.id,
            "scheduleItemId": report.schedule_item_id,
            "activityType": report.activity_type.value,
            "status": report.status.value,
            "followedPlan": report.followed_plan,
            "changesMade": report.changes_made,
            "feltAfter": report.felt_after,
            "symptoms": report.symptoms,
            "notes": report.notes,
            "alertLevel": report.alert_level.value,
            "summary": report.summary,
            "reportedAtIso": report.reported_at_iso,
            "createdAt": report.created_at,
            "conversationTurnId": report.conversation_turn_id,
            "sessionId": report.session_id,
        }

    @staticmethod
    def _build_summary(
        *,
        title: str,
        status: AdherenceStatus,
        followed_plan: bool,
        felt_after: str | None,
        symptoms: str | None,
        notes: str | None,
        summary: str | None,
    ) -> str:
        if summary and summary.strip():
            return summary.strip()
        parts = [f"{title}: {status.value}."]
        parts.append("Followed plan." if followed_plan else "Did not fully follow plan.")
        if felt_after:
            parts.append(f"How they felt: {felt_after.strip()}.")
        if symptoms:
            parts.append(f"Symptoms: {symptoms.strip()}.")
        if notes:
            parts.append(f"Notes: {notes.strip()}.")
        return " ".join(parts)

    @staticmethod
    def _build_saved_payload(
        report: AdherenceReport,
        *,
        saved: bool,
        deduped: bool,
        resolved_schedule_item_id: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "type": "adherence_report_saved",
            "saved": saved,
            "deduped": deduped,
            "reasonCode": None,
            "reportId": report.id,
            "scheduleItemId": report.schedule_item_id,
            "date": report.report_date_local,
            "activityType": report.activity_type.value,
            "status": report.status.value,
            "alertLevel": report.alert_level.value,
            "summary": report.summary,
            "reportedAtIso": report.reported_at_iso,
            "createdAt": report.created_at,
            "followedPlan": report.followed_plan,
            "changesMade": report.changes_made,
            "feltAfter": report.felt_after,
            "symptoms": report.symptoms,
            "notes": report.notes,
            "conversationTurnId": report.conversation_turn_id,
            "sessionId": report.session_id,
            "message": "Saved adherence report.",
        }
        if resolved_schedule_item_id and resolved_schedule_item_id != report.schedule_item_id:
            payload["resolvedScheduleItemId"] = report.schedule_item_id
            payload["message"] = (
                f"Saved adherence report after mapping '{resolved_schedule_item_id}' "
                f"to '{report.schedule_item_id}'."
            )
        return payload

    @staticmethod
    def _build_failure_payload(*, message: str, reason_code: str) -> dict[str, object]:
        return {
            "type": "adherence_report_saved",
            "saved": False,
            "message": message,
            "reasonCode": reason_code,
        }

    def _resolve_schedule_item(
        self,
        *,
        user_id: str,
        schedule_item_id: str,
        context: ScheduleTimeContext,
    ) -> tuple[ScheduleItem | None, str | None]:
        raw = schedule_item_id.strip()
        if not raw:
            return None, None

        exact = self._repository.get_item_by_id(user_id, raw)
        if exact is not None:
            return exact, None

        items = self._repository.list_active_items(user_id)
        if not items:
            return None, raw

        normalized_query = self._normalize_label(raw)

        # 1) Direct title equality on normalized text.
        for item in items:
            if self._normalize_label(item.title) == normalized_query:
                return item, raw

        # 2) Substring similarity on titles.
        substring_matches = [
            item
            for item in items
            if normalized_query and normalized_query in self._normalize_label(item.title)
        ]
        if substring_matches:
            return self._choose_best_item(substring_matches, context), raw

        # 3) Map common aliases (e.g. lunch, meds, walk) to activity type.
        alias_type = self._infer_activity_type_from_alias(normalized_query)
        if alias_type is not None:
            typed = [item for item in items if item.activity_type == alias_type]
            if typed:
                return self._choose_best_item(typed, context), raw

        # 4) If user passed "diet"/"medication"/"sleep"/"activity" directly.
        type_matches = [
            item
            for item in items
            if normalized_query == item.activity_type.value
        ]
        if type_matches:
            return self._choose_best_item(type_matches, context), raw

        return None, raw

    @staticmethod
    def _normalize_label(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    @staticmethod
    def _infer_activity_type_from_alias(label: str) -> ScheduleActivityType | None:
        alias_map: list[tuple[ScheduleActivityType, set[str]]] = [
            (ScheduleActivityType.DIET, {"meal", "breakfast", "lunch", "dinner", "snack", "food"}),
            (ScheduleActivityType.MEDICATION, {"medication", "medicine", "meds", "pill", "tablet", "dose"}),
            (ScheduleActivityType.ACTIVITY, {"activity", "exercise", "walk", "workout", "run", "yoga"}),
            (ScheduleActivityType.SLEEP, {"sleep", "bedtime", "rest", "nap"}),
        ]
        for activity_type, aliases in alias_map:
            if label in aliases:
                return activity_type
        return None

    @staticmethod
    def _choose_best_item(items: list[ScheduleItem], context: ScheduleTimeContext) -> ScheduleItem:
        now_local = context.local_now.time().replace(second=0, microsecond=0)
        in_window = [item for item in items if ScheduleService._is_time_in_window(now_local, item)]
        if in_window:
            return sorted(in_window, key=lambda item: (item.display_order, item.window_start_local, item.id))[0]

        return sorted(
            items,
            key=lambda item: (
                abs(
                    (time.fromisoformat(item.window_start_local).hour * 60 + time.fromisoformat(item.window_start_local).minute)
                    - (now_local.hour * 60 + now_local.minute)
                ),
                item.display_order,
                item.id,
            ),
        )[0]

    @staticmethod
    def _build_time_context(
        *,
        timezone_name: str | None,
        reported_at_iso: str | None,
        date_str: str | None = None,
    ) -> ScheduleTimeContext:
        tz_name = (timezone_name or "").strip() or "UTC"
        try:
            zone = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            zone = ZoneInfo("UTC")
            tz_name = "UTC"

        if date_str:
            try:
                parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                parsed_date = datetime.now(tz=zone).date()
            local_now = datetime.combine(parsed_date, time(hour=12, minute=0), tzinfo=zone)
            return ScheduleTimeContext(
                timezone=tz_name,
                local_now=local_now,
                report_date_local=parsed_date.isoformat(),
            )

        if reported_at_iso and reported_at_iso.strip():
            normalized = reported_at_iso.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=zone)
                local_now = parsed.astimezone(zone)
            except ValueError:
                local_now = datetime.now(tz=zone)
        else:
            local_now = datetime.now(tz=zone)

        return ScheduleTimeContext(
            timezone=tz_name,
            local_now=local_now,
            report_date_local=local_now.date().isoformat(),
        )

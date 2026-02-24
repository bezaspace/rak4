from __future__ import annotations

from app.schedule_models import AdherenceReport
from app.schedule_models import AdherenceStatus
from app.schedule_models import AlertLevel
from app.schedule_models import ScheduleActivityType
from app.schedule_models import ScheduleItem
from app.schedule_service import ScheduleService


class _ScheduleRepositoryStub:
    def __init__(self) -> None:
        self.items = [
            ScheduleItem(
                id="sched_lunch",
                user_id="patient-1",
                activity_type=ScheduleActivityType.DIET,
                title="Lunch",
                instructions=["dal", "salad"],
                window_start_local="13:00",
                window_end_local="14:00",
                display_order=1,
                active=True,
                created_at="2026-02-20T10:00:00Z",
                updated_at="2026-02-20T10:00:00Z",
            ),
            ScheduleItem(
                id="sched_walk",
                user_id="patient-1",
                activity_type=ScheduleActivityType.ACTIVITY,
                title="Walk",
                instructions=["30 min brisk walk"],
                window_start_local="18:00",
                window_end_local="19:00",
                display_order=2,
                active=True,
                created_at="2026-02-20T10:00:00Z",
                updated_at="2026-02-20T10:00:00Z",
            ),
        ]
        self.saved_reports: list[dict[str, str]] = []
        self.reports = [
            AdherenceReport(
                id="rep_1",
                user_id="patient-1",
                schedule_item_id="sched_lunch",
                report_date_local="2026-02-22",
                activity_type=ScheduleActivityType.DIET,
                status=AdherenceStatus.DONE,
                followed_plan=True,
                summary="Lunch done.",
                alert_level=AlertLevel.NONE,
                reported_at_iso="2026-02-22T13:15:00+00:00",
                created_at="2026-02-22T13:15:00+00:00",
            )
        ]

    def list_active_items(self, _user_id: str) -> list[ScheduleItem]:
        return self.items

    def list_reports_by_date(self, _user_id: str, _date: str) -> list[AdherenceReport]:
        return self.reports

    def get_item_by_id(self, _user_id: str, item_id: str) -> ScheduleItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def find_duplicate_report(self, **_kwargs):
        return None

    def save_report(self, row):
        self.saved_reports.append(
            {
                "status": row.status,
                "alert_level": row.alert_level,
                "schedule_item_id": row.schedule_item_id,
            }
        )
        return AdherenceReport.model_validate(
            {
                "id": "rep_saved",
                "user_id": row.user_id,
                "schedule_item_id": row.schedule_item_id,
                "report_date_local": row.report_date_local,
                "activity_type": row.activity_type,
                "status": row.status,
                "followed_plan": row.followed_plan,
                "changes_made": row.changes_made,
                "felt_after": row.felt_after,
                "symptoms": row.symptoms,
                "notes": row.notes,
                "alert_level": row.alert_level,
                "summary": row.summary,
                "reported_at_iso": row.reported_at_iso,
                "conversation_turn_id": row.conversation_turn_id,
                "session_id": row.session_id,
                "created_at": "2026-02-22T13:20:00+00:00",
            }
        )

    def list_reports_for_item(self, _user_id: str, _schedule_item_id: str, report_date_local: str | None = None):
        if report_date_local:
            return [report for report in self.reports if report.report_date_local == report_date_local]
        return self.reports


def test_get_current_schedule_item_strict_window() -> None:
    service = ScheduleService(_ScheduleRepositoryStub())
    current = service.get_current_schedule_item(
        user_id="patient-1",
        timezone_name="UTC",
        now_iso="2026-02-22T13:20:00+00:00",
    )
    assert current.in_window is True
    assert current.current_item is not None
    assert current.current_item.id == "sched_lunch"


def test_get_current_schedule_item_returns_upcoming_when_between_windows() -> None:
    service = ScheduleService(_ScheduleRepositoryStub())
    current = service.get_current_schedule_item(
        user_id="patient-1",
        timezone_name="UTC",
        now_iso="2026-02-22T15:10:00+00:00",
    )
    assert current.in_window is False
    assert current.current_item is None
    assert current.upcoming_item is not None
    assert current.upcoming_item.id == "sched_walk"


def test_save_adherence_report_returns_persisted_payload() -> None:
    repo = _ScheduleRepositoryStub()
    service = ScheduleService(repo)

    payload = service.save_adherence_report(
        user_id="patient-1",
        schedule_item_id="sched_lunch",
        status="partial",
        followed_plan=False,
        changes_made="ate less rice",
        felt_after="felt okay",
        symptoms="none",
        notes="will hydrate more",
        alert_level="watch",
        reported_at_iso="2026-02-22T13:40:00+00:00",
        timezone_name="UTC",
        summary=None,
        conversation_turn_id="turn_10",
        session_id="session_20",
    )
    assert payload["type"] == "adherence_report_saved"
    assert payload["saved"] is True
    assert payload["status"] == "partial"
    assert repo.saved_reports[0]["alert_level"] == "watch"


def test_save_adherence_report_resolves_human_label_to_schedule_item() -> None:
    repo = _ScheduleRepositoryStub()
    service = ScheduleService(repo)

    payload = service.save_adherence_report(
        user_id="patient-1",
        schedule_item_id="lunch",
        status="done",
        followed_plan=True,
        changes_made=None,
        felt_after="good",
        symptoms=None,
        notes=None,
        alert_level="none",
        reported_at_iso="2026-02-22T13:35:00+00:00",
        timezone_name="UTC",
        summary=None,
        conversation_turn_id="turn_12",
        session_id="session_30",
    )

    assert payload["saved"] is True
    assert payload["scheduleItemId"] == "sched_lunch"
    assert payload["resolvedScheduleItemId"] == "sched_lunch"
    assert repo.saved_reports[0]["schedule_item_id"] == "sched_lunch"


def test_save_adherence_report_returns_reason_code_for_invalid_item() -> None:
    repo = _ScheduleRepositoryStub()
    service = ScheduleService(repo)

    payload = service.save_adherence_report(
        user_id="patient-1",
        schedule_item_id="unknown-item",
        status="done",
        followed_plan=True,
        changes_made=None,
        felt_after=None,
        symptoms=None,
        notes=None,
        alert_level="none",
        reported_at_iso="2026-02-22T13:35:00+00:00",
        timezone_name="UTC",
        summary=None,
        conversation_turn_id=None,
        session_id=None,
    )

    assert payload["saved"] is False
    assert payload["reasonCode"] == "invalid_item_id"

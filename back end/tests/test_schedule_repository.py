from __future__ import annotations

from pathlib import Path

from app.schedule_models import AdherenceReportRow
from app.schedule_repository import ScheduleRepository


def _write_seed(seed_path: Path) -> None:
    seed_path.write_text(
        "\n".join(
            [
                "CREATE TABLE IF NOT EXISTS schedule_items (",
                "  id TEXT PRIMARY KEY,",
                "  user_id TEXT NOT NULL,",
                "  activity_type TEXT NOT NULL,",
                "  title TEXT NOT NULL,",
                "  instructions_json TEXT NOT NULL,",
                "  window_start_local TEXT NOT NULL,",
                "  window_end_local TEXT NOT NULL,",
                "  display_order INTEGER NOT NULL DEFAULT 0,",
                "  active BOOLEAN NOT NULL DEFAULT 1,",
                "  created_at TEXT NOT NULL,",
                "  updated_at TEXT NOT NULL",
                ");",
                "INSERT OR REPLACE INTO schedule_items (",
                "  id, user_id, activity_type, title, instructions_json, window_start_local, window_end_local, display_order, active, created_at, updated_at",
                ") VALUES (",
                "  'sched_1', 'patient-1', 'diet', 'Lunch', '[\"dal\",\"salad\"]', '13:00', '14:00', 1, 1, '2026-02-20T10:00:00Z', '2026-02-20T10:00:00Z'",
                ");",
            ]
        ),
        encoding="utf-8",
    )


def test_list_active_items_and_save_report(tmp_path: Path) -> None:
    seed_path = tmp_path / "schedule_seed.sql"
    db_path = tmp_path / "schedule.db"
    _write_seed(seed_path)

    repo = ScheduleRepository(db_url=f"sqlite:///{db_path}", seed_sql_path=seed_path)
    repo.initialize()

    items = repo.list_active_items("patient-1")
    assert len(items) == 1
    assert items[0].title == "Lunch"

    saved = repo.save_report(
        AdherenceReportRow(
            user_id="patient-1",
            schedule_item_id="sched_1",
            report_date_local="2026-02-22",
            activity_type="diet",
            status="done",
            followed_plan=True,
            summary="Lunch completed as planned.",
            alert_level="none",
            reported_at_iso="2026-02-22T13:10:00+00:00",
        )
    )
    assert saved.schedule_item_id == "sched_1"
    reports = repo.list_reports_by_date("patient-1", "2026-02-22")
    assert len(reports) == 1
    assert reports[0].status.value == "done"


def test_find_duplicate_report_by_session_and_turn(tmp_path: Path) -> None:
    seed_path = tmp_path / "schedule_seed.sql"
    db_path = tmp_path / "schedule.db"
    _write_seed(seed_path)

    repo = ScheduleRepository(db_url=f"sqlite:///{db_path}", seed_sql_path=seed_path)
    repo.initialize()
    repo.save_report(
        AdherenceReportRow(
            user_id="patient-1",
            schedule_item_id="sched_1",
            report_date_local="2026-02-22",
            activity_type="diet",
            status="partial",
            followed_plan=False,
            summary="Modified lunch plan.",
            alert_level="watch",
            reported_at_iso="2026-02-22T13:15:00+00:00",
            session_id="sess_1",
            conversation_turn_id="turn_1",
        )
    )

    duplicate = repo.find_duplicate_report(
        user_id="patient-1",
        schedule_item_id="sched_1",
        session_id="sess_1",
        conversation_turn_id="turn_1",
    )
    assert duplicate is not None
    assert duplicate.alert_level.value == "watch"

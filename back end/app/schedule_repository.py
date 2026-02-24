from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

from app.schedule_models import AdherenceReport
from app.schedule_models import AdherenceReportRow
from app.schedule_models import ScheduleItem
from app.schedule_models import ScheduleItemRow

logger = logging.getLogger("raksha.schedule_repository")


class ScheduleRepository:
    def __init__(self, db_url: str, seed_sql_path: Path) -> None:
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        self._engine = create_engine(db_url, connect_args=connect_args)
        self._seed_sql_path = seed_sql_path

    def initialize(self) -> None:
        SQLModel.metadata.create_all(self._engine)

        if not self._seed_sql_path.exists():
            logger.warning("schedule_seed_missing seed_sql_path=%s", self._seed_sql_path)
            return

        sql_script = self._seed_sql_path.read_text(encoding="utf-8").strip()
        if not sql_script:
            logger.warning("schedule_seed_empty seed_sql_path=%s", self._seed_sql_path)
            return

        statements = [statement.strip() for statement in sql_script.split(";") if statement.strip()]
        if not statements:
            return

        with Session(self._engine) as session:
            for statement in statements:
                session.exec(text(statement))
            session.commit()

    def list_active_items(self, user_id: str) -> list[ScheduleItem]:
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            return []

        with Session(self._engine) as session:
            rows = session.exec(
                select(ScheduleItemRow)
                .where(ScheduleItemRow.user_id == normalized_user_id)
                .where(ScheduleItemRow.active.is_(True))
                .order_by(ScheduleItemRow.display_order, ScheduleItemRow.window_start_local, ScheduleItemRow.id)
            ).all()
            return [item for row in rows if (item := self._row_to_item(row)) is not None]

    def get_item_by_id(self, user_id: str, item_id: str) -> ScheduleItem | None:
        normalized_user_id = user_id.strip()
        normalized_item_id = item_id.strip()
        if not normalized_user_id or not normalized_item_id:
            return None

        with Session(self._engine) as session:
            row = session.exec(
                select(ScheduleItemRow)
                .where(ScheduleItemRow.user_id == normalized_user_id)
                .where(ScheduleItemRow.id == normalized_item_id)
            ).first()
            if row is None:
                return None
            return self._row_to_item(row)

    def list_reports_by_date(self, user_id: str, report_date_local: str) -> list[AdherenceReport]:
        normalized_user_id = user_id.strip()
        normalized_date = report_date_local.strip()
        if not normalized_user_id or not normalized_date:
            return []

        with Session(self._engine) as session:
            rows = session.exec(
                select(AdherenceReportRow)
                .where(AdherenceReportRow.user_id == normalized_user_id)
                .where(AdherenceReportRow.report_date_local == normalized_date)
                .order_by(AdherenceReportRow.reported_at_iso, AdherenceReportRow.created_at, AdherenceReportRow.id)
            ).all()
            return [report for row in rows if (report := self._row_to_report(row)) is not None]

    def list_reports_for_item(
        self,
        user_id: str,
        schedule_item_id: str,
        report_date_local: str | None = None,
    ) -> list[AdherenceReport]:
        normalized_user_id = user_id.strip()
        normalized_item_id = schedule_item_id.strip()
        if not normalized_user_id or not normalized_item_id:
            return []

        with Session(self._engine) as session:
            query = (
                select(AdherenceReportRow)
                .where(AdherenceReportRow.user_id == normalized_user_id)
                .where(AdherenceReportRow.schedule_item_id == normalized_item_id)
            )
            if report_date_local:
                query = query.where(AdherenceReportRow.report_date_local == report_date_local.strip())
            rows = session.exec(query.order_by(AdherenceReportRow.reported_at_iso, AdherenceReportRow.created_at)).all()
            return [report for row in rows if (report := self._row_to_report(row)) is not None]

    def find_duplicate_report(
        self,
        *,
        user_id: str,
        schedule_item_id: str,
        session_id: str | None,
        conversation_turn_id: str | None,
    ) -> AdherenceReport | None:
        if not session_id or not conversation_turn_id:
            return None
        with Session(self._engine) as session:
            row = session.exec(
                select(AdherenceReportRow)
                .where(AdherenceReportRow.user_id == user_id.strip())
                .where(AdherenceReportRow.schedule_item_id == schedule_item_id.strip())
                .where(AdherenceReportRow.session_id == session_id.strip())
                .where(AdherenceReportRow.conversation_turn_id == conversation_turn_id.strip())
            ).first()
            if row is None:
                return None
            return self._row_to_report(row)

    def save_report(self, report_row: AdherenceReportRow) -> AdherenceReport:
        with Session(self._engine) as session:
            session.add(report_row)
            session.commit()
            session.refresh(report_row)
            parsed = self._row_to_report(report_row)
            if parsed is None:
                raise ValueError("saved adherence report could not be parsed")
            return parsed

    def _row_to_item(self, row: ScheduleItemRow) -> ScheduleItem | None:
        try:
            instructions = self._decode_list(row.instructions_json, field_name="instructions_json", row_id=row.id)
        except ValueError:
            return None
        try:
            return ScheduleItem.model_validate(
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "activity_type": row.activity_type,
                    "title": row.title,
                    "instructions": instructions,
                    "window_start_local": row.window_start_local,
                    "window_end_local": row.window_end_local,
                    "display_order": row.display_order,
                    "active": row.active,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("schedule_item_invalid_shape id=%s error_type=%s", row.id, type(exc).__name__)
            return None

    def _row_to_report(self, row: AdherenceReportRow) -> AdherenceReport | None:
        try:
            return AdherenceReport.model_validate(
                {
                    "id": row.id,
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
                    "created_at": row.created_at,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("adherence_report_invalid_shape id=%s error_type=%s", row.id, type(exc).__name__)
            return None

    @staticmethod
    def _decode_list(raw: str, *, field_name: str, row_id: str) -> list[Any]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("schedule_json_decode_failed id=%s field=%s", row_id, field_name)
            raise ValueError(field_name) from None

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

        logger.warning("schedule_json_not_list id=%s field=%s", row_id, field_name)
        raise ValueError(field_name)

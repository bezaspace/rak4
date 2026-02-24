from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Field, SQLModel


class ScheduleActivityType(StrEnum):
    DIET = "diet"
    MEDICATION = "medication"
    SLEEP = "sleep"
    ACTIVITY = "activity"


class AdherenceStatus(StrEnum):
    DONE = "done"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    DELAYED = "delayed"


class AlertLevel(StrEnum):
    NONE = "none"
    WATCH = "watch"
    URGENT = "urgent"


class ScheduleItem(BaseModel):
    id: str
    user_id: str
    activity_type: ScheduleActivityType
    title: str
    instructions: list[str] = PydanticField(default_factory=list)
    window_start_local: str
    window_end_local: str
    display_order: int = 0
    active: bool = True
    created_at: str
    updated_at: str


class AdherenceReport(BaseModel):
    id: str
    user_id: str
    schedule_item_id: str
    report_date_local: str
    activity_type: ScheduleActivityType
    status: AdherenceStatus
    followed_plan: bool
    changes_made: str | None = None
    felt_after: str | None = None
    symptoms: str | None = None
    notes: str | None = None
    alert_level: AlertLevel = AlertLevel.NONE
    summary: str
    reported_at_iso: str
    conversation_turn_id: str | None = None
    session_id: str | None = None
    created_at: str


class ScheduleItemRow(SQLModel, table=True):
    __tablename__ = "schedule_items"

    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    activity_type: str = Field(index=True)
    title: str
    instructions_json: str = Field(default="[]")
    window_start_local: str
    window_end_local: str
    display_order: int = Field(default=0)
    active: bool = Field(default=True, index=True)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdherenceReportRow(SQLModel, table=True):
    __tablename__ = "adherence_reports"

    id: str = Field(default_factory=lambda: f"rep_{uuid4().hex[:16]}", primary_key=True, index=True)
    user_id: str = Field(index=True)
    schedule_item_id: str = Field(index=True)
    report_date_local: str = Field(index=True)
    activity_type: str = Field(index=True)
    status: str = Field(index=True)
    followed_plan: bool = Field(default=False)
    changes_made: str | None = Field(default=None)
    felt_after: str | None = Field(default=None)
    symptoms: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    alert_level: str = Field(default=AlertLevel.NONE.value, index=True)
    summary: str
    reported_at_iso: str
    conversation_turn_id: str | None = Field(default=None, index=True)
    session_id: str | None = Field(default=None, index=True)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), index=True)

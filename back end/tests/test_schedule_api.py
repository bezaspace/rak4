from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.schedule_api import build_schedule_router


class _ScheduleServiceStub:
    def __init__(self) -> None:
        self.today_calls = 0
        self.reports_calls = 0

    def get_today_schedule(self, **_kwargs):
        self.today_calls += 1
        return {"date": "2026-02-22", "timezone": "UTC", "items": [], "timeline": []}

    def list_reports_for_item(self, **kwargs):
        self.reports_calls += 1
        return {
            "scheduleItemId": kwargs["schedule_item_id"],
            "date": "2026-02-22",
            "timezone": "UTC",
            "reports": [],
        }


def test_schedule_today_endpoint() -> None:
    service = _ScheduleServiceStub()
    app = FastAPI()
    app.include_router(build_schedule_router(service))
    client = TestClient(app)

    response = client.get("/api/schedule/today", params={"user_id": "patient-1", "timezone": "UTC"})
    assert response.status_code == 200
    assert response.json()["date"] == "2026-02-22"
    assert service.today_calls == 1


def test_schedule_item_reports_endpoint() -> None:
    service = _ScheduleServiceStub()
    app = FastAPI()
    app.include_router(build_schedule_router(service))
    client = TestClient(app)

    response = client.get("/api/schedule/items/sched_1/reports", params={"user_id": "patient-1"})
    assert response.status_code == 200
    assert response.json()["scheduleItemId"] == "sched_1"
    assert service.reports_calls == 1

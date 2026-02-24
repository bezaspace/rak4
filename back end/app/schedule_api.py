from __future__ import annotations

from fastapi import APIRouter, Query

from app.schedule_service import ScheduleService


def build_schedule_router(schedule_service: ScheduleService) -> APIRouter:
    router = APIRouter(prefix="/api/schedule", tags=["schedule"])

    @router.get("/today")
    async def get_today_schedule(
        user_id: str = Query(..., min_length=1),
        timezone: str | None = Query(default=None),
        date: str | None = Query(default=None),
    ) -> dict[str, object]:
        return schedule_service.get_today_schedule(
            user_id=user_id,
            timezone_name=timezone,
            date_str=date,
        )

    @router.get("/items/{schedule_item_id}/reports")
    async def get_item_reports(
        schedule_item_id: str,
        user_id: str = Query(..., min_length=1),
        timezone: str | None = Query(default=None),
        date: str | None = Query(default=None),
    ) -> dict[str, object]:
        return schedule_service.list_reports_for_item(
            user_id=user_id,
            schedule_item_id=schedule_item_id,
            timezone_name=timezone,
            date_str=date,
        )

    return router

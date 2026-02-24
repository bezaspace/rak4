from __future__ import annotations

from pathlib import Path

from app.booking_state import SessionBookingState
from app.doctor_repository import DoctorRepository
from app.doctor_tools import build_doctor_tools


def _build_tools():
    repo = DoctorRepository.from_json_file(Path("app/data/mock_doctors.json"))
    booking_state = SessionBookingState(repo.list_doctors())
    return repo, build_doctor_tools(repo, booking_state)


def test_publish_recommendations_requires_two_to_three_ids() -> None:
    repo, tools = _build_tools()
    publish_recommendations = tools[1]

    response = publish_recommendations("headache", [repo.list_doctors()[0]["doctorId"]])

    assert response["type"] == "booking_update"
    assert response["status"] == "failed"


def test_booking_requires_confirmation_then_confirms() -> None:
    repo, tools = _build_tools()
    book_doctor_slot = tools[2]
    doctor = repo.list_doctors()[0]
    slot = doctor["slots"][0]

    first = book_doctor_slot(doctor["doctorId"], slot["slotId"], False)
    assert first["type"] == "booking_update"
    assert first["status"] == "needs_confirmation"

    second = book_doctor_slot(doctor["doctorId"], slot["slotId"], True)
    assert second["type"] == "booking_update"
    assert second["status"] == "confirmed"
    assert second["booking"]["slotId"] == slot["slotId"]


def test_publish_recommendations_includes_profile_reasoning() -> None:
    repo, tools = _build_tools()
    publish_recommendations = tools[1]
    doctor_ids = [doctor["doctorId"] for doctor in repo.list_doctors()[:2]]

    class _ToolContextStub:
        state = {
            "app:patient_profile": {
                "conditions": [
                    {"name": "Type 2 diabetes"},
                    {"name": "Hypertension"},
                ]
            },
            "app:biomarker_targets": [
                {"biomarker": "HbA1c", "target": "< 7.0", "unit": "%"},
                {"biomarker": "LDL-C", "target": "< 70", "unit": "mg/dL"},
            ],
        }

    response = publish_recommendations("fatigue", doctor_ids, _ToolContextStub())

    assert response["type"] == "doctor_recommendations"
    assert len(response["doctors"]) == 2
    reason = response["doctors"][0]["matchReason"]
    assert "Aligned with biomarker goals" in reason
    assert "Considers your history of Type 2 diabetes, Hypertension." in reason

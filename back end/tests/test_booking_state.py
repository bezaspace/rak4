from __future__ import annotations

from pathlib import Path

from app.booking_state import SessionBookingState
from app.doctor_repository import DoctorRepository


def test_booking_marks_slot_unavailable() -> None:
    repo = DoctorRepository.from_json_file(Path("app/data/mock_doctors.json"))
    doctor = repo.list_doctors()[0]
    slot_id = doctor["slots"][0]["slotId"]

    state = SessionBookingState(repo.list_doctors())
    assert state.is_slot_available(doctor["doctorId"], slot_id)

    success, booking = state.try_book(doctor=doctor, slot_id=slot_id)
    assert success
    assert booking is not None
    assert not state.is_slot_available(doctor["doctorId"], slot_id)


def test_booking_state_is_session_scoped() -> None:
    repo = DoctorRepository.from_json_file(Path("app/data/mock_doctors.json"))
    doctor = repo.list_doctors()[0]
    slot_id = doctor["slots"][0]["slotId"]

    state_a = SessionBookingState(repo.list_doctors())
    state_b = SessionBookingState(repo.list_doctors())

    success, _ = state_a.try_book(doctor=doctor, slot_id=slot_id)
    assert success
    assert not state_a.is_slot_available(doctor["doctorId"], slot_id)
    assert state_b.is_slot_available(doctor["doctorId"], slot_id)

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


class SessionBookingState:
    def __init__(self, doctors: list[dict]) -> None:
        self._slot_index: dict[tuple[str, str], dict] = {}
        self._booked_slots: set[tuple[str, str]] = set()
        self._bookings: list[dict] = []

        for doctor in doctors:
            doctor_id = doctor["doctorId"]
            for slot in doctor["slots"]:
                key = (doctor_id, slot["slotId"])
                self._slot_index[key] = dict(slot)

    def is_slot_available(self, doctor_id: str, slot_id: str) -> bool:
        key = (doctor_id, slot_id)
        if key not in self._slot_index:
            return False
        return key not in self._booked_slots

    def with_availability(self, doctors: list[dict]) -> list[dict]:
        result: list[dict] = []
        for doctor in doctors:
            doctor_copy = {k: v for k, v in doctor.items() if k != "slots"}
            doctor_copy["slots"] = []
            for slot in doctor["slots"]:
                slot_copy = dict(slot)
                slot_copy["isAvailable"] = self.is_slot_available(doctor["doctorId"], slot["slotId"])
                doctor_copy["slots"].append(slot_copy)
            result.append(doctor_copy)
        return result

    def try_book(self, doctor: dict, slot_id: str) -> tuple[bool, dict | None]:
        doctor_id = doctor["doctorId"]
        key = (doctor_id, slot_id)
        slot = self._slot_index.get(key)
        if not slot or key in self._booked_slots:
            return False, None

        self._booked_slots.add(key)
        booking = {
            "bookingId": f"bk_{uuid4().hex[:10]}",
            "doctorId": doctor_id,
            "doctorName": doctor["name"],
            "slotId": slot_id,
            "startIso": slot["startIso"],
            "displayLabel": slot["displayLabel"],
            "timezone": slot["timezone"],
            "createdAtIso": datetime.now(UTC).isoformat(),
        }
        self._bookings.append(booking)
        return True, booking

    def list_bookings(self) -> list[dict]:
        return list(self._bookings)

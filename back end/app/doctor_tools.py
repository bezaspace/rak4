from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from app.booking_state import SessionBookingState
from app.doctor_repository import DoctorRepository


def build_doctor_tools(
    doctor_repository: DoctorRepository, booking_state: SessionBookingState
) -> list[Callable[..., dict[str, Any]]]:
    def get_doctor_catalog() -> dict[str, Any]:
        """
        Fetches doctors and current slot availability for this conversation.
        Call this before recommending doctors based on symptoms.
        """
        doctors = booking_state.with_availability(doctor_repository.list_doctors())
        return {
            "type": "doctor_catalog",
            "timezone": doctor_repository.timezone,
            "doctors": doctors,
        }

    def publish_recommendations(symptoms_summary: str, doctor_ids: list[str]) -> dict[str, Any]:
        """
        Publishes exactly 2-3 doctor recommendations to the chat UI.
        Use doctor_ids that come from get_doctor_catalog.
        """
        summary = str(symptoms_summary).strip()
        selected_ids = [str(doctor_id).strip() for doctor_id in doctor_ids if str(doctor_id).strip()]
        unique_ids = list(dict.fromkeys(selected_ids))
        if len(unique_ids) < 2 or len(unique_ids) > 3:
            return {
                "type": "booking_update",
                "status": "failed",
                "message": "Recommendation publishing failed: provide exactly 2 or 3 unique doctor IDs.",
            }

        doctors: list[dict[str, Any]] = []
        for doctor_id in unique_ids:
            if not doctor_repository.has_doctor(doctor_id):
                return {
                    "type": "booking_update",
                    "status": "failed",
                    "message": f"Recommendation publishing failed: unknown doctor ID '{doctor_id}'.",
                }

            doctor = doctor_repository.get_doctor(doctor_id)
            doctor_with_availability = booking_state.with_availability([doctor])[0]
            doctors.append(
                {
                    "doctorId": doctor_with_availability["doctorId"],
                    "name": doctor_with_availability["name"],
                    "specialty": doctor_with_availability["specialty"],
                    "experienceYears": doctor_with_availability["experienceYears"],
                    "languages": doctor_with_availability.get("languages", []),
                    "matchReason": (
                        f"Potential fit based on your symptoms: {summary or 'current concerns'}."
                    ),
                    "slots": doctor_with_availability["slots"],
                }
            )

        return {
            "type": "doctor_recommendations",
            "requestId": f"rec_{uuid4().hex[:10]}",
            "symptomsSummary": summary or "General symptom discussion",
            "doctors": doctors,
        }

    def book_doctor_slot(doctor_id: str, slot_id: str, user_confirmation: bool = False) -> dict[str, Any]:
        """
        Books an available doctor slot after user confirmation.
        Set user_confirmation=true only when the user explicitly confirms.
        """
        normalized_doctor_id = str(doctor_id).strip()
        normalized_slot_id = str(slot_id).strip()
        if not normalized_doctor_id or not normalized_slot_id:
            return {
                "type": "booking_update",
                "status": "failed",
                "message": "Booking failed: doctor ID and slot ID are required.",
            }

        if not doctor_repository.has_doctor(normalized_doctor_id):
            return {
                "type": "booking_update",
                "status": "failed",
                "message": f"Booking failed: unknown doctor ID '{normalized_doctor_id}'.",
            }

        doctor = doctor_repository.get_doctor(normalized_doctor_id)
        slot_ids = {slot["slotId"] for slot in doctor.get("slots", [])}
        if normalized_slot_id not in slot_ids:
            return {
                "type": "booking_update",
                "status": "failed",
                "message": (
                    f"Booking failed: slot '{normalized_slot_id}' does not belong to "
                    f"{doctor['name']}."
                ),
            }

        if not user_confirmation:
            return {
                "type": "booking_update",
                "status": "needs_confirmation",
                "message": (
                    f"Please confirm booking for {doctor['name']} at slot "
                    f"'{normalized_slot_id}'."
                ),
            }

        if not booking_state.is_slot_available(normalized_doctor_id, normalized_slot_id):
            return {
                "type": "booking_update",
                "status": "unavailable",
                "message": (
                    f"That slot is no longer available for {doctor['name']}. "
                    "Please choose another time."
                ),
            }

        success, booking = booking_state.try_book(doctor=doctor, slot_id=normalized_slot_id)
        if not success or booking is None:
            return {
                "type": "booking_update",
                "status": "failed",
                "message": "Booking failed unexpectedly. Please try another slot.",
            }

        return {
            "type": "booking_update",
            "status": "confirmed",
            "booking": booking,
            "message": (
                f"Booked {booking['doctorName']} on {booking['displayLabel']} "
                f"({booking['timezone']})."
            ),
        }

    return [get_doctor_catalog, publish_recommendations, book_doctor_slot]

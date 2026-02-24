from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from google.adk.tools import ToolContext

from app.booking_state import SessionBookingState
from app.doctor_repository import DoctorRepository
from app.patient_profile_service import BIOMARKER_TARGETS_STATE_KEY
from app.patient_profile_service import PATIENT_PROFILE_STATE_KEY


def build_doctor_tools(
    doctor_repository: DoctorRepository, booking_state: SessionBookingState
) -> list[Callable[..., dict[str, Any]]]:
    def _extract_profile_context(tool_context: ToolContext | None) -> tuple[list[str], list[str]]:
        if tool_context is None:
            return [], []

        raw_targets = tool_context.state.get(BIOMARKER_TARGETS_STATE_KEY, [])
        raw_profile = tool_context.state.get(PATIENT_PROFILE_STATE_KEY, {})
        if not isinstance(raw_targets, list):
            raw_targets = []
        if not isinstance(raw_profile, dict):
            raw_profile = {}

        biomarker_labels: list[str] = []
        for target in raw_targets:
            if not isinstance(target, dict):
                continue
            biomarker = str(target.get("biomarker", "")).strip()
            target_value = str(target.get("target", "")).strip()
            unit = str(target.get("unit", "")).strip()
            if not biomarker:
                continue
            label = biomarker
            if target_value:
                label = f"{label} ({target_value}{f' {unit}' if unit else ''})"
            biomarker_labels.append(label)

        conditions: list[str] = []
        for condition in raw_profile.get("conditions", []) or []:
            if not isinstance(condition, dict):
                continue
            name = str(condition.get("name", "")).strip()
            if name:
                conditions.append(name)

        return biomarker_labels[:3], conditions[:2]

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

    def publish_recommendations(
        symptoms_summary: str,
        doctor_ids: list[str],
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """
        Publishes exactly 2-3 doctor recommendations to the chat UI.
        Use doctor_ids that come from get_doctor_catalog.
        """
        summary = str(symptoms_summary).strip()
        biomarker_targets, conditions = _extract_profile_context(tool_context)
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
            reason_parts = [
                f"Potential fit based on your symptoms: {summary or 'current concerns'}.",
            ]
            if biomarker_targets:
                reason_parts.append(f"Aligned with biomarker goals: {', '.join(biomarker_targets)}.")
            if conditions:
                reason_parts.append(f"Considers your history of {', '.join(conditions)}.")
            doctors.append(
                {
                    "doctorId": doctor_with_availability["doctorId"],
                    "name": doctor_with_availability["name"],
                    "specialty": doctor_with_availability["specialty"],
                    "experienceYears": doctor_with_availability["experienceYears"],
                    "languages": doctor_with_availability.get("languages", []),
                    "matchReason": " ".join(reason_parts),
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

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class DoctorRepository:
    def __init__(self, timezone: str, doctors: list[dict[str, Any]]) -> None:
        self._timezone = timezone
        self._doctors = doctors
        self._doctor_by_id = {doctor["doctorId"]: doctor for doctor in doctors}

    @classmethod
    def from_json_file(cls, json_path: Path) -> "DoctorRepository":
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        timezone = str(raw.get("timezone", "UTC")).strip() or "UTC"
        doctors = raw.get("doctors")
        if not isinstance(doctors, list) or not doctors:
            raise ValueError("mock_doctors.json must contain a non-empty doctors list.")

        for doctor in doctors:
            cls._validate_doctor(doctor)
        return cls(timezone=timezone, doctors=doctors)

    @property
    def timezone(self) -> str:
        return self._timezone

    def has_doctor(self, doctor_id: str) -> bool:
        return doctor_id in self._doctor_by_id

    def get_doctor(self, doctor_id: str) -> dict[str, Any]:
        if doctor_id not in self._doctor_by_id:
            raise KeyError(f"Unknown doctor id: {doctor_id}")
        return copy.deepcopy(self._doctor_by_id[doctor_id])

    def list_doctors(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._doctors)

    @staticmethod
    def _validate_doctor(doctor: Any) -> None:
        if not isinstance(doctor, dict):
            raise ValueError("Each doctor entry must be a JSON object.")
        for key in ("doctorId", "name", "specialty", "experienceYears", "languages", "slots"):
            if key not in doctor:
                raise ValueError(f"Doctor entry missing required key: {key}")

        if not isinstance(doctor["slots"], list) or not doctor["slots"]:
            raise ValueError(f"Doctor '{doctor.get('doctorId', 'unknown')}' must define at least one slot.")

        for slot in doctor["slots"]:
            if not isinstance(slot, dict):
                raise ValueError("Each slot entry must be a JSON object.")
            for key in ("slotId", "startIso", "displayLabel", "timezone"):
                if key not in slot:
                    raise ValueError(f"Slot entry missing required key: {key}")

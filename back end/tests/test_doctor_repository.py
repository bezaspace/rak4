from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.doctor_repository import DoctorRepository


def test_repository_loads_mock_data() -> None:
    repo = DoctorRepository.from_json_file(Path("app/data/mock_doctors.json"))
    doctors = repo.list_doctors()

    assert repo.timezone == "America/Los_Angeles"
    assert len(doctors) >= 2
    assert "doctorId" in doctors[0]
    assert "slots" in doctors[0]
    assert "startIso" in doctors[0]["slots"][0]
    assert "displayLabel" in doctors[0]["slots"][0]


def test_repository_rejects_invalid_doctor_file(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"timezone": "UTC", "doctors": [{"doctorId": "x"}]}), encoding="utf-8")

    with pytest.raises(ValueError):
        DoctorRepository.from_json_file(bad_path)

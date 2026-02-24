from __future__ import annotations

from pathlib import Path

from app.patient_profile_repository import PatientProfileRepository


def _write_seed(seed_path: Path, *, malformed_biomarkers: bool = False) -> None:
    biomarker_payload = (
        '\'[{"biomarker":"HbA1c","target":"< 7.0","unit":"%"}]\''
        if not malformed_biomarkers
        else "'not-json'"
    )
    seed_path.write_text(
        "\n".join(
            [
                "CREATE TABLE IF NOT EXISTS patient_profiles (",
                "  user_id TEXT PRIMARY KEY,",
                "  full_name TEXT,",
                "  age INTEGER,",
                "  sex TEXT,",
                "  conditions_json TEXT NOT NULL,",
                "  treatments_json TEXT NOT NULL,",
                "  allergies_json TEXT NOT NULL,",
                "  contraindications_json TEXT NOT NULL,",
                "  family_history_json TEXT NOT NULL,",
                "  biomarker_targets_json TEXT NOT NULL,",
                "  notes TEXT,",
                "  updated_at TEXT NOT NULL",
                ");",
                "INSERT OR REPLACE INTO patient_profiles (",
                "  user_id, full_name, age, sex, conditions_json, treatments_json, allergies_json,",
                "  contraindications_json, family_history_json, biomarker_targets_json, notes, updated_at",
                ") VALUES (",
                "  'patient-1', 'Demo', 42, 'female',",
                "  '[{\"name\":\"Type 2 diabetes\",\"status\":\"active\"}]',",
                "  '[{\"name\":\"Metformin\",\"status\":\"ongoing\"}]',",
                "  '[\"Penicillin\"]',",
                "  '[\"Systemic steroids\"]',",
                "  '[\"Family history of CVD\"]',",
                f"  {biomarker_payload},",
                "  'note',",
                "  '2026-02-20T10:00:00Z'",
                ");",
            ]
        ),
        encoding="utf-8",
    )


def test_get_by_user_id_returns_profile(tmp_path: Path) -> None:
    seed_path = tmp_path / "seed.sql"
    db_path = tmp_path / "profiles.db"
    _write_seed(seed_path)

    repo = PatientProfileRepository(
        db_url=f"sqlite:///{db_path}",
        seed_sql_path=seed_path,
    )
    repo.initialize()

    profile = repo.get_by_user_id("patient-1")

    assert profile is not None
    assert profile.user_id == "patient-1"
    assert profile.conditions[0].name == "Type 2 diabetes"
    assert profile.biomarker_targets[0].biomarker == "HbA1c"


def test_get_by_user_id_returns_none_for_invalid_shape(tmp_path: Path) -> None:
    seed_path = tmp_path / "seed.sql"
    db_path = tmp_path / "profiles.db"
    _write_seed(seed_path, malformed_biomarkers=True)

    repo = PatientProfileRepository(
        db_url=f"sqlite:///{db_path}",
        seed_sql_path=seed_path,
    )
    repo.initialize()

    profile = repo.get_by_user_id("patient-1")

    assert profile is None

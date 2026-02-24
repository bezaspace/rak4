from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Field, SQLModel


class ConditionRecord(BaseModel):
    name: str
    status: str | None = None


class TreatmentRecord(BaseModel):
    name: str
    status: str | None = None
    dosage: str | None = None


class BiomarkerTarget(BaseModel):
    biomarker: str
    target: str
    unit: str | None = None
    rationale: str | None = None


class PatientProfile(BaseModel):
    user_id: str
    full_name: str | None = None
    age: int | None = None
    sex: str | None = None
    conditions: list[ConditionRecord] = PydanticField(default_factory=list)
    treatments: list[TreatmentRecord] = PydanticField(default_factory=list)
    allergies: list[str] = PydanticField(default_factory=list)
    contraindications: list[str] = PydanticField(default_factory=list)
    family_history: list[str] = PydanticField(default_factory=list)
    biomarker_targets: list[BiomarkerTarget] = PydanticField(default_factory=list)
    notes: str | None = None
    updated_at: str | None = None


class PatientProfileRow(SQLModel, table=True):
    __tablename__ = "patient_profiles"

    user_id: str = Field(primary_key=True, index=True)
    full_name: str | None = Field(default=None)
    age: int | None = Field(default=None)
    sex: str | None = Field(default=None)
    conditions_json: str = Field(default="[]")
    treatments_json: str = Field(default="[]")
    allergies_json: str = Field(default="[]")
    contraindications_json: str = Field(default="[]")
    family_history_json: str = Field(default="[]")
    biomarker_targets_json: str = Field(default="[]")
    notes: str | None = Field(default=None)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

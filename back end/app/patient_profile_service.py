from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.patient_profile_models import BiomarkerTarget
from app.patient_profile_models import PatientProfile
from app.patient_profile_repository import PatientProfileRepository

PATIENT_PROFILE_STATE_KEY = "app:patient_profile"
BIOMARKER_TARGETS_STATE_KEY = "app:biomarker_targets"
PROFILE_AVAILABLE_STATE_KEY = "app:profile_available"
PROFILE_SUMMARY_STATE_KEY = "app:profile_summary"


@dataclass
class ProfileContextResult:
    state: dict[str, Any]
    profile_summary: str | None
    loaded: bool
    source: str
    message: str


class PatientProfileService:
    def __init__(self, repository: PatientProfileRepository) -> None:
        self._repository = repository

    def load_profile_context(self, user_id: str) -> ProfileContextResult:
        profile = self._repository.get_by_user_id(user_id)
        if profile is None:
            return ProfileContextResult(
                state={
                    PROFILE_AVAILABLE_STATE_KEY: False,
                    PATIENT_PROFILE_STATE_KEY: {},
                    BIOMARKER_TARGETS_STATE_KEY: [],
                    PROFILE_SUMMARY_STATE_KEY: "",
                },
                profile_summary=None,
                loaded=False,
                source="none",
                message="No saved patient profile found. Continuing with general guidance.",
            )

        summary = self._build_summary(profile)
        return ProfileContextResult(
            state={
                PROFILE_AVAILABLE_STATE_KEY: True,
                PATIENT_PROFILE_STATE_KEY: profile.model_dump(mode="json"),
                BIOMARKER_TARGETS_STATE_KEY: [target.model_dump(mode="json") for target in profile.biomarker_targets],
                PROFILE_SUMMARY_STATE_KEY: summary,
            },
            profile_summary=summary,
            loaded=True,
            source="db",
            message="Loaded saved patient profile for personalized guidance.",
        )

    @staticmethod
    def _build_summary(profile: PatientProfile) -> str:
        condition_names = [condition.name for condition in profile.conditions if condition.name][:3]
        treatment_names = [treatment.name for treatment in profile.treatments if treatment.name][:3]
        biomarker_labels = [PatientProfileService._format_biomarker_target(target) for target in profile.biomarker_targets][:4]

        parts: list[str] = []
        if profile.full_name:
            parts.append(f"Patient: {profile.full_name}.")
        if condition_names:
            parts.append(f"Known conditions: {', '.join(condition_names)}.")
        if treatment_names:
            parts.append(f"Current or prior treatments: {', '.join(treatment_names)}.")
        if biomarker_labels:
            parts.append(f"Biomarker targets: {', '.join(biomarker_labels)}.")
        if profile.allergies:
            parts.append(f"Allergies: {', '.join(profile.allergies[:3])}.")
        if profile.contraindications:
            parts.append(f"Contraindications: {', '.join(profile.contraindications[:3])}.")
        if profile.notes:
            parts.append(f"Clinician notes: {profile.notes}.")

        return " ".join(parts)

    @staticmethod
    def _format_biomarker_target(target: BiomarkerTarget) -> str:
        unit = f" {target.unit}" if target.unit else ""
        return f"{target.biomarker} ({target.target}{unit})"

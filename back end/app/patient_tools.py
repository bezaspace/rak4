from __future__ import annotations

from typing import Any, Callable

from google.adk.tools import ToolContext

from app.patient_profile_service import BIOMARKER_TARGETS_STATE_KEY
from app.patient_profile_service import PATIENT_PROFILE_STATE_KEY
from app.patient_profile_service import PROFILE_AVAILABLE_STATE_KEY
from app.patient_profile_service import PROFILE_SUMMARY_STATE_KEY


def build_patient_tools() -> list[Callable[..., dict[str, Any]]]:
    def get_patient_profile_summary(tool_context: ToolContext) -> dict[str, Any]:
        """
        Returns persisted patient profile context for personalized recommendations.
        Use this when tailoring suggestions to conditions, treatments, and biomarker targets.
        """
        is_available = bool(tool_context.state.get(PROFILE_AVAILABLE_STATE_KEY, False))
        if not is_available:
            return {
                "profileAvailable": False,
                "message": "No saved patient profile is available for this user.",
                "profileSummary": "",
                "biomarkerTargets": [],
            }

        summary = str(tool_context.state.get(PROFILE_SUMMARY_STATE_KEY, "")).strip()
        profile = tool_context.state.get(PATIENT_PROFILE_STATE_KEY, {})
        biomarker_targets = tool_context.state.get(BIOMARKER_TARGETS_STATE_KEY, [])
        if not isinstance(profile, dict):
            profile = {}
        if not isinstance(biomarker_targets, list):
            biomarker_targets = []

        return {
            "profileAvailable": True,
            "profileSummary": summary,
            "biomarkerTargets": biomarker_targets,
            "conditions": profile.get("conditions", []),
            "treatments": profile.get("treatments", []),
            "allergies": profile.get("allergies", []),
            "contraindications": profile.get("contraindications", []),
        }

    return [get_patient_profile_summary]

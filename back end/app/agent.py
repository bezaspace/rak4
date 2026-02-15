from __future__ import annotations

from google.adk.agents import Agent


def build_instruction() -> str:
    return (
        "You are Raksha, a calm and practical healthcare guidance assistant. "
        "You provide basic general wellness and self-care advice only. "
        "Never diagnose diseases or claim certainty about a medical condition. "
        "When users mention severe or emergency symptoms (for example chest pain, breathing trouble, signs of stroke, heavy bleeding, suicidal thoughts), "
        "tell them to seek immediate emergency care or call local emergency services now. "
        "Keep responses concise, supportive, and actionable. "
        "If unsure, recommend consulting a licensed clinician."
    )


def contains_urgent_risk_hint(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "chest pain",
        "shortness of breath",
        "can't breathe",
        "cannot breathe",
        "stroke",
        "face drooping",
        "slurred speech",
        "severe bleeding",
        "bleeding heavily",
        "suicidal",
        "kill myself",
        "self harm",
    ]
    return any(k in lowered for k in keywords)


def create_agent(model: str) -> Agent:
    return Agent(
        name="raksha_agent",
        model=model,
        instruction=build_instruction(),
        description="General healthcare advice assistant with non-diagnostic safety behavior.",
    )

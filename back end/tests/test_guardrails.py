from app.agent import build_instruction


def test_instruction_includes_emergency_guidance() -> None:
    instruction = build_instruction().lower()
    assert "seek immediate emergency care" in instruction
    assert "emergency services" in instruction


def test_instruction_preserves_non_diagnostic_safety() -> None:
    instruction = build_instruction().lower()
    assert "never diagnose" in instruction
    assert "general wellness and self-care advice only" in instruction


def test_instruction_requires_true_save_before_logging_confirmation() -> None:
    instruction = build_instruction().lower()
    assert "only tell the user that adherence was logged if save_adherence_report returns saved=true" in instruction

from app.agent import contains_urgent_risk_hint


def test_urgent_keywords_detected() -> None:
    assert contains_urgent_risk_hint("I have crushing chest pain")
    assert contains_urgent_risk_hint("My friend wants to kill myself")


def test_non_urgent_message_not_flagged() -> None:
    assert not contains_urgent_risk_hint("I have mild headache after bad sleep")

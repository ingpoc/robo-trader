from src.web.routes.claude_transparency import (
    _empty_daily_evaluation,
    _empty_execution_transparency,
)


def test_empty_execution_transparency_is_blocked_not_fake_success():
    payload = _empty_execution_transparency(error="store unavailable", status="blocked")

    assert payload["status"] == "blocked"
    assert payload["risk_compliance"] == 0.0
    assert payload["recent_executions"] == []
    assert payload["error"] == "store unavailable"


def test_empty_daily_evaluation_returns_no_mock_entries():
    payload = _empty_daily_evaluation(error="not implemented", status="blocked")

    assert payload["status"] == "blocked"
    assert payload["evaluations"] == []
    assert payload["total_evaluations"] == 0
    assert payload["avg_confidence"] == 0.0
    assert payload["error"] == "not implemented"

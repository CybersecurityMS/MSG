from unittest.mock import MagicMock

import anthropic

from agent.models import NormalizedAlert
from agent.tools.investigate_alert import LLMVerdict, investigate_alert

ALERT = NormalizedAlert(
    alert_id="evt-1001",
    source_file="sample_alerts.csv",
    timestamp="2026-08-30T10:15:00Z",
    severity_raw="High",
    source_ip="10.0.0.5",
    dest_ip="10.0.0.10",
    rule_name="Brute Force Login Attempt",
    description="Multiple failed logins from 10.0.0.5",
    raw_row={"EventID": "evt-1001"},
)


def test_investigate_alert_returns_analysis_on_success():
    client = MagicMock()
    client.messages.parse.return_value = MagicMock(
        parsed_output=LLMVerdict(
            score=87.5,
            alert_level=3,
            summary="Multiple failed logins indicate a likely brute-force attempt.",
            recommended_action="Lock the source IP and force a password reset.",
        )
    )

    result = investigate_alert(client, "claude-opus-5", ALERT)

    assert result.alert_id == "evt-1001"
    assert result.score == 87.5
    assert result.alert_level == 3
    assert result.error is None
    client.messages.parse.assert_called_once()


def test_investigate_alert_falls_back_on_non_retryable_error():
    client = MagicMock()
    client.messages.parse.side_effect = anthropic.BadRequestError(
        message="bad request", response=MagicMock(status_code=400, request=MagicMock()), body=None
    )

    result = investigate_alert(client, "claude-opus-5", ALERT)

    assert result.alert_id == "evt-1001"
    assert result.alert_level == 3
    assert result.error is not None
    assert "BadRequestError" in result.error
    client.messages.parse.assert_called_once()

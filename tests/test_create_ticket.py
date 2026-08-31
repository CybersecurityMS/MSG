from pathlib import Path

from agent.models import AlertAnalysis
from agent.tools.create_ticket import create_ticket

LOW = AlertAnalysis(
    alert_id="evt-2001",
    source_file="sample_alerts.csv",
    score=8.0,
    alert_level=1,
    summary="Unusual DNS query volume, consistent with a scheduled job.",
    recommended_action="No action needed, monitor for recurrence.",
    model_used="claude-opus-5",
)

MEDIUM = LOW.model_copy(update={"alert_id": "evt-2002", "alert_level": 2, "score": 45.0})
HIGH = LOW.model_copy(update={"alert_id": "evt-2003", "alert_level": 3, "score": 90.0})


def test_creates_ticket_for_low_level_alert(tmp_path: Path):
    ticket_path = create_ticket(LOW, tmp_path)

    assert ticket_path == tmp_path / "TCKT-evt-2001.txt"
    assert ticket_path.exists()

    content = ticket_path.read_text(encoding="utf-8")
    assert "evt-2001" in content
    assert LOW.summary in content
    assert LOW.recommended_action in content
    assert "SERVICENOW TICKET" in content


def test_no_ticket_for_medium_or_high_level_alerts(tmp_path: Path):
    assert create_ticket(MEDIUM, tmp_path) is None
    assert create_ticket(HIGH, tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_sanitizes_unsafe_characters_in_ticket_filename(tmp_path: Path):
    unsafe = LOW.model_copy(update={"alert_id": "evt/../2001:weird*id"})

    ticket_path = create_ticket(unsafe, tmp_path)

    assert ticket_path.parent == tmp_path
    assert "/" not in ticket_path.name
    assert "\\" not in ticket_path.name
    assert ticket_path.exists()

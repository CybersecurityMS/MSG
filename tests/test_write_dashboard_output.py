import json
from pathlib import Path

from agent.models import AlertAnalysis
from agent.tools.write_dashboard_output import write_dashboard_output

ANALYSIS = AlertAnalysis(
    alert_id="evt-1001",
    source_file="sample_alerts.csv",
    score=87.5,
    alert_level=3,
    summary="Likely brute-force attempt.",
    recommended_action="Lock the source IP.",
    model_used="claude-opus-5",
)


def test_writes_json_file_named_after_alert_id(tmp_path: Path):
    out_path = write_dashboard_output(ANALYSIS, tmp_path)

    assert out_path == tmp_path / "evt-1001.json"
    assert out_path.exists()

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["alert_id"] == "evt-1001"
    assert data["alert_level"] == 3
    assert data["score"] == 87.5


def test_sanitizes_unsafe_characters_in_alert_id(tmp_path: Path):
    unsafe = ANALYSIS.model_copy(update={"alert_id": "evt/../1001:weird*id"})

    out_path = write_dashboard_output(unsafe, tmp_path)

    # No path separators survive, so the file can only ever land inside tmp_path -
    # a stray ".." substring inside a single filename component is harmless.
    assert out_path.parent == tmp_path
    assert "/" not in out_path.name
    assert "\\" not in out_path.name
    assert out_path.exists()

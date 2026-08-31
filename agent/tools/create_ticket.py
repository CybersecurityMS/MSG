"""Tool 5: open a ticket for low-severity alerts.

There is no ServiceNow instance to call yet, so this writes a plain-text ticket
file to data/tickets/ instead. The payload is built as a dict shaped like a
ServiceNow incident (short_description, description, urgency, category, ...)
specifically so that swapping the text-file writer for a real ServiceNow REST
call later is a small, isolated change - build_ticket_payload stays the same,
only _write_ticket_text (or its caller) changes.
"""

from datetime import datetime, timezone
from pathlib import Path

from agent.models import AlertAnalysis

LEVEL_LABELS = {1: "Low", 2: "Medium", 3: "High"}

# Alert level this tool opens a ticket for. SIEM alerts are open to change what
# gets auto-ticketed vs. handled through other escalation paths - keep this the
# single place that decision is made.
TICKETED_ALERT_LEVEL = 1


def build_ticket_payload(analysis: AlertAnalysis) -> dict:
    """Shape the ticket fields the way a ServiceNow incident would expect them."""
    return {
        "short_description": f"[SOC AI] {LEVEL_LABELS[analysis.alert_level]} alert - {analysis.alert_id}",
        "description": analysis.summary,
        "next_action": analysis.recommended_action,
        "urgency": LEVEL_LABELS[analysis.alert_level],
        "category": "Security Alert Triage",
        "alert_id": analysis.alert_id,
        "source_file": analysis.source_file,
        "score": analysis.score,
        "alert_level": analysis.alert_level,
        "analyzed_at": analysis.analyzed_at.isoformat(),
        "model_used": analysis.model_used,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }


def _render_ticket_text(payload: dict) -> str:
    return (
        "=====================================================\n"
        "SERVICENOW TICKET (simulated - no ServiceNow instance configured yet)\n"
        "=====================================================\n"
        f"Short Description: {payload['short_description']}\n"
        f"Urgency:           {payload['urgency']}\n"
        f"Category:          {payload['category']}\n"
        f"Opened At:         {payload['opened_at']}\n"
        "-----------------------------------------------------\n"
        f"Alert ID:          {payload['alert_id']}\n"
        f"Source File:       {payload['source_file']}\n"
        f"Triage Score:      {payload['score']}\n"
        f"Analyzed At:       {payload['analyzed_at']}\n"
        f"Model Used:        {payload['model_used']}\n"
        "-----------------------------------------------------\n"
        "Findings:\n"
        f"{payload['description']}\n"
        "\n"
        "Recommended Next Action:\n"
        f"{payload['next_action']}\n"
        "=====================================================\n"
    )


def create_ticket(analysis: AlertAnalysis, tickets_dir: Path) -> Path | None:
    """Write a ticket file for `analysis` if it's low-severity. Returns the path, or None."""
    if analysis.alert_level != TICKETED_ALERT_LEVEL:
        return None

    payload = build_ticket_payload(analysis)
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in analysis.alert_id)
    out_path = tickets_dir / f"TCKT-{safe_name}.txt"
    out_path.write_text(_render_ticket_text(payload), encoding="utf-8")
    return out_path

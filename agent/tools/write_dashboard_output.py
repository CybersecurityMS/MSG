"""Tool 4: write an analyzed alert to the output folder the dashboard reads from."""

from pathlib import Path

from agent.models import AlertAnalysis


def write_dashboard_output(analysis: AlertAnalysis, output_dir: Path) -> Path:
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in analysis.alert_id)
    out_path = output_dir / f"{safe_name}.json"
    out_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    return out_path

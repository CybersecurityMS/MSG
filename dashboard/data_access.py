"""Reads and aggregates the analyzed-alert JSON files the agent writes."""

import json
import logging
from pathlib import Path

from agent.config import settings
from agent.models import AlertAnalysis

logger = logging.getLogger(__name__)


def load_alerts() -> list[AlertAnalysis]:
    output_dir = settings.resolved_output_dir()
    alerts: list[AlertAnalysis] = []

    for path in output_dir.glob("*.json"):
        try:
            alerts.append(AlertAnalysis.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:  # noqa: BLE001 - one bad file must not break the dashboard
            logger.exception("Failed to load %s", path)

    alerts.sort(key=lambda a: a.analyzed_at, reverse=True)
    return alerts


def compute_stats(alerts: list[AlertAnalysis]) -> dict:
    level_counts = {1: 0, 2: 0, 3: 0}
    total_score = 0.0

    for alert in alerts:
        level_counts[alert.alert_level] += 1
        total_score += alert.score

    return {
        "total": len(alerts),
        "level_counts": level_counts,
        "average_score": round(total_score / len(alerts), 2) if alerts else 0.0,
        "error_count": sum(1 for a in alerts if a.error),
    }

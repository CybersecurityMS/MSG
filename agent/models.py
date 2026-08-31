from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class NormalizedAlert(BaseModel):
    """One SIEM alert row, normalized from an arbitrary CSV schema."""

    alert_id: str
    source_file: str
    timestamp: Optional[str] = None
    severity_raw: Optional[str] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    rule_name: Optional[str] = None
    description: Optional[str] = None
    raw_row: dict = Field(default_factory=dict)


class AlertAnalysis(BaseModel):
    """The LLM's triage verdict for one alert, written out for the dashboard."""

    model_config = ConfigDict(protected_namespaces=())

    alert_id: str
    source_file: str
    score: float = Field(ge=0, le=100)
    alert_level: Literal[1, 2, 3]
    summary: str
    recommended_action: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str
    error: Optional[str] = None

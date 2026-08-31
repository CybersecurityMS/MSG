from typing import TypedDict

from agent.models import AlertAnalysis, NormalizedAlert


class AgentState(TypedDict):
    files: list[str]
    alerts: list[NormalizedAlert]
    analyzed: list[AlertAnalysis]
    tickets: list[str]
    errors: list[str]

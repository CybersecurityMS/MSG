"""LangGraph pipeline wiring the 5 SOC triage tools into one deterministic graph.

This is a fixed pipeline (fetch -> parse -> investigate -> ticket -> write), not
a ReAct-style agent where the LLM picks which tool to call - alert triage needs
to be auditable and reproducible on every run. The LLM's only job is the one
step that needs judgement: scoring/leveling each alert in `investigate_alerts`.
"""

import logging

import anthropic
from langgraph.graph import END, StateGraph

from agent.config import settings
from agent.state import AgentState
from agent.tools.create_ticket import create_ticket
from agent.tools.fetch_alert_files import fetch_alert_files
from agent.tools.investigate_alert import investigate_alert
from agent.tools.parse_alert_details import parse_alert_files
from agent.tools.write_dashboard_output import write_dashboard_output

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def fetch_files_node(state: AgentState) -> AgentState:
    files = fetch_alert_files(settings.resolved_incoming_dir())
    logger.info("Found %d new alert file(s)", len(files))
    return {**state, "files": files}


def has_files(state: AgentState) -> str:
    return "parse_files" if state["files"] else "end"


def parse_files_node(state: AgentState) -> AgentState:
    alerts, errors = parse_alert_files(state["files"], settings.resolved_processed_dir())
    logger.info("Parsed %d alert(s) from %d file(s)", len(alerts), len(state["files"]))
    return {**state, "alerts": alerts, "errors": state["errors"] + errors}


def investigate_alerts_node(state: AgentState) -> AgentState:
    analyzed = [investigate_alert(_client, settings.claude_model, alert) for alert in state["alerts"]]
    logger.info("Analyzed %d alert(s)", len(analyzed))
    return {**state, "analyzed": analyzed}


def create_tickets_node(state: AgentState) -> AgentState:
    tickets_dir = settings.resolved_tickets_dir()
    tickets = []
    for analysis in state["analyzed"]:
        ticket_path = create_ticket(analysis, tickets_dir)
        if ticket_path is not None:
            tickets.append(str(ticket_path))
    logger.info("Opened %d ticket(s) for low-severity alerts", len(tickets))
    return {**state, "tickets": tickets}


def write_output_node(state: AgentState) -> AgentState:
    for analysis in state["analyzed"]:
        write_dashboard_output(analysis, settings.resolved_output_dir())
    logger.info("Wrote %d analysis file(s) to %s", len(state["analyzed"]), settings.resolved_output_dir())
    return state


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_files", fetch_files_node)
    graph.add_node("parse_files", parse_files_node)
    graph.add_node("investigate_alerts", investigate_alerts_node)
    graph.add_node("create_tickets", create_tickets_node)
    graph.add_node("write_output", write_output_node)

    graph.set_entry_point("fetch_files")
    graph.add_conditional_edges("fetch_files", has_files, {"parse_files": "parse_files", "end": END})
    graph.add_edge("parse_files", "investigate_alerts")
    graph.add_edge("investigate_alerts", "create_tickets")
    graph.add_edge("create_tickets", "write_output")
    graph.add_edge("write_output", END)

    return graph.compile()


def run_once() -> AgentState:
    app = build_graph()
    initial_state: AgentState = {"files": [], "alerts": [], "analyzed": [], "tickets": [], "errors": []}
    return app.invoke(initial_state, config={"run_name": "soc-ai-triage-cycle"})

# Architecture

## Overview

Two independent, long-running Python processes share one `data/` folder on disk:

```
                         ┌─────────────────────────────┐
   SIEM export           │      agent process           │
   (every ~5 min)         │  python -m agent.main        │
        │                 │                              │
        ▼                 │  APScheduler tick (5 min)     │
 data/incoming/*.csv ─────┼─▶ LangGraph pipeline:          │
                         │    fetch_files                │
                         │      │ (files found?)           │
                         │      ▼                           │
                         │    parse_files ──▶ data/processed/│  (source CSV moved here)
                         │      │                           │
                         │      ▼                           │
                         │    investigate_alerts            │  (Claude API call per alert)
                         │      │                           │
                         │      ▼                           │
                         │    write_output                  │
                         └──────┼───────────────────────────┘
                                ▼
                    data/output/alerts/<alert_id>.json
                                │
                         ┌──────┼───────────────────────────┐
                         │      ▼        dashboard process   │
                         │  GET /api/alerts, /api/stats       │
                         │  uvicorn dashboard.main:app         │
                         │      │                              │
                         │      ▼                              │
                         │  Jinja2 page + Chart.js (browser)    │
                         └──────────────────────────────────────┘
                                        ▲
                                   SOC analyst
```

## Components

- **`agent/`** — the LangGraph pipeline. See [agent_design.md](agent_design.md) for the state
  schema, node/tool contracts, and error handling.
- **`dashboard/`** — a FastAPI app that reads `data/output/alerts/*.json` on every request (no
  database, no caching layer) and renders a Jinja2 page plus two small JSON endpoints the page
  polls every 30 seconds. See [api_reference.md](api_reference.md).
- **`data/`** — the only thing the two processes share. `incoming/` is the SIEM drop folder and
  doubles as a work queue (a file present there means "not yet parsed"); `processed/` is an
  archive of source CSVs the agent has already read; `output/alerts/` is the agent's output and
  the dashboard's entire data source.

## Why two separate processes instead of one

The agent and the dashboard have different failure modes and different uptime requirements: the
agent can be restarted, backlogged, or briefly down without losing data (files just queue up in
`incoming/`), while the dashboard is user-facing and should stay responsive independent of
whether a triage cycle is currently running. Keeping them as separate processes communicating
only through the filesystem means either one can be restarted, redeployed, or scaled without
touching the other.

## Why LangGraph is used as a fixed pipeline, not a ReAct agent

LangGraph supports both a deterministic `StateGraph` (fixed edges you define) and an agent loop
where an LLM decides which tool to call next. This project uses the former. SOC alert triage
needs to be **auditable and reproducible** — the same alert, run twice, should follow the same
code path and only the LLM's judgement call (the score/level) should vary. Letting the LLM also
choose whether to fetch, parse, or write would add a failure mode (the LLM could hallucinate a
tool call or skip a step) with no corresponding benefit, since the four tools always run in the
same order. The graph in `agent/graph.py` has exactly one decision point that isn't
deterministic: whether `fetch_files` found anything at all.

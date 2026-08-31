# SOC AI

A LangGraph-based SOC alert triage agent plus a FastAPI dashboard. A SIEM drops alert export
CSVs into a watched folder roughly every 5 minutes; the agent parses each alert, sends it to
Claude for triage, and writes a score + alert level (1/2/3) per alert to an output folder. A
separate FastAPI service reads that output folder and renders it as a live dashboard.

Full design rationale lives in `/docs` — read that before making structural changes:
- [docs/architecture.md](docs/architecture.md) — component overview, why two processes, why
  LangGraph is used as a fixed pipeline rather than a ReAct agent
- [docs/agent_design.md](docs/agent_design.md) — state schema, the graph, each tool's contract
- [docs/alert_schema.md](docs/alert_schema.md) — input/intermediate/output data shapes
- [docs/api_reference.md](docs/api_reference.md) — dashboard routes
- [docs/setup.md](docs/setup.md) — environment setup and local run instructions

## Two independent processes

- `python -m agent.main` — the triage agent. Runs forever, polling `data/incoming/` every
  `POLL_INTERVAL_MINUTES` (default 5) via APScheduler.
- `uvicorn dashboard.main:app --reload` — the dashboard. Serves `http://localhost:8000/`.

They only communicate through the `data/` folder — no shared process state, no message queue.

## Directory layout

```
agent/            LangGraph pipeline (config, models, state, graph, scheduler, main)
agent/tools/      the 4 tools: fetch_alert_files, parse_alert_details, investigate_alert, write_dashboard_output
dashboard/        FastAPI app (main, data_access, templates/, static/)
data/incoming/    SIEM drops CSVs here (also the work queue - a file here means "not yet parsed")
data/processed/   source CSVs archived here after parsing
data/output/alerts/  one JSON file per analyzed alert - the dashboard's entire data source
tests/            pytest, one file per tool, no network/API key required
docs/             architecture + design docs, see above
```

## Environment

Copy `.env.example` to `.env` (already done — `.env` exists with placeholders) and set a real
`ANTHROPIC_API_KEY`. See `agent/config.py` for every setting and its default.

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running tests

```powershell
pytest
```

## Conventions

- **Pydantic models for every cross-boundary data shape** (`agent/models.py`): `NormalizedAlert`
  between parsing and the LLM call, `AlertAnalysis` between the LLM call and the dashboard. Don't
  pass raw dicts across tool boundaries.
- **Tools are plain functions**, not LangChain `@tool`-decorated callables — the graph is a fixed
  pipeline, not an LLM-driven agent loop, so there's no tool-calling schema to generate. See
  `docs/architecture.md` for why.
- **A failed LLM call never drops an alert.** `investigate_alert` catches any exception past its
  retry budget and returns an `AlertAnalysis` with `error` set and `alert_level=3` (manual
  review), rather than raising. Keep that behavior when touching this tool — a silent drop is a
  missed alert.
- **The Claude model is configurable** via `CLAUDE_MODEL` (`agent/config.py`), currently
  `claude-opus-5`. Don't hardcode a model string in a tool.
- Alert IDs come from the SIEM (untrusted input) and are used as filenames in
  `write_dashboard_output` — keep the sanitization there if you touch that function.

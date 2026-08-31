# Setup

Commands below are PowerShell, run from the project root (`SOC AI/`).

## 1. Create the virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure `.env`

A `.env` file already exists at the project root with placeholder values. Fill in your real
Anthropic API key:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here   # replace with a real key
CLAUDE_MODEL=claude-opus-5                       # change to any Claude model id if needed

INCOMING_DIR=data/incoming        # point this at your real SIEM export folder if it isn't local
PROCESSED_DIR=data/processed
OUTPUT_DIR=data/output/alerts
TICKETS_DIR=data/tickets

POLL_INTERVAL_MINUTES=5
```

`INCOMING_DIR` / `PROCESSED_DIR` / `OUTPUT_DIR` / `TICKETS_DIR` accept absolute paths too — use
an absolute path if the SIEM writes exports somewhere outside this project (e.g. a network share
or a different drive).

`.env` is git-ignored; `.env.example` is the checked-in template.

## 3. Configure LangSmith tracing (optional but recommended)

Add to `.env`:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=soc-ai
```

Generate the key at [smith.langchain.com](https://smith.langchain.com) → **Settings → API
Keys** → **Service Key** (not a Personal Access Token — a Service Key isn't tied to your user
login, which is what a long-running unattended agent needs).

**If every call 403s despite a valid key:** your key is *org-scoped* rather than tied to one
workspace, and LangSmith rejects org-scoped keys on every authenticated endpoint unless you also
supply the workspace ID. Add:

```
LANGSMITH_WORKSPACE_ID=your_workspace_id_here
```

Find it in the LangSmith URL while viewing your workspace's settings —
`smith.langchain.com/o/<this-id>/settings/apikeys`. There's no error message pointing at this;
a bare `403 Forbidden` on `/sessions` or `/runs/multipart` with an otherwise-valid key is the
tell.

Once configured, view traces (every graph step, plus each Claude call with its full
prompt/response/token usage) under the `soc-ai` project at smith.langchain.com. A failed trace
submission (e.g. wrong key) logs a warning but never blocks or slows down alert triage.

## 4. Run the agent

```powershell
venv\Scripts\Activate.ps1
python -m agent.main
```

This runs one triage cycle immediately, then every `POLL_INTERVAL_MINUTES` thereafter, until you
stop it (Ctrl+C). It logs a one-line summary per cycle (files found, alerts analyzed, errors).

## 5. Run the dashboard

In a second terminal:

```powershell
venv\Scripts\Activate.ps1
uvicorn dashboard.main:app --reload
```

Open `http://localhost:8000/`. The page refreshes itself every 30 seconds — no need to reload
manually as new alerts appear.

## 6. Try it end-to-end

Drop a CSV into `data/incoming/` (see `tests/fixtures/sample_alerts.csv` for the expected
shape — any CSV with recognizable column names works, see
[alert_schema.md](alert_schema.md) for the alias table). Within one poll interval:

- the source CSV moves to `data/processed/`
- one JSON file per alert appears under `data/output/alerts/`
- any alert scored Low additionally gets a ticket under `data/tickets/`
- the dashboard picks it up on its next refresh

## Running tests

```powershell
venv\Scripts\Activate.ps1
pytest
```

Tests cover the five tools in isolation (CSV parsing/column-mapping, file fetch/move, the LLM
call with a mocked Anthropic client, ticket creation, and the output writer) — no network access
or real API key required.

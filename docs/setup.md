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

POLL_INTERVAL_MINUTES=5
```

`INCOMING_DIR` / `PROCESSED_DIR` / `OUTPUT_DIR` accept absolute paths too — use an absolute path
if the SIEM writes exports somewhere outside this project (e.g. a network share or a different
drive).

`.env` is git-ignored; `.env.example` is the checked-in template.

## 3. Run the agent

```powershell
venv\Scripts\Activate.ps1
python -m agent.main
```

This runs one triage cycle immediately, then every `POLL_INTERVAL_MINUTES` thereafter, until you
stop it (Ctrl+C). It logs a one-line summary per cycle (files found, alerts analyzed, errors).

## 4. Run the dashboard

In a second terminal:

```powershell
venv\Scripts\Activate.ps1
uvicorn dashboard.main:app --reload
```

Open `http://localhost:8000/`. The page refreshes itself every 30 seconds — no need to reload
manually as new alerts appear.

## 5. Try it end-to-end

Drop a CSV into `data/incoming/` (see `tests/fixtures/sample_alerts.csv` for the expected
shape — any CSV with recognizable column names works, see
[alert_schema.md](alert_schema.md) for the alias table). Within one poll interval:

- the source CSV moves to `data/processed/`
- one JSON file per alert appears under `data/output/alerts/`
- the dashboard picks it up on its next refresh

## Running tests

```powershell
venv\Scripts\Activate.ps1
pytest
```

Tests cover the four tools in isolation (CSV parsing/column-mapping, file fetch/move, the LLM
call with a mocked Anthropic client, and the output writer) — no network access or real API key
required.

# SOC AI

A LangGraph agent that triages SIEM alerts with Claude, and a FastAPI dashboard to view the
results.

- A SIEM drops alert export CSVs into `data/incoming/` roughly every 5 minutes.
- The agent (`python -m agent.main`) polls that folder, parses each alert, sends it to Claude
  for triage, and writes a JSON verdict (`score`, `alert_level` 1-3, `summary`,
  `recommended_action`) to `data/output/alerts/`.
- The dashboard (`uvicorn dashboard.main:app`) reads that folder and renders a live, auto-
  refreshing view for a SOC analyst.

See [claude.md](claude.md) for the full project map and [docs/](docs/) for architecture and
design details. Quickstart: [docs/setup.md](docs/setup.md).

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in ANTHROPIC_API_KEY

python -m agent.main                        # terminal 1
uvicorn dashboard.main:app --reload         # terminal 2
```

Open `http://localhost:8000/`.

DOC: REMOVED

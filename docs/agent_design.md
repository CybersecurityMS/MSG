# Agent Design

## State (`agent/state.py`)

```python
class AgentState(TypedDict):
    files: list[str]                    # CSV paths found this cycle
    alerts: list[NormalizedAlert]       # parsed rows across all files
    analyzed: list[AlertAnalysis]       # one per alert, after the LLM call
    errors: list[str]                   # non-fatal problems from this cycle
```

One `AgentState` is created fresh for every scheduler tick (`agent/graph.py::run_once`) — nothing
persists between cycles except what's on disk (`data/incoming`, `data/processed`,
`data/output/alerts`).

## Graph (`agent/graph.py`)

```
fetch_files ──(no files)──▶ END
     │
  (files found)
     ▼
parse_files ──▶ investigate_alerts ──▶ write_output ──▶ END
```

| Node | Tool(s) called | Reads | Writes |
|---|---|---|---|
| `fetch_files` | `fetch_alert_files` | `data/incoming/*.csv` | `state.files` |
| `parse_files` | `parse_alert_files` → `parse_alert_file` | files in `state.files` | `state.alerts`, `state.errors`; moves each source CSV to `data/processed/` |
| `investigate_alerts` | `investigate_alert` (once per alert) | `state.alerts` | `state.analyzed` |
| `write_output` | `write_dashboard_output` (once per analysis) | `state.analyzed` | `data/output/alerts/<alert_id>.json` |

The only conditional edge is on `fetch_files`: if no CSVs are waiting, the cycle ends
immediately rather than running an empty parse/investigate/write pass.

## Tool contracts

### Tool 1 — `fetch_alert_files(incoming_dir: Path) -> list[str]`

Lists `*.csv` directly under `incoming_dir` (non-recursive), sorted. No separate "already seen"
ledger is needed — `parse_alert_files` moves each file out of `incoming_dir` once read, so the
incoming folder itself is the queue.

### Tool 2 — `parse_alert_files(file_paths, processed_dir) -> (alerts, errors)`

For each file: read with `pandas.read_csv(path, dtype=str, keep_default_na=False)`, map columns
to a `NormalizedAlert` per row (see [alert_schema.md](alert_schema.md) for the column-alias
table), then move the source file into `processed_dir` — *even if parsing failed*, so a
permanently malformed file doesn't get retried forever. A parse failure on one file is appended
to `errors` and does not stop the other files in the batch from being processed.

Row-level `alert_id`: uses a natural ID column if the CSV has one (`alert_id`, `id`, `event_id`,
`uuid`, ...), otherwise falls back to `<filename-stem>-<row-index>`.

### Tool 3 — `investigate_alert(client, model, alert) -> AlertAnalysis`

Sends the normalized alert's fields (plus the full `raw_row` for context) to Claude via
`client.messages.parse(..., output_format=LLMVerdict)`, which validates the response against a
Pydantic schema (`score`, `alert_level`, `summary`, `recommended_action`) at the API level —
there is no manual JSON parsing or prompt-based coaxing involved.

Retries (via `tenacity`, up to 3 attempts with exponential backoff) only on transient failures:
`RateLimitError`, `APIConnectionError`, `APITimeoutError`, `InternalServerError`. Anything else
(bad API key, invalid request, an unexpected exception) is caught once and turned into a
fallback `AlertAnalysis` with `alert_level=3`, `score=0`, and `error` set to the exception —
the alert still shows up on the dashboard, flagged for a human to look at, instead of silently
disappearing or crashing the whole cycle.

### Tool 4 — `write_dashboard_output(analysis, output_dir) -> Path`

Writes `output_dir/<sanitized alert_id>.json`. The alert ID is sanitized to
`[A-Za-z0-9-_.]` before being used as a filename (SIEM-supplied IDs are untrusted input).
One file per alert — no shared file to lock or a database to run — so the dashboard can just
glob the folder.

## Model configuration

The Claude model is read from `CLAUDE_MODEL` (default `claude-opus-5`) so it can be swapped
(e.g. to a faster/cheaper model for high alert volumes) without a code change — see
`agent/config.py`.

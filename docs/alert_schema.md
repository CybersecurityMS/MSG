# Alert Schemas

## Input: arbitrary SIEM CSV

The agent does not assume a fixed CSV schema. `agent/tools/parse_alert_details.py` normalizes
whatever columns are present using a case/punctuation-insensitive alias table
(`COLUMN_ALIASES`) — e.g. `Source_IP`, `SourceIP`, and `source-ip` all map to the same
normalized field. Columns that don't match any alias are preserved verbatim in `raw_row` (never
dropped), so the LLM and the dashboard always have access to the original data.

| Normalized field | Recognized header variants (case/punctuation-insensitive) |
|---|---|
| `alert_id` | `alert_id`, `id`, `event_id`, `uuid`, `alertid` |
| `timestamp` | `timestamp`, `time`, `date`, `datetime`, `event_time`, `occurred_at`, `alert_time` |
| `severity_raw` | `severity`, `priority`, `level`, `risk`, `criticality` |
| `source_ip` | `source_ip`, `src_ip`, `source`, `src`, `srcip` |
| `dest_ip` | `dest_ip`, `destination_ip`, `dst_ip`, `destination`, `dst`, `dstip` |
| `rule_name` | `rule_name`, `rule`, `signature`, `alert_name`, `event_name`, `title` |
| `description` | `description`, `details`, `message`, `summary`, `info` |

If no `alert_id`-like column exists, one is generated as `<csv filename stem>-<row index>`.

## Intermediate: `NormalizedAlert` (`agent/models.py`)

```python
class NormalizedAlert(BaseModel):
    alert_id: str
    source_file: str
    timestamp: str | None
    severity_raw: str | None
    source_ip: str | None
    dest_ip: str | None
    rule_name: str | None
    description: str | None
    raw_row: dict            # every original CSV column, untouched
```

This is what gets sent to the LLM (`investigate_alert`) — the mapped fields plus `raw_row` for
full context.

## LLM output: `LLMVerdict` (`agent/tools/investigate_alert.py`)

The schema Claude is constrained to via `output_config`/`output_format` (structured outputs —
the API validates this shape, not a prompt instruction):

```python
class LLMVerdict(BaseModel):
    score: float              # 0-100, higher = more urgent/credible
    alert_level: Literal[1, 2, 3]   # 1 = low, 2 = medium, 3 = high
    summary: str               # why it was scored this way
    recommended_action: str    # concrete next step for the analyst
```

## Output: `AlertAnalysis` (`agent/models.py`) — written to `data/output/alerts/`

```python
class AlertAnalysis(BaseModel):
    alert_id: str
    source_file: str
    score: float
    alert_level: Literal[1, 2, 3]
    summary: str
    recommended_action: str
    analyzed_at: datetime       # UTC, set when the analysis was produced
    model_used: str             # e.g. "claude-opus-5"
    error: str | None           # set only when the LLM call failed - see agent_design.md
```

When `error` is set, `alert_level` is forced to `3` and `score` to `0` so a failed automated
triage is never mistaken for "this alert is low risk" — it surfaces as high-priority until a
human reviews it.

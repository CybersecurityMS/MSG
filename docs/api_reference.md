# Dashboard API Reference

Base URL when run locally: `http://localhost:8000`

## `GET /`

Renders the dashboard page (`dashboard/templates/dashboard.html`). The page itself is a static
shell — all data (stat tiles, charts, table) is populated client-side by JavaScript calling the
two endpoints below, and refreshed automatically every 30 seconds.

## `GET /api/alerts`

Returns every analyzed alert currently in `data/output/alerts/`, sorted by `analyzed_at`
descending.

```json
[
  {
    "alert_id": "evt-1001",
    "source_file": "sample_alerts.csv",
    "score": 87.5,
    "alert_level": 3,
    "summary": "Multiple failed logins indicate a likely brute-force attempt.",
    "recommended_action": "Lock the source IP and force a password reset.",
    "analyzed_at": "2026-08-30T10:20:00Z",
    "model_used": "claude-opus-5",
    "error": null
  }
]
```

## `GET /api/stats`

Aggregate counts over the same data, used to drive the stat tiles and charts.

```json
{
  "total": 3,
  "level_counts": { "1": 1, "2": 1, "3": 1 },
  "average_score": 51.5,
  "error_count": 0
}
```

`error_count` is the number of alerts where automated triage failed (`error` is non-null) and
were flagged for manual review — see [alert_schema.md](alert_schema.md).

Both endpoints re-read the output folder on every call — there is no caching layer and no
database, by design (see [architecture.md](architecture.md)). This is fine at SOC alert volumes
polled every 5 minutes; if volume grows enough for folder-scanning to become a bottleneck, that's
the point to introduce an index (e.g. SQLite) behind the same two endpoints without changing the
agent side at all.

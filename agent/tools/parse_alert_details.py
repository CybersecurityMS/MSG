"""Tool 2: parse a SIEM alert CSV export into NormalizedAlert rows."""

import shutil
from pathlib import Path

import pandas as pd

from agent.models import NormalizedAlert

# Candidate CSV header names (case-insensitive, stripped) for each normalized field.
# Whatever isn't mapped stays available in raw_row for the LLM / dashboard to inspect.
COLUMN_ALIASES: dict[str, list[str]] = {
    "alert_id": ["alert_id", "id", "event_id", "uuid", "alertid"],
    "timestamp": ["timestamp", "time", "date", "datetime", "event_time", "occurred_at", "alert_time"],
    "severity_raw": ["severity", "priority", "level", "risk", "criticality"],
    "source_ip": ["source_ip", "src_ip", "source", "src", "srcip"],
    "dest_ip": ["dest_ip", "destination_ip", "dst_ip", "destination", "dst", "dstip"],
    "rule_name": ["rule_name", "rule", "signature", "alert_name", "event_name", "title"],
    "description": ["description", "details", "message", "summary", "info"],
}


def _normalize(name: str) -> str:
    """Lowercase and strip non-alphanumerics so 'Source_IP' / 'SourceIP' / 'source-ip' all match."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _build_header_map(columns: list[str]) -> dict[str, str]:
    """Map normalized field name -> actual CSV column name, first alias match wins."""
    lookup = {_normalize(col): col for col in columns}
    header_map: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _normalize(alias) in lookup:
                header_map[field] = lookup[_normalize(alias)]
                break
    return header_map


def _has_usable_unique_id(df: pd.DataFrame, id_column: str) -> bool:
    """A candidate ID column is only trustworthy if every non-blank value is unique.

    Some SIEM exports have an "Event ID"-style column that looks like an identifier
    but is actually a shared classification code (e.g. Windows event ID 4625 for
    every failed logon) - using it as alert_id would collide and silently overwrite
    other alerts' output files.
    """
    values = df[id_column].str.strip()
    non_blank = values[values != ""]
    return not non_blank.duplicated().any()


def parse_alert_file(file_path: Path) -> list[NormalizedAlert]:
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    header_map = _build_header_map(list(df.columns))
    if "alert_id" in header_map and not _has_usable_unique_id(df, header_map["alert_id"]):
        del header_map["alert_id"]
    filename = file_path.name

    alerts: list[NormalizedAlert] = []
    for row_index, row in df.iterrows():
        raw_row = row.to_dict()
        natural_id = raw_row.get(header_map.get("alert_id", ""), "").strip() if "alert_id" in header_map else ""
        alert_id = natural_id or f"{file_path.stem}-{row_index}"

        alerts.append(
            NormalizedAlert(
                alert_id=alert_id,
                source_file=filename,
                timestamp=raw_row.get(header_map.get("timestamp", "")) or None,
                severity_raw=raw_row.get(header_map.get("severity_raw", "")) or None,
                source_ip=raw_row.get(header_map.get("source_ip", "")) or None,
                dest_ip=raw_row.get(header_map.get("dest_ip", "")) or None,
                rule_name=raw_row.get(header_map.get("rule_name", "")) or None,
                description=raw_row.get(header_map.get("description", "")) or None,
                raw_row=raw_row,
            )
        )
    return alerts


def parse_alert_files(file_paths: list[str], processed_dir: Path) -> tuple[list[NormalizedAlert], list[str]]:
    """Parse each fetched CSV and move it to processed_dir. Returns (alerts, errors).

    A parse failure on one file is logged and skipped rather than aborting the run.
    """
    alerts: list[NormalizedAlert] = []
    errors: list[str] = []

    for raw_path in file_paths:
        path = Path(raw_path)
        try:
            alerts.extend(parse_alert_file(path))
        except Exception as exc:  # noqa: BLE001 - one bad file must not kill the cycle
            errors.append(f"Failed to parse {path.name}: {exc}")
            continue
        finally:
            if path.exists():
                shutil.move(str(path), str(processed_dir / path.name))

    return alerts, errors

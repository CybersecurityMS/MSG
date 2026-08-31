import shutil
from pathlib import Path

from agent.tools.parse_alert_details import parse_alert_file, parse_alert_files


def test_parse_alert_file_maps_known_columns(sample_csv_path: Path):
    alerts = parse_alert_file(sample_csv_path)

    assert len(alerts) == 3
    first = alerts[0]
    assert first.alert_id == "evt-1001"
    assert first.timestamp == "2026-08-30T10:15:00Z"
    assert first.severity_raw == "High"
    assert first.source_ip == "10.0.0.5"
    assert first.dest_ip == "10.0.0.10"
    assert first.rule_name == "Brute Force Login Attempt"
    assert first.description == "Multiple failed logins from 10.0.0.5"
    assert first.raw_row["EventID"] == "evt-1001"


def test_parse_alert_file_falls_back_to_generated_id(tmp_path: Path):
    csv_path = tmp_path / "no_id.csv"
    csv_path.write_text("Severity,Message\nHigh,something happened\n")

    alerts = parse_alert_file(csv_path)

    assert alerts[0].alert_id == "no_id-0"


def test_parse_alert_file_ignores_non_unique_id_column(tmp_path: Path):
    # Event_ID looks like an id column but is really a repeated classification code
    # (e.g. Windows event 4625 = failed logon, shared across many distinct alerts).
    # Trusting it would collide two different rows onto the same output filename.
    csv_path = tmp_path / "windows_events.csv"
    csv_path.write_text(
        "Event_ID,Message\n4625,First failed logon\n4625,Second failed logon\n4104,Script execution\n"
    )

    alerts = parse_alert_file(csv_path)

    ids = [a.alert_id for a in alerts]
    assert ids == ["windows_events-0", "windows_events-1", "windows_events-2"]
    assert len(set(ids)) == len(ids)


def test_parse_alert_files_moves_source_and_returns_alerts(tmp_path: Path, sample_csv_path: Path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    incoming.mkdir()
    processed.mkdir()
    working_copy = incoming / "sample_alerts.csv"
    shutil.copy(sample_csv_path, working_copy)

    alerts, errors = parse_alert_files([str(working_copy)], processed)

    assert len(alerts) == 3
    assert errors == []
    assert not working_copy.exists()
    assert (processed / "sample_alerts.csv").exists()


def test_parse_alert_files_records_error_without_aborting(tmp_path: Path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    incoming.mkdir()
    processed.mkdir()
    bad_file = incoming / "broken.csv"
    # An unterminated quoted field forces pandas' C parser to raise ParserError.
    bad_file.write_text('a,b\n"unterminated,2\n')

    alerts, errors = parse_alert_files([str(bad_file)], processed)

    assert alerts == []
    assert len(errors) == 1
    assert "broken.csv" in errors[0]

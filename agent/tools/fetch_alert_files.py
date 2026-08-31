"""Tool 1: list new SIEM alert CSVs waiting in the incoming folder."""

from pathlib import Path


def fetch_alert_files(incoming_dir: Path) -> list[str]:
    """Return sorted paths of *.csv files directly under incoming_dir.

    The incoming folder doubles as the queue: parse_alert_details moves each
    file to the processed folder once it's read, so anything found here is new.
    """
    csv_files = [p for p in incoming_dir.iterdir() if p.is_file() and p.suffix.lower() == ".csv"]
    return sorted(str(p) for p in csv_files)

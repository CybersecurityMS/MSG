from pathlib import Path

from agent.tools.fetch_alert_files import fetch_alert_files


def test_returns_only_csv_files_sorted(tmp_path: Path):
    (tmp_path / "b_alerts.csv").write_text("a,b\n1,2\n")
    (tmp_path / "a_alerts.csv").write_text("a,b\n1,2\n")
    (tmp_path / "notes.txt").write_text("ignore me")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.csv").write_text("a,b\n1,2\n")

    result = fetch_alert_files(tmp_path)

    assert result == [str(tmp_path / "a_alerts.csv"), str(tmp_path / "b_alerts.csv")]


def test_empty_folder_returns_empty_list(tmp_path: Path):
    assert fetch_alert_files(tmp_path) == []

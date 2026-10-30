"""Contract for low-memory, append-only-safe public movement snapshots."""
import csv
import hashlib
from pathlib import Path

import pytest

from scripts.build_site_movement_snapshot import build


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["game_id", "prediction_timestamp_utc", "final_home_prob"])
        writer.writeheader()
        writer.writerows(rows)


def test_current_slate_movement_is_bounded_and_original_bytes_are_immutable(tmp_path):
    current = tmp_path / "this_week.csv"
    history = tmp_path / "run_history.csv"
    output = tmp_path / "recent_run_history.csv"
    write_csv(current, [{"game_id": "2026_08_A_B"}, {"game_id": "2026_08_C_D"}])
    rows = [
        {"game_id": "2026_07_OLD_X", "prediction_timestamp_utc": str(i), "final_home_prob": ".5"}
        for i in range(500)
    ]
    rows += [
        {"game_id": "2026_08_A_B", "prediction_timestamp_utc": str(i), "final_home_prob": ".6"}
        for i in range(40)
    ]
    rows += [
        {"game_id": "2026_08_C_D", "prediction_timestamp_utc": str(i), "final_home_prob": ".7"}
        for i in range(3)
    ]
    write_csv(history, rows)
    original_digest = hashlib.sha256(history.read_bytes()).hexdigest()
    assert build(current, history, output, per_game=24) == (2, 27)
    with output.open(newline="", encoding="utf-8") as handle:
        recent = list(csv.DictReader(handle))
    assert len(recent) == 27
    assert {row["game_id"] for row in recent} == {"2026_08_A_B", "2026_08_C_D"}
    assert [row["prediction_timestamp_utc"] for row in recent if row["game_id"] == "2026_08_A_B"] == [str(i) for i in range(16, 40)]
    assert hashlib.sha256(history.read_bytes()).hexdigest() == original_digest
    assert output.stat().st_size < history.stat().st_size


def test_never_synthesize_game_or_accept_empty_slate(tmp_path):
    current = tmp_path / "this_week.csv"
    history = tmp_path / "run_history.csv"
    write_csv(current, [])
    write_csv(history, [])
    with pytest.raises(ValueError, match="empty current slate"):
        build(current, history, tmp_path / "recent.csv")


def test_public_surfaces_do_not_fetch_full_run_history_on_initial_load():
    for name in ("AppSignal.jsx", "SignalEnhancements.jsx", "ForecastClarity.jsx", "ExperienceLayer.jsx"):
        source = (ROOT / "site" / "src" / name).read_text(encoding="utf-8")
        assert "fetchCSV('run_history.csv')" not in source, name
        assert "fetchCSV('run_history_recent.csv')" in source, name

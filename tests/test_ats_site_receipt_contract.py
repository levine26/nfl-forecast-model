from __future__ import annotations

import csv
from pathlib import Path

from scripts.build_site_history_compat import normalize_history_for_site


def _single_row(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.DictReader(handle))


def test_explicit_locked_market_alias_wins_over_generic_receipt_columns(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,gameday,snapshot_type,home_team,away_team,locked_model_spread,locked_market_spread,"
        "expected_margin,spread_line,model_edge\n"
        "2026_03_A_B,2026-09-27,FINAL,B,A,5.0,3.5,-99.0,99.0,1.5\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)
    row = _single_row(path)

    assert row["locked_ats_status"] == "VALUE"
    assert row["locked_ats_pick_team"] == "B"
    assert float(row["locked_ats_pick_market_spread"]) == -3.5
    assert float(row["locked_ats_model_margin_home"]) == 5.0
    assert float(row["locked_ats_market_margin_home"]) == 3.5


def test_missing_locked_market_contract_is_marked_unavailable_not_manufactured(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line\n"
        "2026_03_A_B,2026-09-27,FINAL,B,A,5.0,\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)
    row = _single_row(path)

    assert row["locked_ats_status"] == "UNAVAILABLE"
    assert row["locked_ats_pick_team"] == ""
    assert row["locked_ats_pick_market_spread"] == ""

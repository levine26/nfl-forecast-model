from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from scripts.build_site_history_compat import normalize_history_for_site


def test_final_history_rows_become_locked_site_receipts(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,snapshot_type,prediction_timestamp_utc,final_home_prob,pick\n"
        "2026_01_NE_SEA,2026,1,FINAL,2026-09-09T22:43:57.474413+00:00,0.6042095145,SEA\n"
        "2026_01_SF_LA,2026,1,FINAL,2026-09-10T22:41:08.024270+00:00,0.6167319044,LA\n"
        "2026_01_CHI_CAR,2026,1,LIVE,2026-09-12T19:44:06.634330+00:00,0.3788008117,CHI\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["lock_status"] == "LOCKED"
    assert rows[0]["lock_timestamp_utc"] == "2026-09-09T22:43:57.474413+00:00"
    assert rows[1]["lock_status"] == "LOCKED"
    assert rows[1]["lock_timestamp_utc"] == "2026-09-10T22:41:08.024270+00:00"
    assert rows[2]["lock_status"] == ""
    assert rows[2]["lock_timestamp_utc"] == ""


def test_locked_spread_and_edge_aliases_are_immutable_receipt_values(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,snapshot_type,prediction_timestamp_utc,expected_margin,spread_line,model_edge\n"
        "2026_01_NE_SEA,FINAL,lock-time,3.25,2.5,0.75\n"
        "2026_01_SF_LA,LIVE,live-time,4.5,3.5,1.0\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["locked_model_spread"] == "3.25"
    assert rows[0]["locked_market_spread"] == "2.5"
    assert rows[0]["locked_edge"] == "0.75"
    assert rows[0]["closing_spread"] == ""
    assert rows[1]["locked_model_spread"] == ""
    assert rows[1]["locked_market_spread"] == ""
    assert rows[1]["locked_edge"] == ""


def test_closing_line_is_kept_distinct_from_lock_line(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,snapshot_type,prediction_timestamp_utc,expected_margin,spread_line,model_edge,closing_spread_line\n"
        "2026_01_NE_SEA,FINAL,lock-time,3.25,2.5,0.75,4.0\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["locked_market_spread"] == "2.5"
    assert row["closing_spread"] == "4.0"
    assert row["closing_spread"] != row["locked_market_spread"]


def test_existing_lock_fields_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,snapshot_type,prediction_timestamp_utc,lock_status,lock_timestamp_utc,"
        "locked_model_spread,locked_market_spread,locked_edge,closing_spread,"
        "expected_margin,spread_line,model_edge\n"
        "2026_01_NE_SEA,FINAL,newer,LOCKED,original,9.0,8.0,1.0,7.5,3.0,2.0,1.0\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["lock_status"] == "LOCKED"
    assert row["lock_timestamp_utc"] == "original"
    assert row["locked_model_spread"] == "9.0"
    assert row["locked_market_spread"] == "8.0"
    assert row["locked_edge"] == "1.0"
    assert row["closing_spread"] == "7.5"


def test_sep_27_receipt_backfills_model_selected_home_ats_side_from_frozen_inputs(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line,model_edge\n"
        "2026_03_LAC_BUF,2026,3,2026-09-27,FINAL,BUF,LAC,9.9881180843,7.0,2.9881180843\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["locked_ats_status"] == "VALUE"
    assert row["locked_ats_pick_team"] == "BUF"
    assert float(row["locked_ats_pick_market_spread"]) == -7.0
    assert float(row["locked_ats_model_margin_home"]) == 9.9881180843
    assert float(row["locked_ats_market_margin_home"]) == 7.0
    assert abs(float(row["locked_ats_home_edge_points"]) - 2.9881180843) < 1e-9
    assert row["locked_ats_receipt_source"] == "POLICY_ERA_FROZEN_PREGAME_V1"


def test_sep_27_receipt_backfills_model_selected_home_underdog_from_frozen_inputs(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line,model_edge\n"
        "2026_03_CAR_CLE,2026,3,2026-09-27,FINAL,CLE,CAR,-1.124340402,-2.5,1.375659598\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["locked_ats_status"] == "VALUE"
    assert row["locked_ats_pick_team"] == "CLE"
    assert float(row["locked_ats_pick_market_spread"]) == 2.5


def test_sep_27_receipt_backfills_model_selected_away_ats_side_from_frozen_inputs(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line,model_edge\n"
        "2026_03_NE_JAX,2026,3,2026-09-27,FINAL,JAX,NE,2.48956708,3.0,-0.51043292\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["locked_ats_status"] == "VALUE"
    assert row["locked_ats_pick_team"] == "NE"
    assert float(row["locked_ats_pick_market_spread"]) == 3.0


def test_week_1_and_2_receipts_gain_historical_ats_from_frozen_inputs(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line,"
        "actual_home_score,actual_away_score\n"
        "2026_01_NE_SEA,2026,1,2026-09-09,FINAL,SEA,NE,3.058257004562057,3.0,13,10\n"
        "2026_02_CAR_ATL,2026,2,2026-09-20,FINAL,ATL,CAR,3.515840426885202,-2.5,3,34\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["locked_ats_status"] == "VALUE"
    assert rows[0]["locked_ats_pick_team"] == "SEA"
    assert float(rows[0]["locked_ats_pick_market_spread"]) == -3.0
    assert rows[0]["locked_ats_receipt_source"] == "HISTORICAL_W1_W2_FROZEN_PREGAME_V1"

    assert rows[1]["locked_ats_status"] == "VALUE"
    assert rows[1]["locked_ats_pick_team"] == "ATL"
    assert float(rows[1]["locked_ats_pick_market_spread"]) == 2.5
    assert rows[1]["locked_ats_receipt_source"] == "HISTORICAL_W1_W2_FROZEN_PREGAME_V1"


def test_week_3_pre_policy_receipt_does_not_retroactively_gain_ats_bet(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line,model_edge\n"
        "2026_03_ATL_GB,2026,3,2026-09-24,FINAL,GB,ATL,4.9736399949,5.5,-0.5263600051\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["locked_ats_status"] == ""
    assert row["locked_ats_pick_team"] == ""
    assert row["locked_ats_pick_market_spread"] == ""
    assert row["locked_ats_receipt_source"] == ""


def test_historical_week_1_and_2_record_matches_canonical_production_history(tmp_path: Path) -> None:
    """Pin the official W1-W2 ATS record to the repository's immutable history rows."""
    source = Path(__file__).resolve().parents[1] / "outputs" / "prediction_history.csv"
    path = tmp_path / "prediction_history.csv"
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("season") == "2026" and row.get("week") in {"1", "2"}
        ]

    assert len(rows) == 32
    by_week: dict[int, Counter[str]] = {1: Counter(), 2: Counter()}
    for row in rows:
        assert row["locked_ats_status"] == "VALUE"
        assert row["locked_ats_receipt_source"] == "HISTORICAL_W1_W2_FROZEN_PREGAME_V1"

        side = row["locked_ats_pick_team"]
        spread = float(row["locked_ats_pick_market_spread"])
        home_score = float(row["actual_home_score"])
        away_score = float(row["actual_away_score"])
        selected_margin = home_score - away_score if side == row["home_team"] else away_score - home_score
        edge = selected_margin + spread
        result = "push" if abs(edge) <= 1e-9 else "win" if edge > 0 else "loss"
        by_week[int(row["week"])][result] += 1

    assert by_week[1] == Counter({"loss": 8, "win": 7, "push": 1})
    assert by_week[2] == Counter({"win": 8, "loss": 8})
    combined = by_week[1] + by_week[2]
    assert combined == Counter({"loss": 16, "win": 15, "push": 1})


def test_existing_explicit_ats_receipt_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,season,week,gameday,snapshot_type,home_team,away_team,expected_margin,spread_line,"
        "locked_ats_status,locked_ats_pick_team,locked_ats_pick_market_spread,"
        "locked_ats_model_margin_home,locked_ats_market_margin_home,locked_ats_home_edge_points\n"
        "2026_03_A_B,2026,3,2026-09-27,FINAL,B,A,9.0,7.0,VALUE,A,+7.0,9.0,7.0,-999\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["locked_ats_status"] == "VALUE"
    assert row["locked_ats_pick_team"] == "A"
    assert row["locked_ats_pick_market_spread"] == "+7.0"
    assert row["locked_ats_home_edge_points"] == "-999"
    assert row["locked_ats_receipt_source"] == "DEDICATED_LOCK_RECEIPT"

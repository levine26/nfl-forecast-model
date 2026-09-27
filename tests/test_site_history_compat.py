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
        "2026_02_CAR_ATL,2026,2,2026-09-20,FINAL,ATL,CAR,3.515840426885202,-2.5,34,3\n",
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


def test_historical_week_1_and_2_record_matches_frozen_receipts(tmp_path: Path) -> None:
    """Pin the exact canonical historical ATS record before Week 3 is added."""
    # away, home, expected home margin, sportsbook home margin, final home, final away
    week_1 = [
        ("NE", "SEA", 3.058257004562057, 3.0, 13, 10),
        ("SF", "LA", 4.774445680689222, 3.5, 27, 7),
        ("CHI", "CAR", -2.124642858810936, -3.0, 59, 37),
        ("TB", "CIN", 5.343666609911804, 3.5, 27, 33),
        ("NO", "DET", 3.558400731676545, 7.0, 30, 31),
        ("BUF", "HOU", -0.3296822886967447, -1.5, 36, 31),
        ("BAL", "IND", -3.757713790251336, -3.5, 41, 23),
        ("CLE", "JAX", 13.664164021911455, 8.5, 10, 34),
        ("ATL", "PIT", 5.0091496968778895, 6.5, 13, 20),
        ("NYJ", "TEN", 1.6039794518343071, 1.5, 23, 10),
        ("ARI", "LAC", 6.371711743227861, 9.5, 26, 14),
        ("MIA", "LV", -3.517786900939809, 3.0, 13, 27),
        ("GB", "MIN", 4.325146077149629, 1.5, 22, 39),
        ("WAS", "PHI", 6.388275445655903, 6.0, 22, 24),
        ("DAL", "NYG", 1.3147192180239633, -3.0, 20, 28),
        ("DEN", "KC", -5.034144088432176, 2.5, 10, 31),
    ]
    week_2 = [
        ("DET", "BUF", 6.680681524167905, 5.5, 41, 31),
        ("CAR", "ATL", 3.515840426885202, -2.5, 34, 3),
        ("NO", "BAL", 6.798280598328836, 8.5, 24, 17),
        ("MIN", "CHI", 0.9929717436236912, 4.5, 9, 3),
        ("CIN", "HOU", 3.445075879872115, 3.0, 20, 6),
        ("PIT", "NE", 6.973648182140599, 5.5, 3, 20),
        ("GB", "NYJ", -5.060586715776751, -3.5, 20, 17),
        ("CLE", "TB", 6.8777763681905855, 8.5, 23, 19),
        ("PHI", "TEN", -6.99214051138799, -7.0, 24, 20),
        ("JAX", "DEN", -0.1034017478268528, 2.5, 13, 20),
        ("LV", "LAC", 7.161884144032172, 7.0, 26, 14),
        ("SEA", "ARI", -7.46417672050274, -3.5, 31, 7),
        ("WAS", "DAL", 1.184266274105914, 4.5, 20, 37),
        ("MIA", "SF", 11.125945966417596, 13.5, 13, 35),
        ("IND", "KC", 4.564888888250444, 6.0, 30, 33),
        ("NYG", "LA", 3.963918293600165, 6.5, 6, 28),
    ]

    path = tmp_path / "prediction_history.csv"
    fieldnames = [
        "game_id", "season", "week", "gameday", "snapshot_type", "home_team", "away_team",
        "expected_margin", "spread_line", "actual_home_score", "actual_away_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for week, games in ((1, week_1), (2, week_2)):
            for index, (away, home, model, market, home_score, away_score) in enumerate(games, start=1):
                writer.writerow({
                    "game_id": f"2026_{week:02d}_{index:02d}",
                    "season": "2026",
                    "week": str(week),
                    "gameday": "2026-09-13" if week == 1 else "2026-09-20",
                    "snapshot_type": "FINAL",
                    "home_team": home,
                    "away_team": away,
                    "expected_margin": str(model),
                    "spread_line": str(market),
                    "actual_home_score": str(home_score),
                    "actual_away_score": str(away_score),
                })

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    by_week: dict[int, Counter[str]] = {1: Counter(), 2: Counter()}
    for row in rows:
        side = row["locked_ats_pick_team"]
        spread = float(row["locked_ats_pick_market_spread"])
        home_score = float(row["actual_home_score"])
        away_score = float(row["actual_away_score"])
        selected_margin = home_score - away_score if side == row["home_team"] else away_score - home_score
        edge = selected_margin + spread
        result = "push" if abs(edge) <= 1e-9 else "win" if edge > 0 else "loss"
        by_week[int(row["week"])][result] += 1
        assert row["locked_ats_receipt_source"] == "HISTORICAL_W1_W2_FROZEN_PREGAME_V1"

    assert by_week[1] == Counter({"win": 8, "loss": 7, "push": 1})
    assert by_week[2] == Counter({"win": 12, "loss": 4})
    combined = by_week[1] + by_week[2]
    assert combined == Counter({"win": 20, "loss": 11, "push": 1})


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

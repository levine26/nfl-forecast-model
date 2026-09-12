from __future__ import annotations

import csv
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


def test_existing_lock_fields_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "prediction_history.csv"
    path.write_text(
        "game_id,snapshot_type,prediction_timestamp_utc,lock_status,lock_timestamp_utc\n"
        "2026_01_NE_SEA,FINAL,newer,LOCKED,original\n",
        encoding="utf-8",
    )

    normalize_history_for_site(path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["lock_status"] == "LOCKED"
    assert row["lock_timestamp_utc"] == "original"

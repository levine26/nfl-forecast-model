"""Protect candidate QB1 research capture from checkout races and ledger rewrites."""
from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

import pytest

from research.qb1_t120_ledger_publish_v1 import reconcile_qb1_ledger


FIELDS = [
    "game_id", "qb1_snapshot_sha256", "candidate_id", "captured_at_utc",
    "t120_target_utc", "kickoff_utc", "research_only",
    "production_authorized", "completed_2026_outcomes_used",
    "home_t120_qb1_player_name",
]


def row(game_id="2026_05_BUF_KC", digest="a"*64):
    return dict(game_id=game_id, qb1_snapshot_sha256=digest,
        candidate_id="ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1",
        captured_at_utc="2026-10-11T18:54:00Z",
        t120_target_utc="2026-10-11T19:00:00Z",
        kickoff_utc="2026-10-11T21:00:00Z",
        research_only="True", production_authorized="False",
        completed_2026_outcomes_used="0",
        home_t120_qb1_player_name="QB1")


def write(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def test_new_data_file_created_once(tmp_path):
    pending=tmp_path/"pending.csv"; target=tmp_path/"tree"/"qb1.csv"
    write(pending,[row()])
    assert reconcile_qb1_ledger(target,pending)=={"added":1,"existing":0}
    before=target.read_bytes()
    assert reconcile_qb1_ledger(target,pending)=={"added":0,"existing":1}
    assert before==target.read_bytes()


def test_append_preserves_original_bytes_and_other_research_data(tmp_path):
    pending=tmp_path/"pending.csv"; root=tmp_path/"tree"
    target=root/"qb1_t120_snapshots.csv"; other=root/"qb_state.csv"
    write(target,[row()])
    other.write_bytes(b"existing other Candidate 4 data\n")
    old=target.read_bytes()
    newer=row("2026_05_NYJ_MIA","b"*64)
    write(pending,[row(),newer])
    assert reconcile_qb1_ledger(target,pending)=={"added":1,"existing":1}
    assert target.read_bytes().startswith(old)
    assert other.read_bytes()==b"existing other Candidate 4 data\n"
    assert reconcile_qb1_ledger(target,pending)=={"added":0,"existing":2}


def test_remote_advance_merges_without_losing_intervening_rows(tmp_path):
    incoming=tmp_path/"captured.csv"; published=tmp_path/"data"/"qb1.csv"
    old=row(); intervening=row("2026_05_NE_SEA","b"*64)
    pending=row("2026_05_LAR_SF","c"*64)
    write(incoming,[old,pending])
    write(published,[old,intervening])
    got=reconcile_qb1_ledger(published,incoming)
    assert got=={"added":1,"existing":2}
    with published.open(newline="") as f:
        ids=[x["game_id"] for x in csv.DictReader(f)]
    assert ids==[old["game_id"],intervening["game_id"],pending["game_id"]]


@pytest.mark.parametrize("failure",[
    "same_game_different_hash", "same_digest_changed_player", "bad_header",
    "no_final_newline", "duplicate_id", "late_capture", "production_flag",
    "invalid_hash",
])
def test_fail_closed_and_does_not_mutate_archive(tmp_path,failure):
    target=tmp_path/"target.csv"; incoming=tmp_path/"pending.csv"
    original=row()
    write(target,[original]); proposed=row()
    if failure=="same_game_different_hash":
        proposed["qb1_snapshot_sha256"]="b"*64
    elif failure=="same_digest_changed_player":
        proposed["home_t120_qb1_player_name"]="Different QB"
    elif failure=="bad_header":
        write(incoming,[row()])
        incoming.write_text(incoming.read_text().replace("candidate_id,","candidate_bad,",1))
    elif failure=="no_final_newline":
        target.write_bytes(target.read_bytes().rstrip(b"\n"))
        proposed=row("2026_05_LAR_SF","b"*64)
    elif failure=="duplicate_id":
        write(incoming,[row(),row()])
    elif failure=="late_capture":
        proposed["captured_at_utc"]="2026-10-11T19:01:00Z"
    elif failure=="production_flag":
        proposed["production_authorized"]="True"
    elif failure=="invalid_hash":
        proposed["qb1_snapshot_sha256"]="invalid"
    if failure not in ("duplicate_id","bad_header"):
        write(incoming,[proposed])
    before=target.read_bytes()
    with pytest.raises(ValueError):
        reconcile_qb1_ledger(target,incoming)
    assert target.read_bytes()==before

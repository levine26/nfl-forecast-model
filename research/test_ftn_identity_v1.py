from __future__ import annotations

import pandas as pd
import pytest

from research.ftn_identity_v1 import FTNIdentityGateError, join_ftn_to_pbp


def _ftn(rows: int) -> pd.DataFrame:
    records = []
    for i in range(rows):
        records.append(
            {
                "nflverse_game_id": "2025_01_DAL_PHI",
                "nflverse_play_id": i + 1,
                "season": 2025,
                "week": 1,
                "date_pulled": "2025-09-06T12:00:00Z",
                "n_defense_box": 7,
                "is_motion": i % 2,
                "is_play_action": i % 3 == 0,
                "is_screen_pass": False,
                "is_rpo": False,
                "is_qb_out_of_pocket": False,
                "is_interception_worthy": False,
                "n_blitzers": 1,
                "n_pass_rushers": 4,
                "is_qb_fault_sack": False,
            }
        )
    return pd.DataFrame(records)


def _pbp(ftn: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_id": ftn["nflverse_game_id"].astype(str),
            "play_id": ftn["nflverse_play_id"],
            "posteam": "DAL",
            "defteam": "PHI",
        }
    )


def test_key_identity_gate_keeps_frozen_995_threshold() -> None:
    ftn = _ftn(200)
    pbp = _pbp(ftn).iloc[:-1].copy()

    joined, audit = join_ftn_to_pbp(ftn, pbp)
    assert audit["identity_join_rate"] == pytest.approx(0.995)
    assert audit["identity_unmatched_rows"] == 1
    assert audit["semantic_team_assignment_rate_given_identity"] == pytest.approx(1.0)
    assert len(joined) == 199

    pbp = _pbp(ftn).iloc[:-2].copy()
    with pytest.raises(FTNIdentityGateError, match="identity join rate") as exc:
        join_ftn_to_pbp(ftn, pbp)
    assert exc.value.audit["identity_join_rate"] == pytest.approx(0.99)
    assert exc.value.audit["minimum_required_rate"] == pytest.approx(0.995)


def test_missing_team_semantics_do_not_redefine_exact_key_identity() -> None:
    ftn = _ftn(200)
    pbp = _pbp(ftn)
    pbp.loc[199, ["posteam", "defteam"]] = None

    joined, audit = join_ftn_to_pbp(ftn, pbp)

    assert audit["identity_join_rate"] == pytest.approx(1.0)
    assert audit["identity_matched_rows"] == 200
    assert audit["semantic_team_missing_rows"] == 1
    assert audit["semantic_team_assignment_rate_given_identity"] == pytest.approx(0.995)
    assert audit["eligible_joined_rows"] == 199
    assert len(joined) == 199


def test_duplicate_source_or_pbp_keys_still_fail_closed() -> None:
    ftn = _ftn(3)
    duplicate_ftn = pd.concat([ftn, ftn.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="FTN game/play identity is not unique"):
        join_ftn_to_pbp(duplicate_ftn, _pbp(ftn))

    duplicate_pbp = pd.concat([_pbp(ftn), _pbp(ftn).iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="PBP game/play identity is not unique"):
        join_ftn_to_pbp(ftn, duplicate_pbp)


def test_invalid_date_gate_emits_machine_readable_audit() -> None:
    ftn = _ftn(200)
    ftn.loc[0:1, "date_pulled"] = "bad-date"

    with pytest.raises(FTNIdentityGateError, match="date_pulled validity") as exc:
        join_ftn_to_pbp(ftn, _pbp(ftn))
    assert exc.value.audit["identity_join_rate"] == pytest.approx(1.0)
    assert exc.value.audit["date_pulled_valid_rate"] == pytest.approx(0.99)
    assert exc.value.audit["completed_2026_outcomes_used"] == 0

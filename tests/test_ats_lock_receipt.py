import pandas as pd

from nfl_forecast.publish import _ats_lock_fields, _backfill_policy_ats_locks


def test_ats_lock_fields_select_home_side_at_market_number():
    fields = _ats_lock_fields({
        "home_team": "BUF",
        "away_team": "LAC",
        "expected_margin": 9.988,
        "spread_line": 7.0,
    })
    assert fields["locked_ats_status"] == "VALUE"
    assert fields["locked_ats_pick_team"] == "BUF"
    assert fields["locked_ats_pick_market_spread"] == -7.0
    assert fields["locked_ats_home_edge_points"] == 2.988


def test_ats_lock_fields_select_away_side_at_market_number():
    fields = _ats_lock_fields({
        "home_team": "JAX",
        "away_team": "NE",
        "expected_margin": 2.49,
        "spread_line": 3.0,
    })
    assert fields["locked_ats_status"] == "VALUE"
    assert fields["locked_ats_pick_team"] == "NE"
    assert fields["locked_ats_pick_market_spread"] == 3.0
    assert fields["locked_ats_home_edge_points"] == -0.51


def test_backfill_only_uses_policy_era_locked_receipts_and_their_own_inputs():
    frame = pd.DataFrame([
        {
            "game_id": "2026_03_KC_MIA",
            "gameday": "2026-09-27",
            "lock_status": "LOCKED",
            "home_team": "MIA",
            "away_team": "KC",
            "expected_margin": -3.6876,
            "spread_line": -10.0,
        },
        {
            "game_id": "2026_03_ATL_GB",
            "gameday": "2026-09-24",
            "lock_status": "LOCKED",
            "home_team": "GB",
            "away_team": "ATL",
            "expected_margin": 4.97,
            "spread_line": 4.5,
        },
    ])
    migrated = _backfill_policy_ats_locks(frame)
    today = migrated[migrated.game_id.eq("2026_03_KC_MIA")].iloc[0]
    prior = migrated[migrated.game_id.eq("2026_03_ATL_GB")].iloc[0]

    assert today.locked_ats_status == "VALUE"
    assert today.locked_ats_pick_team == "MIA"
    assert today.locked_ats_pick_market_spread == 10.0
    assert pd.isna(prior.locked_ats_status)

import pandas as pd

from nfl_forecast.staff_impact import add_staff_impact


def _season(team, season, start_play, motion_rate, play_action_rate):
    rows_pbp = []
    rows_ftn = []
    n = 100
    for i in range(n):
        game_id = f"{season}_{team}_{i // 25}"
        play_id = start_play + i
        rows_pbp.append({
            "game_id": game_id,
            "play_id": play_id,
            "season": season,
            "posteam": team,
            "defteam": "NE" if team != "NE" else "SEA",
            "epa": 0.08,
            "down": 1 if i % 2 == 0 else 2,
            "pass_attempt": 1 if i % 10 < 6 else 0,
            "rush_attempt": 0 if i % 10 < 6 else 1,
        })
        rows_ftn.append({
            "nflverse_game_id": game_id,
            "nflverse_play_id": play_id,
            "is_motion": i < round(n * motion_rate),
            "is_play_action": i < round(n * play_action_rate),
            "is_rpo": False,
            "is_screen_pass": i < 4,
            "qb_location": "S" if i < 70 else "U",
            "n_blitzers": 1 if i < 28 else 0,
            "n_defense_box": 6,
        })
    return rows_pbp, rows_ftn


def test_new_coordinator_gets_prior_tendency_impact_context():
    pbp_rows, ftn_rows = [], []
    for args in [
        ("SEA", 2025, 1, 0.10, 0.12),
        ("MIN", 2024, 1001, 0.52, 0.46),
        ("MIN", 2025, 2001, 0.48, 0.44),
    ]:
        p, f = _season(*args)
        pbp_rows.extend(p)
        ftn_rows.extend(f)

    predictions = pd.DataFrame([{
        "game_id": "2026_01_NE_SEA",
        "away_team": "NE",
        "home_team": "SEA",
    }])
    coaches = {
        "SEA": {
            2026: {"off_coach": "Alex Coach", "def_coach": "D One", "source_url": "https://example.com/sea-2026"},
            2025: {"off_coach": "Old Coach", "def_coach": "D One", "source_url": "https://example.com/sea-2025"},
        },
        "MIN": {
            2025: {"off_coach": "Alex Coach", "def_coach": "D Two", "source_url": "https://example.com/min-2025"},
            2024: {"off_coach": "Alex Coach", "def_coach": "D Two", "source_url": "https://example.com/min-2024"},
        },
    }

    evidence, status = add_staff_impact(
        predictions=predictions,
        evidence={"2026_01_NE_SEA": []},
        coaching_history=coaches,
        ftn=pd.DataFrame(ftn_rows),
        pbp=pd.DataFrame(pbp_rows),
        season=2026,
    )

    impacts = [
        item for item in evidence["2026_01_NE_SEA"]
        if (item.get("metadata") or {}).get("family") == "staff_impact"
    ]
    assert status["status"] == "healthy"
    assert status["impacts_added"] == 1
    assert len(impacts) == 1
    item = impacts[0]
    assert item["category"] == "coaching"
    assert "Alex Coach" in item["title"]
    assert "pre-snap motion" in item["summary"] or "play action" in item["summary"]
    assert "historical tendency projection" in item["summary"]
    assert item["metadata"]["coordinator"] == "Alex Coach"
    assert item.get("promoted_to_model", False) is False

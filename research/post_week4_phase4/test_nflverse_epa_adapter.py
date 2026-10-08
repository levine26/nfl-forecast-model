"""Synthetic adapter-level tests; never count as real 2026 prospective captures."""
from copy import deepcopy
from datetime import datetime, timezone
import pytest

from research.post_week4_phase4.nflverse_epa_adapter import (
    acquisition_evidence, team_game_epa, build_team_states,
    live_source_verifier_unavailable,
)


def fixture():
    games, plays, counts = [], [], {}
    for season, weeks in ((2025, range(1, 9)), (2026, range(1, 3))):
        for team, other in (("KC", "NYJ"), ("BUF", "MIA")):
            for week in weeks:
                gid = f"{season}_{week:02d}_{other}_{team}"
                ko = f"{season}-09-{week+1:02d}T12:00:00+00:00"
                games.append({"game_id":gid,"season":season,"week":week,
                              "away_team":other,"home_team":team,
                              "kickoff_utc":ko,"game_type":"REG",
                              "completed_verified":True})
                plays.extend([
                    {"game_id":gid,"season":season,"week":week,"home_team":team,
                     "away_team":other,"season_type":"REG","play_id":1,
                     "posteam":team,"defteam":other,"epa":0.1},
                    {"game_id":gid,"season":season,"week":week,"home_team":team,
                     "away_team":other,"season_type":"REG","play_id":2,
                     "posteam":team,"defteam":other,"epa":0.3},
                    {"game_id":gid,"season":season,"week":week,"home_team":team,
                     "away_team":other,"season_type":"REG","play_id":3,
                     "posteam":other,"defteam":team,"epa":-0.4},
                ])
                counts[gid] = 3
    target = {"game_id":"2026_05_BUF_KC","season":2026,"week":5,
              "away_team":"BUF","home_team":"KC",
              "kickoff_utc":"2026-10-11T20:30:00+00:00"}
    return games,plays,counts,target


def test_epa_matches_offense_and_defense_mean_rule():
    games,plays,counts,target = fixture()
    team = team_game_epa(plays,games,counts)
    first = team[("2025_01_NYJ_KC","KC")]
    assert first["off_epa"] == pytest.approx(0.2)
    assert first["def_epa_allowed"] == pytest.approx(-0.4)
    states = build_team_states(target=target,historical_games=games,
              per_team_epa=team,stats_observed_utc="2026-10-08T12:00:00Z",
              capture_cutoff_utc="2026-10-08T13:00:00Z")
    assert len(states["home"]["last_eight_previous_season"]) == 8
    assert states["away"]["expected_completed_current_season_games"] == 2
    assert states["home"]["previous_season_league_mean"]["off_epa"] == pytest.approx(-0.1)
    assert states["home"]["previous_season_league_mean"]["def_epa_allowed"] == pytest.approx(-0.1)


@pytest.mark.parametrize("mutation", ["missing_play","revision","wrong_week",
                    "unexpected_team","duplicate_play","missing_manifest",
                    "wrong_season","missing_epa","unverified_fixture"])
def test_rejects_bad_pbp_and_schedule(mutation):
    games,plays,counts,target=fixture()
    if mutation=="missing_play": plays.pop()
    elif mutation=="revision": plays[-1]["epa"]=float("inf")
    elif mutation=="wrong_week": plays[0]["week"]=7
    elif mutation=="unexpected_team": plays[0]["posteam"]="XXX"
    elif mutation=="duplicate_play": plays[1]["play_id"]=plays[0]["play_id"]
    elif mutation=="missing_manifest": counts.pop(next(iter(counts)))
    elif mutation=="wrong_season": plays[0]["season"]=2024
    elif mutation=="missing_epa": plays[0]["epa"]=None
    elif mutation=="unverified_fixture": games[0]["completed_verified"]=False
    if mutation == "unverified_fixture":
        team=team_game_epa(plays,games,counts)
        with pytest.raises(ValueError,match="unverified"):
            build_team_states(target=target,historical_games=games,per_team_epa=team,
                stats_observed_utc="2026-10-08T12:00:00Z",
                capture_cutoff_utc="2026-10-08T13:00:00Z")
    elif mutation=="missing_epa":
        # Incomplete individual EPA can be legal; no eligible two-sided EPA cannot.
        for p in plays:
            if p["game_id"]==games[0]["game_id"]:
                p["epa"]=None
        with pytest.raises(ValueError):
            team_game_epa(plays,games,counts)
    else:
        with pytest.raises(ValueError):
            team_game_epa(plays,games,counts)


def test_acquisition_clock_and_hash_not_a_publication_claim():
    got=acquisition_evidence(b"sample",received_utc="2026-10-08T12:00:00Z",
          asset_id="nflverse-pbp-2026",
          claimed_asset_updated_utc="2026-10-07T20:00:00Z")
    assert len(got["payload_sha256"]) == 64
    assert got["publication_independently_attested"] is False
    with pytest.raises(ValueError):
        acquisition_evidence(b"x",received_utc="2026-10-08T12:00:00Z",
                asset_id="pbp",claimed_asset_updated_utc="2026-10-09T12:00:00Z")


@pytest.mark.parametrize("failure", ["late_source","target_started","missing_prior",
                                     "missing_team_game","missing_completed"])
def test_state_build_fail_closed(failure):
    games,plays,counts,target=fixture()
    team=team_game_epa(plays,games,counts)
    receipt="2026-10-08T12:00:00Z"
    cutoff="2026-10-08T13:00:00Z"
    if failure=="late_source": receipt="2026-10-09T15:00:00Z"
    elif failure=="target_started": cutoff="2026-10-12T13:00:00Z"
    elif failure=="missing_prior": games=[g for g in games if g["game_id"]!="2025_01_NYJ_KC"]
    elif failure=="missing_team_game": team.pop(("2025_01_NYJ_KC","KC"))
    elif failure=="missing_completed": games[0]["completed_verified"]=False
    with pytest.raises(ValueError):
        build_team_states(target=target,historical_games=games,
           per_team_epa=team,stats_observed_utc=receipt,capture_cutoff_utc=cutoff)


def test_no_synthetic_live_approval():
    with pytest.raises(RuntimeError,match="not configured"):
        live_source_verifier_unavailable({})

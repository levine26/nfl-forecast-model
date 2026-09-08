import pandas as pd

from nfl_forecast.qb_history import add_portable_qb_history, portable_qb_history


def _fixtures():
    game = pd.Series({"game_id":"g","away_team":"ATL","home_team":"PIT"})
    depth = pd.DataFrame([
        {"team":"ATL","player_name":"Tua Tagovailoa","pos_abb":"QB","pos_rank":1,"gsis_id":"tua"},
        {"team":"PIT","player_name":"PIT QB","pos_abb":"QB","pos_rank":1,"gsis_id":"pitqb"},
    ])
    pbp = pd.DataFrame([
        {"season":2024,"posteam":"MIA","defteam":"PIT","passer_player_id":"tua","epa":0.20,"game_id":"m1"},
        {"season":2024,"posteam":"MIA","defteam":"PIT","passer_player_id":"tua","epa":-0.10,"game_id":"m1"},
    ] * 12)
    return game, depth, pbp


def test_qb_opponent_history_follows_player_across_team_change():
    game, depth, pbp = _fixtures()
    items = portable_qb_history(game, pbp, depth, 2026)
    tua = [x for x in items if "Tua Tagovailoa vs PIT" in x["title"]]
    assert tua, "QB-vs-opponent history should follow the quarterback after a team change"
    assert tua[0]["sample_size"] == 24
    assert tua[0]["metadata"]["team_changed"] is True
    assert "MIA" in tua[0]["metadata"]["prior_offenses"]


def test_portable_history_replaces_generic_duplicate_but_keeps_coordinator_history():
    game, depth, pbp = _fixtures()
    predictions = pd.DataFrame([game])
    evidence = {
        "g": [
            {"category":"history","title":"Tua Tagovailoa vs PIT: prior meetings","metadata":{"family":"qb_opponent_history"}},
            {"category":"history","title":"Tua Tagovailoa vs Coach X's PIT defense","metadata":{"family":"qb_coordinator_history"}},
        ]
    }
    out = add_portable_qb_history(predictions, evidence, pbp, depth, 2026)["g"]
    generic = [x for x in out if (x.get("metadata") or {}).get("family") == "qb_opponent_history"]
    coordinator = [x for x in out if (x.get("metadata") or {}).get("family") == "qb_coordinator_history"]
    assert len(generic) == 1
    assert "player history" in generic[0]["title"]
    assert len(coordinator) == 1

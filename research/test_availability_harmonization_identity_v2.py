from __future__ import annotations

import pandas as pd
import pytest

import research.run_availability_harmonization_identity_v2 as v2


def _official(player: str = "Kam Curl", *, team: str = "WAS") -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2022,
        "week": 9,
        "team": team,
        "external_player": player,
        "external_position": "S",
        "external_injury": "Back",
        "external_practice_status": "Limited Participation in Practice",
        "external_game_status": "Questionable",
        "external_source": "nfl_com_official_injury_page",
        "source_url": "https://www.nfl.com/injuries/league/2022/reg9",
    }])


def _injury(*, team: str = "WAS", gsis_id: str = "00-0036383", name: str = "Kamren Curl") -> pd.DataFrame:
    first, last = name.split(" ", 1)
    return pd.DataFrame([{
        "season": 2022,
        "week": 9,
        "team": team,
        "gsis_id": gsis_id,
        "full_name": name,
        "first_name": first,
        "last_name": last,
    }])


def _players() -> pd.DataFrame:
    return pd.DataFrame([{
        "gsis_id": "00-0036383",
        "display_name": "Kamren Curl",
        "football_name": "Kam Curl",
        "common_first_name": "Kam",
        "first_name": "Kamren",
        "last_name": "Curl",
    }])


def test_player_master_exact_alias_resolves_same_team_week_identity() -> None:
    metrics, unresolved = v2.deterministic_alias_reverse_identity_audit(
        _official(), _injury(), season=2022, player_master=_players()
    )
    assert metrics["official_identity_resolution_rate"] == 1.0
    assert metrics["identity_bridge_resolved_rows"] == 1
    assert metrics["identity_bridge_ambiguous_rows"] == 0
    assert unresolved.empty


def test_alias_cannot_move_identity_across_team_or_week() -> None:
    metrics, unresolved = v2.deterministic_alias_reverse_identity_audit(
        _official(team="WAS"), _injury(team="DAL"), season=2022, player_master=_players()
    )
    assert metrics["official_identity_resolution_rate"] == 0.0
    assert metrics["identity_bridge_resolved_rows"] == 0
    assert len(unresolved) == 1


def test_alias_bridge_does_not_use_fuzzy_matching() -> None:
    metrics, unresolved = v2.deterministic_alias_reverse_identity_audit(
        _official(player="Kam Curll"), _injury(), season=2022, player_master=_players()
    )
    assert metrics["identity_bridge_resolved_rows"] == 0
    assert len(unresolved) == 1


def test_ambiguous_exact_alias_stays_unresolved() -> None:
    injuries = pd.concat([
        _injury(gsis_id="00-0036383", name="Kamren Curl"),
        _injury(gsis_id="00-0099999", name="Kameron Curl"),
    ], ignore_index=True)
    players = pd.concat([
        _players(),
        pd.DataFrame([{
            "gsis_id": "00-0099999",
            "display_name": "Kameron Curl",
            "football_name": "Kam Curl",
            "common_first_name": "Kam",
            "first_name": "Kameron",
            "last_name": "Curl",
        }]),
    ], ignore_index=True)
    metrics, unresolved = v2.deterministic_alias_reverse_identity_audit(
        _official(), injuries, season=2022, player_master=players
    )
    assert metrics["identity_bridge_resolved_rows"] == 0
    assert metrics["identity_bridge_ambiguous_rows"] == 1
    assert len(unresolved) == 1


def test_existing_exact_name_resolution_is_not_rewritten_by_bridge() -> None:
    official = _official(player="Kamren Curl")
    metrics, unresolved = v2.deterministic_alias_reverse_identity_audit(
        official, _injury(), season=2022, player_master=_players()
    )
    assert metrics["official_identity_resolution_rate"] == 1.0
    assert metrics["identity_bridge_attempted_rows"] == 0
    assert metrics["identity_bridge_resolved_rows"] == 0
    assert unresolved.empty


def test_player_master_digest_is_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(v2, "PLAYER_MASTER_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="digest changed"):
        v2.load_player_master(b"gsis_id,display_name,football_name,common_first_name,first_name,last_name\n")

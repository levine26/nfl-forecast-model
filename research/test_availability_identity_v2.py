from __future__ import annotations

import pandas as pd
import pytest

import research.availability_identity_v2 as identity_v2
from research.availability_identity_v2 import (
    attach_stable_identity_v2,
    build_player_alias_lookup,
    sha256_bytes,
    validate_player_master_payload,
)


def _player_master() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "gsis_id": "00-0036349",
            "display_name": "Kamren Curl",
            "common_first_name": "Kam",
            "first_name": "Kamren",
            "last_name": "Curl",
            "short_name": "K.Curl",
            "football_name": "Kam Curl",
        },
        {
            "gsis_id": "00-0037079",
            "display_name": "Tariq Woolen",
            "common_first_name": "Riq",
            "first_name": "Tariq",
            "last_name": "Woolen",
            "short_name": "T.Woolen",
            "football_name": "Riq Woolen",
        },
    ])


def _canonical() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "season": 2022,
            "week": 1,
            "team": "WAS",
            "gsis_id": "00-0036349",
            "full_name": "Kamren Curl",
            "first_name": "Kamren",
            "last_name": "Curl",
        },
        {
            "season": 2022,
            "week": 2,
            "team": "SEA",
            "gsis_id": "00-0037079",
            "full_name": "Tariq Woolen",
            "first_name": "Tariq",
            "last_name": "Woolen",
        },
    ])


def _official(player: str, *, week: int, team: str) -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2022,
        "week": week,
        "team": team,
        "external_player": player,
    }])


def test_player_master_alias_lookup_contains_only_exact_declared_name_forms() -> None:
    aliases = build_player_alias_lookup(_player_master())
    assert aliases["kam curl"] == ("00-0036349",)
    assert aliases["kamren curl"] == ("00-0036349",)
    assert aliases["riq woolen"] == ("00-0037079",)
    assert aliases["tariq woolen"] == ("00-0037079",)
    assert "k curl" not in aliases  # short_name is intentionally not an allowed alias.


def test_v2_resolves_exact_player_master_alias_only_when_gsis_is_in_same_team_week() -> None:
    matched = attach_stable_identity_v2(
        _official("Kam Curl", week=1, team="WAS"),
        _canonical(),
        _player_master(),
    )
    row = matched.iloc[0]
    assert row.gsis_id == "00-0036349"
    assert row.identity_match_state == "unique"
    assert row.identity_match_method == "player_master_alias_team_week"


def test_v2_does_not_use_current_player_master_identity_to_invent_historical_team_membership() -> None:
    blocked = attach_stable_identity_v2(
        _official("Kam Curl", week=2, team="SEA"),
        _canonical(),
        _player_master(),
    )
    row = blocked.iloc[0]
    assert row.gsis_id == ""
    assert row.identity_match_state == "unmatched"
    assert row.identity_match_method == "player_master_alias_not_in_historical_team_week"


def test_v2_never_fuzzy_matches_nearby_name() -> None:
    blocked = attach_stable_identity_v2(
        _official("Ken Curl", week=1, team="WAS"),
        _canonical(),
        _player_master(),
    )
    assert blocked.iloc[0].gsis_id == ""
    assert blocked.iloc[0].identity_match_state == "unmatched"


def test_v2_alias_ambiguity_fails_closed_when_multiple_alias_gsis_exist_in_same_team_week() -> None:
    players = pd.concat([
        _player_master(),
        pd.DataFrame([{
            "gsis_id": "00-0099999",
            "display_name": "Other Person",
            "common_first_name": "Kam",
            "first_name": "Other",
            "last_name": "Curl",
            "short_name": "O.Curl",
            "football_name": "Kam Curl",
        }]),
    ], ignore_index=True)
    canonical = pd.concat([
        _canonical(),
        pd.DataFrame([{
            "season": 2022,
            "week": 1,
            "team": "WAS",
            "gsis_id": "00-0099999",
            "full_name": "Other Person",
            "first_name": "Other",
            "last_name": "Person",
        }]),
    ], ignore_index=True)
    blocked = attach_stable_identity_v2(_official("Kam Curl", week=1, team="WAS"), canonical, players)
    assert blocked.iloc[0].gsis_id == ""
    assert blocked.iloc[0].identity_match_state == "ambiguous"


def test_v2_preserves_unique_v1_exact_match_before_alias_logic() -> None:
    matched = attach_stable_identity_v2(
        _official("Kamren Curl", week=1, team="WAS"),
        _canonical(),
        _player_master(),
    )
    assert matched.iloc[0].gsis_id == "00-0036349"
    assert matched.iloc[0].identity_match_method == "exact_full_name"


def test_player_master_payload_digest_and_primary_key_fail_closed(monkeypatch) -> None:
    payload = _player_master().to_csv(index=False).encode()
    monkeypatch.setattr(identity_v2, "PLAYER_MASTER_EXPECTED_SHA256", sha256_bytes(payload))
    validated = validate_player_master_payload(payload)
    assert len(validated) == 2

    duplicate = pd.concat([_player_master(), _player_master().iloc[[0]]], ignore_index=True)
    duplicate_payload = duplicate.to_csv(index=False).encode()
    monkeypatch.setattr(identity_v2, "PLAYER_MASTER_EXPECTED_SHA256", sha256_bytes(duplicate_payload))
    with pytest.raises(ValueError, match="duplicate GSIS primary keys"):
        validate_player_master_payload(duplicate_payload)

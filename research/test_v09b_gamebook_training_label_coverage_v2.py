from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from research.v09b_gamebook_training_label_coverage_v1 import ArchiveSource
from research.v09b_gamebook_training_label_coverage_v2 import (
    build_source_map_v2,
    resolve_game_source_v2,
    source_host,
)

CONTRACT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_contract_v2.json"
)
V1_RECEIPT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_receipt_v1.json"
)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _source(host: str, team: str, *, gsis: str = "99999", timestamp: str = "20200101000000") -> ArchiveSource:
    return ArchiveSource(
        timestamp=timestamp,
        original=f"https://{host}/liveupdate/gamecenter/{gsis}/{team}_Gamebook.pdf",
        statuscode="200",
        digest=f"DIGEST-{host}-{team}",
        mimetype="application/pdf",
        length="1000",
        gsis=gsis,
        team_code=team,
    )


def test_v2_preserves_v1_failure_and_thresholds() -> None:
    contract = _contract()
    receipt = json.loads(V1_RECEIPT_PATH.read_text(encoding="utf-8"))
    assert receipt["technical_status"] == "BLOCKED"
    assert receipt["historical_gamebook_coverage_qualified"] is False
    assert contract["v1_result_preservation"]["v1_failure_reclassified_as_pass"] is False
    assert contract["v1_result_preservation"]["v1_thresholds_relaxed"] is False
    gates = contract["frozen_qualification_gates"]
    assert gates["combined_archive_game_coverage_rate_required"] == 1.0
    assert gates["season_combined_archive_game_coverage_rate_required"] == 1.0
    assert gates["alias_conflict_games_allowed"] == 0
    assert contract["non_authorizations"]["v09b_model_fit_authorized_by_coverage_alone"] is False
    assert contract["governance"]["completed_2026_outcomes_used"] == 0


def test_same_game_same_team_across_hosts_is_mirror_not_ambiguity() -> None:
    contract = _contract()
    sources = [
        _source("www.nfl.com", "CHI", timestamp="20190101000000"),
        _source("nflcdns.nfl.com", "CHI", timestamp="20190102000000"),
    ]
    source_index = {("99999", "CHI"): sources}
    chosen, diagnostic = resolve_game_source_v2(
        gsis="99999",
        home_team="CHI",
        source_index=source_index,
        contract=contract,
    )
    assert chosen is not None
    assert source_host(chosen) == "nflcdns.nfl.com"
    assert diagnostic["alias_conflict"] is False
    assert diagnostic["mirror_count"] == 2
    assert diagnostic["mirror_hosts"] == ["nflcdns.nfl.com", "www.nfl.com"]


def test_different_team_aliases_for_same_game_are_reported_as_conflict() -> None:
    contract = _contract()
    source_index = {
        ("99999", "LAR"): [_source("nflcdns.nfl.com", "LAR")],
        ("99999", "STL"): [_source("www.nfl.com", "STL")],
    }
    chosen, diagnostic = resolve_game_source_v2(
        gsis="99999",
        home_team="LAR",
        source_index=source_index,
        contract=contract,
    )
    assert chosen is not None
    assert chosen.team_code == "LAR"
    assert diagnostic["alias_conflict"] is True
    assert diagnostic["resolved_team_codes"] == ["LAR", "STL"]


def test_source_map_does_not_use_outcome_or_participation_fields() -> None:
    contract = _contract()
    schedule = pd.DataFrame(
        [
            {
                "season": 2020,
                "week": 1,
                "game_type": "REG",
                "game_id": "2020_01_DAL_LAR",
                "gsis": 99999,
                "home_team": "LAR",
                "away_team": "DAL",
                "gsis_normalized": "99999",
            }
        ]
    )
    sources = [_source("nflcdns.nfl.com", "LAR")]
    mapped = build_source_map_v2(schedule, sources, contract)
    assert bool(mapped.loc[0, "archive_found"]) is True
    assert mapped.loc[0, "archive_host"] == "nflcdns.nfl.com"
    assert int(mapped.loc[0, "mirror_count"]) == 1
    forbidden = {"result", "winner", "score", "snaps", "participation", "starter"}
    assert forbidden.isdisjoint(set(mapped.columns))

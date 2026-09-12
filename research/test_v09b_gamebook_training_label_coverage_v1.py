from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from research.v09b_gamebook_training_label_coverage_v1 import (
    ArchiveSource,
    build_source_map,
    home_code_candidates,
    normalize_gsis,
    parse_cdx_json,
    replay_url,
)

CONTRACT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_contract_v1.json"
)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_is_fail_closed_and_source_only() -> None:
    contract = _contract()
    assert contract["contract_id"] == "V09B-GAMEBOOK-TRAINING-LABEL-COVERAGE-V1"
    assert contract["source_universe"]["expected_regular_season_games_total"] == 2576
    assert contract["frozen_qualification_gates"]["archive_game_coverage_rate_required"] == 1.0
    assert contract["frozen_qualification_gates"]["season_archive_game_coverage_rate_required"] == 1.0
    assert contract["non_authorizations"]["training_label_semantics_qualified_by_coverage_alone"] is False
    assert contract["non_authorizations"]["v09b_model_fit_authorized_by_coverage_alone"] is False
    assert contract["governance"]["model_fit_performed"] is False
    assert contract["governance"]["game_outcomes_used"] == 0
    assert contract["governance"]["completed_2026_outcomes_used"] == 0
    assert contract["governance"]["thresholds_frozen_before_coverage_execution"] is True


def test_normalize_gsis_is_strict() -> None:
    assert normalize_gsis(55594) == "55594"
    assert normalize_gsis(55594.0) == "55594"
    assert normalize_gsis("55594") == "55594"
    assert normalize_gsis(None) == ""
    assert normalize_gsis("55A94") == ""


def test_historical_home_aliases_cover_relocations() -> None:
    contract = _contract()
    assert home_code_candidates("LAR", contract) == ["LAR", "LA", "STL"]
    assert home_code_candidates("LAC", contract) == ["LAC", "SD"]
    assert home_code_candidates("LV", contract) == ["LV", "OAK"]
    assert home_code_candidates("JAX", contract) == ["JAX", "JAC"]


def test_parse_cdx_json_extracts_legacy_gamebook_identity() -> None:
    payload = [
        ["timestamp", "original", "statuscode", "digest", "mimetype", "length"],
        [
            "20121017010203",
            "http://www.nfl.com/liveupdate/gamecenter/55594/SD_Gamebook.pdf",
            "200",
            "ABCDEF",
            "application/pdf",
            "123456",
        ],
        [
            "20121017010203",
            "http://www.nfl.com/liveupdate/gamecenter/55594/SD_Gamedata.xml",
            "200",
            "IGNORE",
            "text/xml",
            "999",
        ],
    ]
    rows = parse_cdx_json(payload)
    assert len(rows) == 1
    assert rows[0].gsis == "55594"
    assert rows[0].team_code == "SD"
    assert rows[0].digest == "ABCDEF"


def test_source_map_resolves_legacy_home_alias_without_outcome_data() -> None:
    contract = _contract()
    schedule = pd.DataFrame(
        [
            {
                "season": 2015,
                "week": 1,
                "game_type": "REG",
                "game_id": "2015_01_SEA_STL",
                "gsis": 99999,
                "home_team": "LAR",
                "away_team": "SEA",
                "gsis_normalized": "99999",
            }
        ]
    )
    sources = [
        ArchiveSource(
            timestamp="20150914000000",
            original="http://www.nfl.com/liveupdate/gamecenter/99999/STL_Gamebook.pdf",
            statuscode="200",
            digest="DIGEST",
            mimetype="application/pdf",
            length="1000",
            gsis="99999",
            team_code="STL",
        )
    ]
    mapped = build_source_map(schedule, sources, contract)
    assert bool(mapped.loc[0, "archive_found"]) is True
    assert mapped.loc[0, "archive_original"].endswith("/STL_Gamebook.pdf")
    assert bool(mapped.loc[0, "archive_ambiguous"]) is False


def test_replay_url_preserves_original_source_identity() -> None:
    original = "http://www.nfl.com/liveupdate/gamecenter/55594/SD_Gamebook.pdf"
    assert replay_url("20121017010203", original) == (
        "https://web.archive.org/web/20121017010203id_/"
        "http://www.nfl.com/liveupdate/gamecenter/55594/SD_Gamebook.pdf"
    )

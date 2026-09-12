from __future__ import annotations

import polars as pl

from research.v09b_roster_universe_audit_v1 import (
    audit_frame,
    canonical_team_game_weeks,
    normalize_team,
    source_era,
)


TEAMS = [f"T{i:02d}" for i in range(32)]


def _games_2012() -> list[dict[str, object]]:
    games: list[dict[str, object]] = []
    game_no = 0
    for week in range(1, 17):
        for pairing in range(16):
            away = TEAMS[pairing * 2]
            home = TEAMS[pairing * 2 + 1]
            games.append(
                {
                    "week": week,
                    "game_id": f"2012_{week:02d}_{away}_{home}_{game_no}",
                    "away_team": away,
                    "home_team": home,
                }
            )
            game_no += 1
    assert len(games) == 256
    return games


def _frame_2012(*, drop_last: bool = False, duplicate_first: bool = False) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    keys = sorted(canonical_team_game_weeks(_games_2012()))
    if drop_last:
        keys = keys[:-1]
    for index, (week, team) in enumerate(keys):
        rows.append(
            {
                "season": 2012,
                "game_type": "REG",
                "week": week,
                "team": team,
                "gsis_id": f"00-{index:07d}",
                "status_description_abbr": "ACT",
                "status_short_description": "Active",
                "status": "ACT",
            }
        )
    if duplicate_first:
        rows.append(dict(rows[0]))
    return pl.DataFrame(rows)


def _audit(frame: pl.DataFrame) -> dict[str, object]:
    return audit_frame(
        season=2012,
        frame=frame,
        games=_games_2012(),
        raw_sha256="a" * 64,
        raw_size_bytes=12345,
        parquet_magic_valid=True,
        source_url="https://example.test/roster_weekly_2012.parquet",
    )


def test_historical_team_aliases_are_identity_only() -> None:
    assert normalize_team("JAC") == "JAX"
    assert normalize_team("SD") == "LAC"
    assert normalize_team("STL") == "LA"
    assert normalize_team("LAR") == "LA"
    assert normalize_team("OAK") == "LV"
    assert normalize_team("WSH") == "WAS"
    assert normalize_team("NE") == "NE"


def test_source_eras_are_not_collapsed() -> None:
    assert source_era(2012) == "data_exchange_2012_2015"
    assert source_era(2015) == "data_exchange_2012_2015"
    assert source_era(2016) == "ngs_2016_2021"
    assert source_era(2021) == "ngs_2016_2021"


def test_complete_team_game_week_source_passes_only_raw_coverage_gate() -> None:
    result = _audit(_frame_2012())
    assert result["canonical_team_game_week_coverage_rate"] == 1.0
    assert result["duplicate_non_null_gsis_player_team_week_keys"] == 0
    assert result["all_frozen_gates_pass"] is True
    assert result["weekly_roster_raw_source_coverage_qualified"] is True
    assert result["generic_status_field_present"] is True
    assert result["generic_status_used_for_audit_membership"] is False
    assert result["source_era_status_semantics_qualified"] is False
    assert result["game_day_roster_universe_qualified"] is False
    assert result["v09b_model_fit_authorized"] is False
    assert result["completed_2026_outcomes_used"] == 0


def test_one_missing_canonical_team_game_week_fails_closed() -> None:
    result = _audit(_frame_2012(drop_last=True))
    assert result["canonical_team_game_week_coverage_rate"] < 1.0
    assert len(result["missing_canonical_team_game_weeks"]) == 1
    assert result["all_frozen_gates_pass"] is False
    assert result["weekly_roster_raw_source_coverage_qualified"] is False


def test_duplicate_player_team_week_identity_fails_closed() -> None:
    result = _audit(_frame_2012(duplicate_first=True))
    assert result["canonical_team_game_week_coverage_rate"] == 1.0
    assert result["duplicate_non_null_gsis_player_team_week_keys"] == 1
    assert result["all_frozen_gates_pass"] is False


def test_missing_required_field_fails_before_semantic_inference() -> None:
    frame = _frame_2012().drop("status_description_abbr")
    result = _audit(frame)
    assert result["required_fields_present"] is False
    assert result["missing_required_fields"] == ["status_description_abbr"]
    assert result["all_frozen_gates_pass"] is False
    assert result["game_day_roster_universe_qualified"] is False


def test_status_values_are_reported_but_not_interpreted_as_labels() -> None:
    frame = _frame_2012()
    result = _audit(frame)
    assert result["status_description_abbr_distribution"] == {"ACT": 512}
    assert result["status_short_description_distribution"] == {"Active": 512}
    assert result["source_era_status_semantics_qualified"] is False
    assert result["training_label_semantics_qualified"] is False

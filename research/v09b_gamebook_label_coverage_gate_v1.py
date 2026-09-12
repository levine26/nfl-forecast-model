from __future__ import annotations

"""Fail-closed coverage gate for the frozen V09B historical P(active) label source.

This module intentionally does not discover or parse sources. It evaluates a normalized
coverage receipt produced by source-specific collectors. The collector must prove every
canonical 2012-2021 regular-season game rather than letting unavailable Game Books vanish
from the training sample.
"""

from dataclasses import dataclass
from typing import Any, Mapping

EXPECTED_GAMES_BY_SEASON = {
    2012: 256,
    2013: 256,
    2014: 256,
    2015: 256,
    2016: 256,
    2017: 256,
    2018: 256,
    2019: 256,
    2020: 256,
    2021: 272,
}
EXPECTED_TOTAL = sum(EXPECTED_GAMES_BY_SEASON.values())


@dataclass(frozen=True)
class HistoricalLabelCoverageResult:
    inactive_source_qualified: bool
    game_day_roster_universe_qualified: bool
    training_label_semantics_qualified: bool
    training_source_chronology_qualified: bool
    v09b_model_fit_authorized: bool
    blockers: tuple[str, ...]


def _rate_is_one(receipt: Mapping[str, Any], key: str) -> bool:
    try:
        return float(receipt.get(key)) == 1.0
    except (TypeError, ValueError):
        return False


def evaluate_historical_label_coverage(
    receipt: Mapping[str, Any],
    *,
    completed_2026_outcomes_used: int = 0,
) -> HistoricalLabelCoverageResult:
    if int(completed_2026_outcomes_used) != 0:
        raise ValueError("completed 2026 outcomes are prohibited in V09B label-source qualification")

    blockers: list[str] = []
    observed_counts_raw = receipt.get("canonical_games_by_season", {})
    observed_counts = {int(k): int(v) for k, v in observed_counts_raw.items()}
    if observed_counts != EXPECTED_GAMES_BY_SEASON:
        blockers.append("canonical season game counts mismatch")
    if int(receipt.get("canonical_games_total", -1)) != EXPECTED_TOTAL:
        blockers.append("canonical game total mismatch")
    if int(receipt.get("games_with_verified_source_bytes", -1)) != EXPECTED_TOTAL:
        blockers.append("not all canonical games have verified source bytes")
    if int(receipt.get("duplicate_game_source_rows", -1)) != 0:
        blockers.append("duplicate game source rows")

    for key in (
        "canonical_game_coverage_rate",
        "source_bytes_verified_rate",
        "gamebook_parse_success_rate",
        "not_active_section_present_rate",
        "did_not_play_semantically_distinguished_rate",
    ):
        if not _rate_is_one(receipt, key):
            blockers.append(key)

    inactive_source_qualified = not any(
        blocker in blockers
        for blocker in (
            "canonical season game counts mismatch",
            "canonical game total mismatch",
            "not all canonical games have verified source bytes",
            "duplicate game source rows",
            "canonical_game_coverage_rate",
            "source_bytes_verified_rate",
            "gamebook_parse_success_rate",
            "not_active_section_present_rate",
            "did_not_play_semantically_distinguished_rate",
        )
    )

    if not _rate_is_one(receipt, "game_day_roster_universe_coverage_rate"):
        blockers.append("game_day_roster_universe_coverage_rate")
    try:
        identity_rate = float(receipt.get("player_team_game_identity_resolution_rate"))
    except (TypeError, ValueError):
        identity_rate = -1.0
    if identity_rate < 0.995:
        blockers.append("player_team_game_identity_resolution_rate")
    if int(receipt.get("duplicate_player_team_game_labels", -1)) != 0:
        blockers.append("duplicate player-team-game labels")
    if int(receipt.get("contradictory_active_inactive_labels", -1)) != 0:
        blockers.append("contradictory active/inactive labels")
    if receipt.get("positive_class_requires_game_day_roster_universe") is not True:
        blockers.append("positive class denominator not explicitly roster-bounded")
    if receipt.get("active_inferred_from_postgame_participation") is not False:
        blockers.append("postgame participation used as active proxy")
    if receipt.get("weekly_roster_ina_is_label_authority") is not False:
        blockers.append("weekly roster INA used as label authority")

    roster_blockers = {
        "game_day_roster_universe_coverage_rate",
        "player_team_game_identity_resolution_rate",
        "duplicate player-team-game labels",
        "contradictory active/inactive labels",
        "positive class denominator not explicitly roster-bounded",
        "postgame participation used as active proxy",
        "weekly roster INA used as label authority",
    }
    game_day_roster_universe_qualified = not any(x in roster_blockers for x in blockers)

    semantics_qualified = inactive_source_qualified and game_day_roster_universe_qualified
    chronology_qualified = semantics_qualified and receipt.get("source_provenance_reproducible") is True
    if receipt.get("source_provenance_reproducible") is not True:
        blockers.append("source provenance not reproducible")

    authorized = semantics_qualified and chronology_qualified and not blockers
    return HistoricalLabelCoverageResult(
        inactive_source_qualified=inactive_source_qualified,
        game_day_roster_universe_qualified=game_day_roster_universe_qualified,
        training_label_semantics_qualified=semantics_qualified,
        training_source_chronology_qualified=chronology_qualified,
        v09b_model_fit_authorized=authorized,
        blockers=tuple(blockers),
    )

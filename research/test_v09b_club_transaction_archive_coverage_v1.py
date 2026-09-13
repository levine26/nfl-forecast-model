from __future__ import annotations

import json
from pathlib import Path

import requests

from research import v09b_club_transaction_archive_coverage_v1 as diag

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "research" / "availability" / "v09b_club_transaction_archive_coverage_v1_contract.json"


def _response(url: str, body: str, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.encoding = "utf-8"
    response._content = body.encode("utf-8")
    return response


def test_frozen_season_universe_is_32_unique_clubs() -> None:
    for season in diag.SEASONS:
        teams = diag.teams_for_season(season)
        assert len(teams) == 32
        assert len(set(teams)) == 32
        assert ("OAK" in teams) is (season <= 2019)
        assert ("LV" in teams) is (season >= 2020)


def test_candidate_url_is_exact_year_scoped_first_party_path() -> None:
    assert diag.candidate_urls("NE", 2017) == ["https://www.patriots.com/team/transactions/2017"]
    assert diag.candidate_urls("OAK", 2018) == ["https://www.raiders.com/team/transactions/2018"]
    assert diag.candidate_urls("WAS", 2021) == [
        "https://www.commanders.com/team/transactions/2021",
        "https://www.washingtonfootball.com/team/transactions/2021",
        "https://www.redskins.com/team/transactions/2021",
    ]


def test_response_requires_year_retaining_path_and_semantics() -> None:
    body = "<html><body><h1>TRANSACTIONS</h1><option>2021</option><h2>December</h2><p>12/23 Signed Player X.</p></body></html>"
    good = diag.evaluate_response(
        season=2021,
        domains=("buccaneers.com",),
        response=_response("https://www.buccaneers.com/team/transactions/2021", body),
    )
    assert good["qualifying_page"] is True
    assert good["observed_transaction_date_count"] == 1

    bare = diag.evaluate_response(
        season=2021,
        domains=("buccaneers.com",),
        response=_response("https://www.buccaneers.com/team/transactions/", body),
    )
    assert bare["qualifying_page"] is False
    assert bare["semantics"]["final_path_pass"] is False

    wrong_host = diag.evaluate_response(
        season=2021,
        domains=("buccaneers.com",),
        response=_response("https://www.nfl.com/team/transactions/2021", body),
    )
    assert wrong_host["qualifying_page"] is False
    assert wrong_host["semantics"]["final_host_pass"] is False


def test_response_requires_date_month_and_requested_year_signal() -> None:
    base = "https://www.chiefs.com/team/transactions/2021"
    no_date = diag.evaluate_response(
        season=2021,
        domains=("chiefs.com",),
        response=_response(base, "<h1>TRANSACTIONS</h1><p>2021 December Signed Player.</p>"),
    )
    assert no_date["qualifying_page"] is False
    assert no_date["semantics"]["transaction_date_pass"] is False

    no_year = diag.evaluate_response(
        season=2021,
        domains=("chiefs.com",),
        response=_response(base, "<h1>TRANSACTIONS</h1><p>December 12/23 Signed Player.</p>"),
    )
    assert no_year["qualifying_page"] is False
    assert no_year["semantics"]["requested_season_signal_pass"] is False


def test_aggregate_preserves_missing_pairs_and_has_no_authority() -> None:
    results = []
    for season in diag.SEASONS:
        rows = []
        teams = diag.teams_for_season(season)
        for index, team in enumerate(teams):
            found = index < 20
            rows.append({"team": team, "qualifying_archive_found": found, "candidate_attempts": []})
        results.append({
            "season": season,
            "team_season_pairs_reported": 32,
            "team_season_pairs_with_qualifying_archive": 20,
            "team_season_pairs_missing": 12,
            "coverage_fraction": 20 / 32,
            "candidate_attempt_count": 32,
            "network_or_transport_errors": 0,
            "rows": rows,
        })
    aggregate = diag.aggregate(results)
    assert aggregate["team_season_pairs_reported"] == 160
    assert aggregate["team_season_pairs_with_qualifying_archive"] == 100
    assert aggregate["team_season_pairs_missing"] == 60
    assert aggregate["coverage_fraction"] == 0.625
    assert aggregate["coverage_is_descriptive_not_qualification_gate"] is True
    assert aggregate["diagnostic_has_membership_authority"] is False
    assert aggregate["modern_game_day_roster_universe_qualified"] is False
    assert aggregate["v09b_model_fit_authorized"] is False


def test_contract_is_fail_closed_and_matches_implementation() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["contract_id"] == diag.CONTRACT_ID
    assert contract["frozen_universe"]["team_season_pairs_expected"] == 160
    assert contract["explicit_non_gates"]["coverage_threshold_for_source_qualification"] is None
    assert contract["explicit_non_gates"]["absence_of_transaction_used_as_active_evidence"] is False
    assert contract["authority"]["diagnostic_has_source_coverage_qualification_authority"] is False
    assert contract["authority"]["diagnostic_has_membership_authority"] is False
    assert contract["authority"]["modern_game_day_roster_universe_qualified"] is False
    assert contract["governance"]["completed_2026_outcomes_used"] == 0

from __future__ import annotations

import json
from pathlib import Path


POLICY = Path("research/free_only_policy.json")


def _policy() -> dict:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def test_zero_cost_policy_is_binding_and_disallows_paid_upgrade() -> None:
    policy = _policy()
    assert policy["status"] == "binding_research_constraint"
    assert policy["cost_policy"] == "free_only"
    assert policy["monthly_paid_service_budget_usd"] == 0
    assert policy["paid_data_services_authorized"] is False
    assert policy["paid_compute_authorized"] is False
    assert policy["automatic_paid_upgrade_authorized"] is False
    assert policy["supersedes_legacy_paid_source_recommendations"] is True


def test_paid_candidate_families_are_explicitly_excluded() -> None:
    policy = _policy()
    excluded = set(policy["explicitly_excluded_paid_paths"])
    assert {
        "sportradar_weekly_injuries_v7",
        "sportsdataio_injuries",
        "sis_football_commercial",
        "pff_pro_api",
        "sumersports_subscription_stats",
        "paid_the_odds_api_historical",
        "paid_github_larger_runners",
    }.issubset(excluded)


def test_free_market_path_cannot_call_paid_historical_endpoint() -> None:
    policy = _policy()
    paths = {row["source_id"]: row for row in policy["approved_zero_cost_paths"]}
    odds = paths["the_odds_api_free_tier"]
    assert odds["cost_status"] == "free_tier_only"
    assert "historical endpoints are prohibited" in odds["endpoint_policy"].lower()
    assert "fail closed" in odds["quota_policy"].lower()


def test_free_personnel_state_never_impersonates_injury_availability() -> None:
    policy = _policy()["availability_policy"]
    assert policy["injury_probability_feature_status"] == "blocked_until_free_point_in_time_source_qualifies"
    assert policy["free_personnel_state_path"] == "timestamped_nflverse_depth_charts_plus_rosters"
    assert policy["personnel_state_is_not_injury_status"] is True
    assert policy["realized_snap_or_postgame_participation_proxy_allowed"] is False


def test_new_sources_and_models_remain_nonproduction_by_default() -> None:
    policy = _policy()["production_policy"]
    assert policy["new_source_production_authorized"] is False
    assert policy["new_model_production_authorized"] is False
    assert policy["explicit_user_authorization_still_required"] is True

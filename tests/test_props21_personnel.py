from datetime import datetime, timezone

from nfl_forecast.props21_personnel import adapt_personnel_evidence, build_personnel_intelligence


FORECAST = "2026-09-19T20:00:00+00:00"
KICKOFF = "2026-09-20T17:00:00+00:00"


def player(player_id="qb2", name="Backup Quarterback", position="QB"):
    return {"game_id": "g", "team": "ATL", "player_id": player_id,
            "player_name": name, "position": position, "kickoff_timestamp": KICKOFF}


def evidence(kind, *, stamp="2026-09-19T18:00:00+00:00", player_id="qb2"):
    return {"game_id": "g", "team": "ATL", "player_id": player_id,
            "evidence_type": kind, "source": "NFL.com", "source_url": "https://www.nfl.com/news/item",
            "source_kind": "official", "qualification_state": "QUALIFIED",
            "timestamp": stamp, "capture_timestamp": stamp}


def test_replacement_starter_and_out_are_separate_fail_closed_states():
    result = build_personnel_intelligence(
        [player(), player("qb1", "Injured Quarterback")],
        [evidence("REPLACEMENT_STARTER"), evidence("OUT", player_id="qb1")],
        forecast_timestamp=FORECAST, kickoff_timestamp=KICKOFF,
    )
    states = {row["player_id"]: row for row in result["states"]}
    assert states["qb2"]["role_state"] == "STARTER_EXPECTED"
    assert states["qb2"]["workload_multiplier"] is None
    assert states["qb1"]["role_state"] == "OUT"
    assert states["qb1"]["opportunity_policy"] == "ZERO_OPPORTUNITY"
    assert states["qb1"]["workload_multiplier"] == 0.0


def test_limited_and_committee_states_never_assert_normal_workload():
    result = build_personnel_intelligence(
        [player("rb1", "Runner One", "RB")],
        [evidence("WORKLOAD_LIMITED", player_id="rb1"), evidence("COMMITTEE_UNCERTAIN", player_id="rb1")],
        forecast_timestamp=FORECAST, kickoff_timestamp=KICKOFF,
    )
    state = result["states"][0]
    assert state["role_state"] == "WORKLOAD_LIMITED"
    assert state["workload_state"] == "LIMITED"
    assert state["workload_multiplier"] is None
    assert state["opportunity_policy"] == "BLOCK_ROLE_DEPENDENT_SIGNAL"


def test_future_stale_and_unresolved_evidence_are_rejected():
    result = build_personnel_intelligence(
        [player()],
        [evidence("STARTER_CONFIRMED", stamp="2026-09-20T18:00:00+00:00"),
         evidence("STARTER_EXPECTED", stamp="2026-09-15T18:00:00+00:00"),
         evidence("STARTER_EXPECTED", player_id="missing")],
        forecast_timestamp=FORECAST, kickoff_timestamp=KICKOFF,
    )
    reasons = {row["rejection_reason"] for row in result["evidence"]}
    assert {"FUTURE_EVIDENCE", "STALE_EVIDENCE", "UNRESOLVED_PLAYER_IDENTITY"} <= reasons
    assert result["states"][0]["role_state"] == "UNKNOWN"


def test_naive_timestamp_is_not_point_in_time_evidence():
    row = evidence("STARTER_CONFIRMED")
    row["capture_timestamp"] = "2026-09-19T18:00:00"
    result = build_personnel_intelligence([player()], [row], forecast_timestamp=FORECAST,
                                          kickoff_timestamp=KICKOFF)
    assert result["evidence"][0]["rejection_reason"] == "MISSING_AWARE_TIMESTAMP"
    assert datetime.fromisoformat(result["forecast_timestamp"]).tzinfo == timezone.utc


def test_qualified_current_reporting_converts_subject_bound_google_rss_title():
    manifest = {"game_id": "g", "kickoff_utc": KICKOFF}
    payload = {"generated_utc": FORECAST, "g": {"current_reported_sources": [{
        "title": "Seahawks’ Backup Quarterback Auditioning for QB-Needy Teams With Start at Cardinals",
        "source_name": "Sports Illustrated",
        "source_url": "https://news.google.com/rss/articles/example",
        "as_of": "2026-09-19T18:00:00+00:00",
    }]}}
    adapted = adapt_personnel_evidence(manifest, [player()], payload)
    result = build_personnel_intelligence(adapted["player_state"], adapted["evidence"],
                                          forecast_timestamp=FORECAST, kickoff_timestamp=KICKOFF)
    assert result["states"][0]["role_state"] == "STARTER_EXPECTED"
    assert result["audit"]["accepted_evidence"] == 1



def test_timestamped_structured_official_availability_joins_exact_canonical_player():
    manifest = {"game_id": "g", "kickoff_utc": KICKOFF}
    payload = {
        "generated_utc": FORECAST,
        "g": {
            "matchup_meter": [{
                "family": "availability",
                "title": "ATL: Runner One — Out",
                "source_name": "NFL.com official injury report",
                "as_of": "2026-09-19T18:00:00+00:00",
            }],
            "evidence_used": [{
                "category": "personnel",
                "title": "ATL: Runner One — Out",
                "source_name": "NFL.com official injury report",
                "source_url": "https://www.nfl.com/injuries/league/2026/reg2",
            }],
        },
    }
    adapted = adapt_personnel_evidence(
        manifest,
        [player("rb1", "Runner One", "RB")],
        payload,
    )
    structured = [
        row for row in adapted["evidence"]
        if row.get("qualification_reference") == "sunday_signal:structured_official_availability"
    ]
    assert len(structured) == 1
    assert structured[0]["evidence_type"] == "OUT"
    result = build_personnel_intelligence(
        adapted["player_state"],
        adapted["evidence"],
        forecast_timestamp=FORECAST,
        kickoff_timestamp=KICKOFF,
    )
    state = result["states"][0]
    assert state["availability_state"] == "OUT"
    assert state["role_state"] == "OUT"
    assert state["workload_multiplier"] == 0.0


def test_structured_availability_fails_closed_without_timestamp_or_official_url():
    manifest = {"game_id": "g", "kickoff_utc": KICKOFF}
    base = {
        "family": "availability",
        "title": "ATL: Runner One — Questionable",
        "source_name": "NFL.com official injury report",
    }
    payload = {
        "generated_utc": FORECAST,
        "g": {
            "matchup_meter": [base],
            "evidence_used": [{
                "category": "personnel",
                "title": base["title"],
                "source_name": base["source_name"],
                "source_url": "https://example.com/injury",
            }],
        },
    }
    adapted = adapt_personnel_evidence(
        manifest,
        [player("rb1", "Runner One", "RB")],
        payload,
    )
    assert not [
        row for row in adapted["evidence"]
        if row.get("qualification_reference") == "sunday_signal:structured_official_availability"
    ]


def test_rank1_depth_chart_is_categorical_starter_evidence_only():
    manifest = {"game_id": "g", "kickoff_utc": KICKOFF}
    runner = player("rb1", "Runner One", "RB")
    adapted = adapt_personnel_evidence(
        manifest,
        [runner],
        {},
        depth_charts=[{
            "dt": "2026-09-19T18:00:00+00:00",
            "capture_timestamp": "2026-09-19T19:00:00+00:00",
            "team": "ATL",
            "gsis_id": "rb1",
            "pos_rank": 1,
            "position": "RB",
        }],
    )
    result = build_personnel_intelligence(
        adapted["player_state"],
        adapted["evidence"],
        forecast_timestamp=FORECAST,
        kickoff_timestamp=KICKOFF,
    )
    state = result["states"][0]
    assert state["role_state"] == "STARTER_EXPECTED"
    assert state["workload_state"] == "UNKNOWN"
    assert state["workload_multiplier"] is None
    assert state["news_coverage"] is False
    assert "ROLE_UNCERTAIN" in state["uncertainties"]
    assert "MISSING_CURRENT_NEWS_COVERAGE" in state["uncertainties"]

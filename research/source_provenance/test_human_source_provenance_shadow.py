from __future__ import annotations

import json

import pytest

from research.source_provenance.audit_human_source_provenance_shadow import (
    SlateProvenanceError, audit_game, audit_slate, validate_active_slate,
)


def _candidate(tmp_path, gid="2026_05_TB_DAL"):
    packet = {"games": {gid: {
        "headline": "Independent pregame tactical analysis",
        "paragraph1": "Human analysis never certifies itself.",
        "sources": [
            {"title": "Buccaneers pregame report", "url": "https://www.buccaneers.com/news/alpha"},
            {"title": "Cowboys pregame report", "url": "https://www.dallascowboys.com/news/bravo"},
        ],
    }}}
    (tmp_path / f"{gid}.json").write_text(json.dumps(packet), encoding="utf-8")
    return gid


def _fetch(url, *, expected_title, away_name, home_name):
    assert away_name == "Buccaneers"
    assert home_name == "Cowboys"
    home = "dallascowboys" in url
    return {
        "publisher_family": "dallascowboys.com" if home else "buccaneers.com",
        "article_title": expected_title,
        "retrieved_utc": "2026-10-10T12:00:00+00:00",
        "published_or_updated_raw": "2026-10-07",
        "content_sha256": "a" * 64,
        "extracted_body_sha256": "b" * 64,
        "article_resolution_verified": True,
        "reported_teams": ["Cowboys"] if home else ["Buccaneers"],
        "body_text": "A real verified publisher article body (not persisted).",
    }


def test_two_fetched_independent_team_reports_only_verify_article_identity(tmp_path):
    gid = _candidate(tmp_path)
    report = audit_game(gid, input_dir=tmp_path, fetch=_fetch)
    assert report["article_resolution_verified"] is True
    assert report["claim_support_verified"] is False
    assert report["publication_authorized"] is False
    assert report["issues"] == ["semantic_claim_support_not_verified"]
    assert all("body_text" not in x for x in report["sources"])
    assert all(x["claim_entailment_verified"] is False for x in report["sources"])


def test_one_failed_source_does_not_prevent_diagnostic_for_other(tmp_path):
    gid = _candidate(tmp_path)
    seen = []

    def one_missing(url, **kwargs):
        seen.append(url)
        if "dallascowboys" in url:
            raise ConnectionError("simulated outage")
        return _fetch(url, **kwargs)

    report = audit_game(gid, input_dir=tmp_path, fetch=one_missing)
    assert len(seen) == 2
    assert report["article_resolution_verified"] is False
    assert report["claim_support_verified"] is False
    assert any("simulated outage" in x for x in report["issues"])


def test_duplicate_publisher_is_rejected_without_semantic_promotion(tmp_path):
    gid = _candidate(tmp_path)

    def duplicate(url, **kwargs):
        report = _fetch(url, **kwargs)
        report["publisher_family"] = "same-publisher.com"
        return report

    report = audit_game(gid, input_dir=tmp_path, fetch=duplicate)
    assert report["article_resolution_verified"] is False
    assert any("independent_two_team_coverage" in x for x in report["issues"])


def test_missing_candidate_is_isolated_not_slate_abort(tmp_path):
    good = _candidate(tmp_path)
    missing = "2026_05_DEN_LAC"
    result = audit_slate({"game_ids": [good, missing]}, input_dir=tmp_path, fetch=_fetch, max_workers=2)
    assert result["games_expected"] == 2
    assert result["games_with_verified_article_resolutions"] == 1
    assert result["games_with_verified_claim_support"] == 0
    assert result["full_slate_article_resolution_verified"] is False
    assert result["full_slate_claim_support_verified"] is False
    assert result["publication_authorized"] is False
    assert any("missing_or_invalid_candidate" in s for s in result["games"][missing]["issues"])


@pytest.mark.parametrize("ids", [[], ["same", "same"], ["2026_05_TB_DAL", 123], "not_a_list"])
def test_manifest_rejects_invalid_roster_ids(tmp_path, ids):
    with pytest.raises(SlateProvenanceError):
        audit_slate({"game_ids": ids}, input_dir=tmp_path, fetch=_fetch)


def test_report_never_changes_authored_input_or_produces_release_file(tmp_path):
    gid = _candidate(tmp_path)
    path = tmp_path / f"{gid}.json"
    before = path.read_bytes()
    report = audit_slate({"game_ids": [gid]}, input_dir=tmp_path, fetch=_fetch)
    assert path.read_bytes() == before
    assert report["full_slate_article_resolution_verified"] is True
    assert report["full_slate_claim_support_verified"] is False
    assert report["publication_authorized"] is False



def _current_forecast_csv(tmp_path, ids):
    p = tmp_path / "this_week.csv"
    rows = ["game_id,season,week,away_team,home_team"]
    for gid in ids:
        year, week, away, home = gid.split("_")
        rows.append(f"{gid},{year},{int(week)},{away},{home}")
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p


def _frozen_roster(tmp_path, *, week, ids):
    p = tmp_path / "historical_roster.json"
    p.write_text(json.dumps({"season": 2026, "week": week, "frozen": True,
                             "game_ids": ids}), encoding="utf-8")
    return p


def test_current_week_audit_accepts_manifest_without_mutating_frozen_prior_week(tmp_path):
    current_ids = ["2026_05_TB_DAL", "2026_05_PHI_JAX"]
    active = _current_forecast_csv(tmp_path, current_ids)
    frozen = _frozen_roster(tmp_path, week=4, ids=["2026_04_PIT_CLE"])
    frozen_bytes = frozen.read_bytes()
    active_bytes = active.read_bytes()
    status = validate_active_slate({"game_ids": list(reversed(current_ids))},
                                   current_csv=active, historical_roster=frozen)
    assert status["games_expected"] == 2
    assert status["season"] == 2026 and status["week"] == 5
    assert status["canonical_game_ids"] == sorted(current_ids)
    assert status["historical_roster_status"] == "different_week_historical_not_authoritative"
    assert status["publication_authorized"] is False
    assert frozen.read_bytes() == frozen_bytes
    assert active.read_bytes() == active_bytes


def test_same_week_frozen_roster_cannot_disagree_with_live_forecasts(tmp_path):
    active = _current_forecast_csv(tmp_path, ["2026_05_TB_DAL", "2026_05_PHI_JAX"])
    frozen = _frozen_roster(tmp_path, week=5, ids=["2026_05_TB_DAL"])
    with pytest.raises(SlateProvenanceError, match="same-week frozen roster differs"):
        validate_active_slate(
            {"game_ids": ["2026_05_TB_DAL", "2026_05_PHI_JAX"]},
            current_csv=active, historical_roster=frozen,
        )


def test_missing_or_extra_game_cannot_pass_current_slate_even_at_same_cardinality(tmp_path):
    active = _current_forecast_csv(tmp_path, ["2026_05_TB_DAL", "2026_05_PHI_JAX"])
    missing_roster = tmp_path / "missing.json"
    with pytest.raises(SlateProvenanceError, match="ACTIVE canonical forecast"):
        validate_active_slate(
            {"game_ids": ["2026_05_TB_DAL", "2026_05_CHI_GB"]},
            current_csv=active, historical_roster=missing_roster,
        )


@pytest.mark.parametrize("bad_ids", [
    ["2026_05_TB_DAL", "2026_05_TB_DAL"],
    ["2026_05_TB_DAL", "2026_06_PHI_JAX"],
])
def test_duplicate_or_mixed_week_forecasts_fail_closed(tmp_path, bad_ids):
    active = _current_forecast_csv(tmp_path, bad_ids)
    with pytest.raises(SlateProvenanceError):
        validate_active_slate({"game_ids": bad_ids}, current_csv=active,
                              historical_roster=tmp_path / "absent.json")


def test_missing_active_forecast_never_falls_back_to_old_roster(tmp_path):
    frozen = _frozen_roster(tmp_path, week=4, ids=["2026_04_PIT_CLE"])
    with pytest.raises(SlateProvenanceError, match="active canonical forecast CSV unavailable"):
        validate_active_slate({"game_ids": ["2026_05_TB_DAL"]},
                              current_csv=tmp_path / "missing.csv",
                              historical_roster=frozen)

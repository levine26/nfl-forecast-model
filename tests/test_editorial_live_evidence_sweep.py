from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nfl_forecast.editorial_article_capture import ArticleCaptureError
from scripts.editorial_live_evidence_sweep import audit_slate, write_report


NOW = datetime(2026, 10, 10, 23, 0, tzinfo=timezone.utc)
DET = "2026_05_DET_ARI"
CLE = "2026_05_CLE_NYJ"


def rows():
    return [
        {"game_id": DET, "away_team": "DET", "home_team": "ARI"},
        {"game_id": CLE, "away_team": "CLE", "home_team": "NYJ"},
    ]


def candidates():
    return {
        DET: {"sources": [
            {"title": "Cardinals rookie tackle against Detroit", "url": "https://www.azcardinals.com/news/rookie-vs-lions"},
            {"title": "Lions prepare for Arizona", "url": "https://www.detroitlions.com/news/matchup-lions-vs-cardinals"},
        ]},
        CLE: {"sources": [
            {"title": "Jets Browns defensive matchups", "url": "https://www.newyorkjets.com/news/jets-browns"},
            {"title": "Browns game preview against New York", "url": "https://www.clevelandbrowns.com/news/browns-jets"},
        ]},
    }


def _capture(url, **kwargs):
    families = {
        "azcardinals.com": ("azcardinals.com", ["Arizona Cardinals"]),
        "detroitlions.com": ("detroitlions.com", ["Detroit Lions"]),
        "newyorkjets.com": ("newyorkjets.com", ["New York Jets"]),
        "clevelandbrowns.com": ("clevelandbrowns.com", ["Cleveland Browns"]),
    }
    domain = next(key for key in families if key in url)
    fam, teams = families[domain]
    return {
        "article_resolution_verified": True,
        "url": url,
        "article_title": kwargs["expected_title"],
        "publisher_family": fam,
        "content_sha256": "a" * 64,
        "extracted_body_sha256": "b" * 64,
        "retrieved_utc": NOW.isoformat(),
        "reported_teams": teams,
        "body_text": "This should never appear in the published audit.",
    }


def test_sweep_processes_all_games_and_never_grants_publication():
    report = audit_slate(rows(), candidates(), capture=_capture, now=NOW)
    assert report["status"] == "shadow_provenance_complete"
    assert report["games_expected"] == 2
    assert report["games_with_two_resolved_independent_reporters"] == 2
    assert report["editorial_publication_authorized"] is False
    assert report["fact_checking_complete"] is False
    assert report["games"][DET]["semantic_claim_entailment_verified"] is False
    assert "body_text" not in report["games"][DET]["source_checks"][0]


def test_all_source_failures_collected_without_skipping_later_games():
    seen = []

    def fail_first(url, **kwargs):
        seen.append(url)
        if "azcardinals" in url or "newyorkjets" in url:
            raise ArticleCaptureError("publisher content unavailable or source title incorrect")
        return _capture(url, **kwargs)

    report = audit_slate(rows(), candidates(), capture=fail_first, now=NOW)
    assert len(seen) == 4  # every independent source attempted
    assert report["games_with_two_resolved_independent_reporters"] == 0
    assert report["status"] == "shadow_provenance_incomplete"
    assert report["games"][DET]["source_checks"][0]["status"] == "rejected"
    assert report["games"][CLE]["source_checks"][0]["reason"].startswith("publisher content")


def test_duplicate_publisher_sources_do_not_count_as_independent():
    c = candidates()
    c[DET]["sources"][1]["url"] = "https://www.azcardinals.com/news/other-article"
    report = audit_slate([rows()[0]], {DET: c[DET]}, capture=_capture, now=NOW)
    assert report["games"][DET]["status"] == "provenance_incomplete"
    assert "independence_or_combined_coverage" in " ".join(report["games"][DET]["errors"])


def test_missing_game_does_not_hide_other_games():
    c = candidates()
    del c[CLE]
    report = audit_slate(rows(), c, capture=_capture, now=NOW)
    assert "game_has_no_human_candidate" in report["games"][CLE]["errors"]
    assert report["games"][DET]["status"] == "provenance_candidates_resolved"
    assert report["games"]["__slate__"]["missing_candidates"] == [CLE]


def test_atomic_shadow_report_is_explicitly_not_a_publication(tmp_path: Path):
    path = tmp_path / "research_outputs" / "editorial" / "sweep.json"
    report = audit_slate(rows(), candidates(), capture=_capture, now=NOW)
    write_report(path, report)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["editorial_publication_authorized"] is False
    assert stored["games"][DET]["status"] == "provenance_candidates_resolved"
    assert not any(file.suffix == ".tmp" for file in path.parent.iterdir())


def test_third_unresolved_citation_blocks_provenance_even_if_two_others_work():
    c = candidates()
    c[DET]["sources"].append({
        "title": "Purported late injury report",
        "url": "https://www.detroitlions.com/news/bad-404-article",
    })

    def partial(url, **kwargs):
        if "bad-404" in url:
            raise ArticleCaptureError("source HTTP status 404, not article success")
        return _capture(url, **kwargs)

    report = audit_slate([rows()[0]], {DET: c[DET]}, capture=partial, now=NOW)
    assert report["games_with_two_resolved_independent_reporters"] == 0
    assert report["games"][DET]["status"] == "provenance_incomplete"
    assert "source[2]_not_retrieved_or_verified" in report["games"][DET]["errors"]
    assert len(report["games"][DET]["source_checks"]) == 3


def test_real_publisher_heading_mismatch_not_marked_verified():
    def misleading_heading(url, **kwargs):
        report = _capture(url, **kwargs)
        if "azcardinals" in url:
            report["article_title"] = "Unrelated Cardinals article from another week"
        return report

    report = audit_slate([rows()[0]], {DET: candidates()[DET]},
                         capture=misleading_heading, now=NOW)
    assert report["games"][DET]["status"] == "provenance_incomplete"
    assert "source[0]_not_retrieved_or_verified" in report["games"][DET]["errors"]
    assert "headline differs" in report["games"][DET]["source_checks"][0]["reason"]

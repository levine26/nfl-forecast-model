from __future__ import annotations

import json
from hashlib import sha256

from scripts.audit_editorial_sources_shadow import audit_candidates


SLATE = [
    {"game_id": "2026_05_CLE_NYJ", "away_team": "CLE", "home_team": "NYJ"},
    {"game_id": "2026_05_DEN_LAC", "away_team": "DEN", "home_team": "LAC"},
]


def write_candidate(folder, game_id, sources):
    (folder / f"{game_id}.json").write_text(
        json.dumps({"games": {game_id: {"sources": sources}}}), encoding="utf-8",
    )


def source(url, title):
    return {"url": url, "title": title}


def fake_report(url, *, expected_title, away_name, home_name):
    if "broken" in url:
        raise ValueError("source page is unrelated to game")
    team = away_name if "away" in url else home_name
    domain = "publisher-a.example" if "away" in url else "publisher-b.example"
    return {
        "url": url,
        "publisher_family": domain,
        "article_title": expected_title,
        "published_or_updated_raw": "2026-10-09T11:00:00Z",
        "retrieved_utc": "2026-10-10T11:00:00+00:00",
        "content_sha256": sha256(url.encode()).hexdigest(),
        "extracted_body_sha256": sha256(expected_title.encode()).hexdigest(),
        "reported_teams": [team],
        "article_resolution_verified": True,
        "body_text": "This should never appear in any persisted audit.",
    }


def test_full_slate_captures_two_independent_sources_per_game_without_authorizing(tmp_path):
    for row in SLATE:
        write_candidate(tmp_path, row["game_id"], [
            source(f"https://away.example/news/{row['game_id']}", "Away feature"),
            source(f"https://home.example/news/{row['game_id']}", "Home feature"),
        ])
    result = audit_candidates(SLATE, tmp_path, fetcher=fake_report)
    assert result["games_expected"] == 2
    assert result["games_with_verified_article_provenance"] == 2
    assert result["article_provenance_status"] == "complete"
    assert result["games_with_verified_semantic_claims"] == 0
    assert result["semantic_claim_entailment_verified"] is False
    assert result["editorial_publication_authorized"] is False
    for game in result["games"].values():
        assert game["errors"] == []
        assert len(game["sources"]) == 2
        assert len(game["candidate_sha256"]) == 64
        assert all(s["semantic_claim_entailment_verified"] is False for s in game["sources"])
        assert "body_text" not in game["sources"][0]
        assert game["editorial_publication_authorized"] is False


def test_collects_every_source_and_game_failure_not_fail_fast(tmp_path):
    write_candidate(tmp_path, SLATE[0]["game_id"], [
        source("https://broken.example/news/1", "Wrong content"),
        source("https://home.example/news/2", "Valid home report"),
    ])
    write_candidate(tmp_path, SLATE[1]["game_id"], [
        source("https://broken.example/news/3", "Wrong another"),
        source("https://broken.example/news/4", "Another failure"),
    ])
    result = audit_candidates(SLATE, tmp_path, fetcher=fake_report)
    assert result["games_with_verified_article_provenance"] == 0
    assert result["article_provenance_status"] == "incomplete"
    assert "source_1:ValueError" in result["games"][SLATE[0]["game_id"]]["errors"][0]
    assert len(result["games"][SLATE[1]["game_id"]]["errors"]) >= 3
    assert result["editorial_publication_authorized"] is False


def test_missing_candidate_and_corrupt_sources_return_specific_blockers(tmp_path):
    write_candidate(tmp_path, SLATE[0]["game_id"], [])
    result = audit_candidates(SLATE, tmp_path, fetcher=fake_report)
    assert all(x["status"] == "source_blocked" for x in result["games"].values())
    assert result["games"][SLATE[1]["game_id"]]["errors"][0].startswith("candidate_unavailable")


def test_duplicate_or_invalid_canonical_slate_refused(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="duplicate"):
        audit_candidates(SLATE + [SLATE[0]], tmp_path, fetcher=fake_report)
    with pytest.raises(ValueError, match="team"):
        audit_candidates([dict(SLATE[0], away_team="UNKNOWN")], tmp_path, fetcher=fake_report)


def test_repeated_one_publisher_cannot_count_as_independent(tmp_path):
    gid = SLATE[0]["game_id"]
    write_candidate(tmp_path, gid, [
        source("https://away.example/one", "one"),
        source("https://away.example/two", "two"),
    ])
    result = audit_candidates([SLATE[0]], tmp_path, fetcher=fake_report)
    assert result["games"][gid]["status"] == "source_blocked"
    assert "two independently verified" in str(result["games"][gid]["errors"])


def test_capture_is_shadow_only_and_never_overwrites_numerical_outputs():
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1] /
              "scripts/audit_editorial_sources_shadow.py").read_text()
    assert '"editorial_publication_authorized": False' in script
    assert '"semantic_claim_entailment_verified": False' in script
    assert "write_text" in script
    assert 'args.out.write_text' in script
    assert 'outputs/this_week.csv' in script  # read-only input
    assert 'outputs/context_source_status.json' not in script
    assert 'outputs/copilot_media_reads.json' not in script

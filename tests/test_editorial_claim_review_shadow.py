from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.prepare_editorial_claim_review_shadow import review_queue


def make_slate(tmp_path: Path, game_ids=None):
    ids = game_ids if game_ids is not None else ["2026_05_TB_DAL", "2026_05_NYG_WAS"]
    path = tmp_path / "this_week.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["game_id", "away_team", "home_team"])
        writer.writeheader()
        for gid in ids:
            writer.writerow({"game_id": gid, "away_team": "TB", "home_team": "DAL"})
    return path


def make_candidate(tmp_path: Path, game_id: str, *, inject_fake_approval=False):
    directory = tmp_path / "fallback"
    directory.mkdir(exist_ok=True)
    entry = {
        "headline": "Real football matchup",
        "paragraph1": "Dallas defended the middle. Tampa Bay adjusted its protections and looked outside.",
        "sources": [
            {"title": "Source One", "url": "https://www.buccaneers.com/news/story-a"},
            {"title": "Source Two", "url": "https://www.dallascowboys.com/news/story-b"},
        ],
    }
    if inject_fake_approval:
        entry["semantic_claim_entailment_verified"] = True
        entry["editorial_publication_authorized"] = True
    (directory / f"{game_id}.json").write_text(
        json.dumps({"games": {game_id: entry}}), encoding="utf-8"
    )
    return directory


def test_review_queue_includes_every_game_and_each_sentence(tmp_path):
    slate = make_slate(tmp_path)
    directory = make_candidate(tmp_path, "2026_05_TB_DAL")
    make_candidate(tmp_path, "2026_05_NYG_WAS")
    queue = review_queue(slate, directory)
    assert queue["games_expected"] == queue["games_queued"] == 2
    assert queue["sentences_queued"] == 4
    assert len(queue["canonical_slate_sha256"]) == 64
    assert queue["editorial_publication_authorized"] is False
    for game in queue["games"].values():
        assert game["status"] == "pending_independent_clause_and_claim_review"
        assert len(game["candidate_file_sha256"]) == 64
        assert len(game["human_paragraph_sha256"]) == 64
        assert len(game["sentences"]) == 2
        assert all(s["semantic_claim_entailment_verified"] is False for s in game["sentences"])
        assert all(s["all_factual_clauses_enumerated"] is False for s in game["sentences"])
        assert all(s["independent_reviewer_attestation"] is None for s in game["sentences"])


def test_llm_supplied_verified_flags_never_become_release_receipts(tmp_path):
    slate = make_slate(tmp_path, ["2026_05_TB_DAL"])
    directory = make_candidate(tmp_path, "2026_05_TB_DAL", inject_fake_approval=True)
    item = review_queue(slate, directory)
    assert item["semantic_claim_entailment_verified"] is False
    assert item["editorial_publication_authorized"] is False
    assert not any(x["semantic_claim_entailment_verified"] for x in item["games"]["2026_05_TB_DAL"]["sentences"])


def test_missing_candidate_produces_per_game_issue_without_dropping_game(tmp_path):
    slate = make_slate(tmp_path)
    directory = make_candidate(tmp_path, "2026_05_TB_DAL")
    queue = review_queue(slate, directory)
    assert queue["games_queued"] == 2
    assert queue["games"]["2026_05_NYG_WAS"]["status"] == "candidate_blocked"
    assert queue["games"]["2026_05_NYG_WAS"]["issues"] == ["candidate_unavailable:FileNotFoundError"]


def test_canonical_duplicate_game_rejected(tmp_path):
    slate = make_slate(tmp_path, ["2026_05_TB_DAL", "2026_05_TB_DAL"])
    with pytest.raises(ValueError, match="unique"):
        review_queue(slate, tmp_path)


def test_changed_candidate_changes_fingerprint(tmp_path):
    slate = make_slate(tmp_path, ["2026_05_TB_DAL"])
    directory = make_candidate(tmp_path, "2026_05_TB_DAL")
    first = review_queue(slate, directory)
    file = directory / "2026_05_TB_DAL.json"
    updated = json.loads(file.read_text())
    updated["games"]["2026_05_TB_DAL"]["paragraph1"] += " Dallas adjusted."
    file.write_text(json.dumps(updated))
    second = review_queue(slate, directory)
    left = first["games"]["2026_05_TB_DAL"]
    right = second["games"]["2026_05_TB_DAL"]
    assert left["candidate_file_sha256"] != right["candidate_file_sha256"]
    assert left["human_paragraph_sha256"] != right["human_paragraph_sha256"]
    assert len(right["sentences"]) == 3

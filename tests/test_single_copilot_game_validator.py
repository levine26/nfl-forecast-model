from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "validate_single_copilot_game.py"
spec = importlib.util.spec_from_file_location("validate_single_copilot_game", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_headline_template_catches_team_swapped_stock_structure():
    a = module._headline_template(
        "Dolphins–Raiders: Dolphins pass rush vs. Raiders protection", "MIA", "LV"
    )
    b = module._headline_template(
        "Packers–Vikings: Packers pass rush vs. Vikings protection", "GB", "MIN"
    )
    assert a == b


def test_source_gate_requires_two_independent_direct_domains():
    _, families, failures = module._valid_sources([
        {"name": "ESPN", "title": "One", "url": "https://www.espn.com/nfl/story/_/id/1/one"},
        {"name": "ESPN", "title": "Two", "url": "https://www.espn.com/nfl/story/_/id/2/two"},
    ])
    assert len(families) == 1
    assert any("two independent" in failure for failure in failures)

    _, families, failures = module._valid_sources([
        {"name": "ESPN", "title": "One", "url": "https://www.espn.com/nfl/story/_/id/1/one"},
        {"name": "NFL", "title": "Two", "url": "https://www.nfl.com/news/two"},
    ])
    assert len(families) == 2
    assert not failures


def test_focused_source_gate_uses_deterministic_backfill_before_rejecting(monkeypatch):
    provider_sources = [
        {
            "name": "ESPN",
            "title": "Bears at Panthers preview",
            "url": "https://www.espn.com/nfl/preview/_/gameId/401872661",
        }
    ]
    repaired = [
        {
            "name": "CBS Sports",
            "title": "Bears Panthers matchup report",
            "url": "https://www.cbssports.com/nfl/news/bears-panthers-matchup-report/",
        },
        {
            "name": "Panthers",
            "title": "Panthers prepare for Chicago",
            "url": "https://www.panthers.com/news/panthers-prepare-for-chicago",
        },
    ]

    def fake_backfill(row, existing_sources):
        assert row["away_team"] == "CHI"
        assert row["home_team"] == "CAR"
        assert existing_sources == provider_sources
        return repaired

    monkeypatch.setattr(module, "backfill_direct_sources", fake_backfill)
    valid, families, failures = module._valid_sources_with_backfill(
        {"away_team": "CHI", "home_team": "CAR"}, provider_sources
    )
    assert len(valid) == 2
    assert len(families) == 2
    assert not failures


def test_focused_source_backfill_still_fails_closed_without_two_families(monkeypatch):
    provider_sources = [
        {
            "name": "ESPN",
            "title": "Bears at Panthers preview",
            "url": "https://www.espn.com/nfl/preview/_/gameId/401872661",
        }
    ]
    monkeypatch.setattr(
        module,
        "backfill_direct_sources",
        lambda row, sources: [
            {
                "name": "ESPN",
                "title": "One direct report",
                "url": "https://www.espn.com/nfl/story/_/id/123/one-direct-report",
            }
        ],
    )
    valid, families, failures = module._valid_sources_with_backfill(
        {"away_team": "CHI", "home_team": "CAR"}, provider_sources
    )
    assert len(valid) == 1
    assert families == {"espn.com"}
    assert any("two independent" in failure for failure in failures)


def test_underlength_rationale_repair_is_narrow_matchup_specific_and_contract_safe():
    row = pd.Series({"away_team": "TB", "home_team": "CIN", "pick": "CIN"})
    rationale = "Cincinnati can control the game if its offense stays ahead of pressure."
    paragraph1 = (
        "Tampa Bay must manage Cincinnati pressure with a disciplined protection plan, "
        "while the Bengals need their front to keep the Buccaneers behind schedule."
    )
    repaired, changed = module._repair_underlength_rationale(rationale, paragraph1, row)
    assert changed
    assert 18 <= len(module._words(repaired)) <= 40
    assert "Bengals" in repaired
    assert "Buccaneers" in repaired
    assert rationale.rstrip(".") in repaired
    assert not module._rationale_has_prohibited(repaired)


def test_too_short_clean_fragment_is_rebuilt_from_researched_mechanism():
    row = pd.Series({"away_team": "CHI", "home_team": "CAR", "pick": "CHI"})
    rationale = "Chicago must protect its quarterback."
    paragraph1 = (
        "The Bears protection plan has to withstand Panthers pressure, especially when "
        "Carolina can force longer downs and let its pass rush attack the pocket."
    )
    repaired, changed = module._repair_underlength_rationale(rationale, paragraph1, row)
    assert changed
    assert 18 <= len(module._words(repaired)) <= 40
    assert "Bears" in repaired
    assert "Panthers" in repaired
    assert repaired != rationale
    assert not module._rationale_has_prohibited(repaired)


def test_rationale_repair_refuses_one_to_three_words_prohibited_or_unrecognized_copy():
    row = pd.Series({"away_team": "TB", "home_team": "CIN", "pick": "CIN"})
    pressure_paragraph = "The Bengals pressure Tampa Bay while the Buccaneers adjust their protection."

    too_small = "Pressure matters."
    repaired, changed = module._repair_underlength_rationale(too_small, pressure_paragraph, row)
    assert not changed
    assert repaired == too_small

    prohibited = "Cincinnati has a market edge if pressure works."
    repaired, changed = module._repair_underlength_rationale(prohibited, pressure_paragraph, row)
    assert not changed
    assert repaired == prohibited

    no_mechanism = "Cincinnati needs a sharper start."
    neutral_paragraph = "The Bengals and Buccaneers each need cleaner execution for four quarters."
    repaired, changed = module._repair_underlength_rationale(no_mechanism, neutral_paragraph, row)
    assert not changed
    assert repaired == no_mechanism


def test_validate_persists_repaired_rationale_and_exact_passing_sources(tmp_path):
    gid = "2026_01_TB_CIN"
    paragraph1 = (
        "Buccaneers protection has to handle Cincinnati pressure without forcing rushed throws, while Tampa Bay can help with motion and quick-game answers. "
        "The Bengals need their front to win enough early downs to avoid obvious passing situations, and Cincinnati's secondary must tackle cleanly after the catch. "
        "That protection-versus-pressure exchange should shape both teams' third-down options and determine which offense can stay on schedule."
    )
    payload = {
        "games": {
            gid: {
                "headline": "Bengals pressure tests Buccaneers protection plan",
                "paragraph1": paragraph1,
                "model_rationale": "Cincinnati can control the game if its offense stays ahead of pressure.",
                "sources": [
                    {
                        "name": "ESPN",
                        "title": "Buccaneers Bengals matchup report",
                        "url": "https://www.espn.com/nfl/story/_/id/123/buccaneers-bengals-matchup-report",
                    },
                    {
                        "name": "NFL.com",
                        "title": "Bengals prepare for Tampa Bay",
                        "url": "https://www.nfl.com/news/bengals-prepare-for-tampa-bay",
                    },
                ],
            }
        }
    }
    path = tmp_path / f"{gid}.txt"
    path.write_text(json.dumps(payload), encoding="utf-8")
    predictions = pd.DataFrame([
        {"game_id": gid, "away_team": "TB", "home_team": "CIN", "pick": "CIN"}
    ])

    failures = module.validate(path, gid, predictions)
    assert not failures

    saved = json.loads(path.read_text(encoding="utf-8"))["games"][gid]
    repaired = saved["model_rationale"]
    assert 18 <= len(re.findall(r"\b[\w'-]+\b", repaired)) <= 40
    assert "Bengals" in repaired and "Buccaneers" in repaired
    assert not module._rationale_has_prohibited(repaired)
    assert [source["name"] for source in saved["sources"]] == ["ESPN", "NFL.com"]


def test_validate_persists_rebuilt_too_short_rationale(tmp_path):
    gid = "2026_01_CHI_CAR"
    paragraph1 = (
        "Chicago needs its protection to handle Carolina pressure without letting obvious passing downs dictate the game. "
        "The Bears can help with quick throws and movement, while the Panthers need their front to collapse the pocket before routes develop. "
        "If Carolina cannot create that pressure, Chicago can stay balanced and make the Panthers defend the entire field instead of attacking predictable dropbacks."
    )
    payload = {
        "games": {
            gid: {
                "headline": "Bears protection faces Panthers pressure test",
                "paragraph1": paragraph1,
                "model_rationale": "Chicago must protect its quarterback.",
                "sources": [
                    {
                        "name": "CBS Sports",
                        "title": "Bears Panthers matchup report",
                        "url": "https://www.cbssports.com/nfl/news/bears-panthers-matchup-report/",
                    },
                    {
                        "name": "Panthers",
                        "title": "Panthers prepare for Chicago",
                        "url": "https://www.panthers.com/news/panthers-prepare-for-chicago",
                    },
                ],
            }
        }
    }
    path = tmp_path / f"{gid}.txt"
    path.write_text(json.dumps(payload), encoding="utf-8")
    predictions = pd.DataFrame([
        {"game_id": gid, "away_team": "CHI", "home_team": "CAR", "pick": "CHI"}
    ])

    failures = module.validate(path, gid, predictions)
    assert not failures
    saved = json.loads(path.read_text(encoding="utf-8"))["games"][gid]
    repaired = saved["model_rationale"]
    assert 18 <= len(module._words(repaired)) <= 40
    assert "Bears" in repaired and "Panthers" in repaired
    assert repaired != "Chicago must protect its quarterback."
    assert not module._rationale_has_prohibited(repaired)


def test_source_gate_rejects_generic_team_schedule_game_and_stats_pages():
    generic = [
        {"name": "NFL", "title": "Chargers team", "url": "https://www.nfl.com/teams/los-angeles-chargers/"},
        {"name": "Chargers", "title": "Schedule", "url": "https://www.chargers.com/schedule/"},
        {"name": "NFL", "title": "Game", "url": "https://www.nfl.com/games/bills-at-texans-2026-reg-1"},
        {"name": "ESPN", "title": "Giants team page", "url": "https://www.espn.com/nfl/team/_/name/nyg/new-york-giants"},
        {"name": "NGS", "title": "Passing stats", "url": "https://nextgenstats.nfl.com/stats/quarterbacks/2025/REG/all"},
    ]
    valid, families, failures = module._valid_sources(generic)
    assert not valid
    assert not families
    assert sum("not a direct approved article/report" in failure for failure in failures) == len(generic)


def test_official_team_news_article_counts_as_direct_reporting():
    valid, families, failures = module._valid_sources([
        {"name": "Colts", "title": "Colts report", "url": "https://www.colts.com/news/example-report"},
        {"name": "NFL", "title": "NFL report", "url": "https://www.nfl.com/news/example-report"},
    ])
    assert len(valid) == 2
    assert len(families) == 2
    assert not failures


def test_x_and_twitter_are_one_source_family():
    _, families, failures = module._valid_sources([
        {"name": "Reporter A", "title": "One", "url": "https://x.com/reporter/status/123456789"},
        {"name": "Reporter B", "title": "Two", "url": "https://twitter.com/reporter2/status/987654321"},
    ])
    assert families == {"x.com"}
    assert any("two independent" in failure for failure in failures)


def test_seven_word_substantive_phrase_collision_is_detectable():
    a = "turn its explosive play threat into steady production now"
    b = "Miami can turn its explosive play threat into steady production now"
    assert module._unique_ngrams(a) & module._unique_ngrams(b)


def test_standardized_injury_report_phrase_is_exempt_from_uniqueness_collision():
    a = "The receiver did not participate in practice on Wednesday because of a hamstring issue."
    b = "The tackle did not participate in practice on Wednesday because of an ankle issue."
    assert not (module._unique_ngrams(a) & module._unique_ngrams(b))

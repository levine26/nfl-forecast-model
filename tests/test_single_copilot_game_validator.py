from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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

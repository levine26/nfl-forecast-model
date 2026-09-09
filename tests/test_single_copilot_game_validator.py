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


def test_seven_word_human_phrase_collision_is_detectable():
    a = "turn its explosive play threat into steady production now"
    b = "Miami can turn its explosive play threat into steady drives"
    assert module._ngrams(a) & module._ngrams(b)

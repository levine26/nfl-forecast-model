from __future__ import annotations

from pathlib import Path

import pytest

from nfl_forecast.player_impact_cards import build_payload, validate_card, validate_impact, validate_observed_stat
from scripts.build_player_impact_cards import example_card


def test_example_card_keeps_observed_and_modeled_information_separate():
    card = example_card()
    validate_card(card)
    assert all(row["kind"] == "source_observed" for row in card["observed_statistics"])
    assert all(row["kind"] == "levline_modeled_impact" for row in card["levline_impacts"])
    payload = build_payload([card], generated_utc="test")
    assert payload["mode"] == "research_only"
    assert payload["public_site_consumes_this_file"] is False
    assert payload["fantasy_style_projections"] is False


def test_fantasy_style_projection_metrics_are_rejected():
    stat = example_card()["observed_statistics"][0].copy()
    stat["metric"] = "projected yardage"
    with pytest.raises(ValueError):
        validate_observed_stat(stat)

    impact = example_card()["levline_impacts"][0].copy()
    impact["metric"] = "touchdown probability"
    with pytest.raises(ValueError):
        validate_impact(impact)


def test_modeled_impact_cannot_be_called_an_official_nfl_statistic():
    impact = example_card()["levline_impacts"][0].copy()
    impact["interpretation"] = "Official NFL modeled impact statistic"
    with pytest.raises(ValueError, match="official NFL statistic"):
        validate_impact(impact)


def test_stable_identity_is_required():
    card = example_card()
    card["player_id"] = ""
    with pytest.raises(ValueError, match="Stable player_id"):
        validate_card(card)


def test_live_site_has_no_player_impact_card_consumer():
    site = Path("site")
    matches = []
    if site.exists():
        for path in site.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".json", ".html"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "player_impact_cards" in text or "levline_player_impact" in text:
                    matches.append(str(path))
    assert matches == []

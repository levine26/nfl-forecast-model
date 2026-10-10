import pandas as pd

from nfl_forecast.editorial_acceptance import audit_editorial_acceptance


def _frame():
    return pd.DataFrame([
        {"game_id": "g1", "away_team": "TB", "home_team": "DAL"},
        {"game_id": "g2", "away_team": "PHI", "home_team": "JAX"},
    ])


def _preview(away: str, home: str, unique: str):
    p1 = (
        f"{away} must account for the defense's changing coverage rotations after the snap, "
        f"especially when the opponent walks a safety toward the line. "
        f"{home} can counter by threatening the flats before attacking the seams, "
        f"but a healthy run game changes the spacing decisions considerably. "
        f"The key is how {away} adjusts protection with a tight end attached; "
        f"that decision could force {home} to declare its pressure look and "
        f"make the matchup's critical third downs easier to anticipate. {unique}"
    )
    return {
        "headline": f"{away} and {home}: distinct pressure and coverage responses {unique}",
        "paragraphs": [p1, f"Deterministic forecast explanation. The pick: {home} moneyline."],
        "editorial_voice": {"copilot_researched": True},
        "reported_sources": [
            {"source_url": "https://www.nfl.com/news/a-game-report"},
            {"source_url": "https://www.cbssports.com/nfl/news/a-game-report"},
        ],
    }


def test_no_provider_must_not_be_healthy_even_if_finalizer_is_healthy():
    games = {"g1": _preview("Buccaneers", "Cowboys", "Dallas adjustments"),
             "g2": _preview("Eagles", "Jaguars", "Jacksonville spacing")}
    for p in games.values():
        p["editorial_voice"]["copilot_researched"] = False
    result = audit_editorial_acceptance(_frame(), games)
    assert result["status"] == "degraded"
    assert result["games_with_structurally_eligible_human_reads"] == 0
    assert all("no_accepted_provider_human_read" in result["issues"][gid] for gid in ("g1", "g2"))


def test_rejects_repeatable_injury_led_fallback_and_intermediary_sources():
    games = {"g1": _preview("Buccaneers", "Cowboys", "Dallas adjustments"),
             "g2": _preview("Eagles", "Jaguars", "Jacksonville spacing")}
    games["g1"]["paragraphs"][0] = (
        "Buccaneers–Cowboys centers on TB: Baker Mayfield — Out. "
        "The official NFL injury report lists Baker Mayfield as out. "
        "LevLine does not make up an injury point value for it. " * 4
    )
    games["g1"]["reported_sources"] = [
        {"source_url": "https://news.google.com/rss/articles/abc"},
        {"source_url": "http://www.bing.com/news/apiclick.aspx?url=https://www.nfl.com/news/report"},
    ]
    result = audit_editorial_acceptance(_frame(), games)
    assert "mechanical_injury_or_stock_template" in result["issues"]["g1"]
    assert "fewer_than_two_independent_direct_report_url_candidates" in result["issues"]["g1"]


def test_two_https_source_shapes_do_not_claim_article_or_fact_verification():
    result = audit_editorial_acceptance(_frame(), {
        "g1": _preview("Buccaneers", "Cowboys", "Dallas adjustments"),
        "g2": _preview("Eagles", "Jaguars", "Jacksonville spacing"),
    })
    assert result["article_resolution_verified"] is False
    assert result["claim_support_verified"] is False
    assert result["games_expected"] == 2
    # Eligible is deliberately a structural precondition, never a claim that pages were fetched.
    assert result["status"] in {"structurally_eligible", "degraded"}


def test_missing_game_or_duplicate_ids_fails_closed():
    result = audit_editorial_acceptance(_frame(), {"g1": _preview("Buccaneers", "Cowboys", "Dallas adjustments")})
    assert result["status"] == "degraded"
    assert "g2" in result["issues"]
    assert "__slate__" in result["issues"]


def test_syntactically_plausible_same_publisher_is_not_independent():
    games = {"g1": _preview("Buccaneers", "Cowboys", "Dallas adjustments"),
             "g2": _preview("Eagles", "Jaguars", "Jacksonville spacing")}
    games["g2"]["reported_sources"] = [
        {"source_url": "https://www.nfl.com/news/a-game-report"},
        {"source_url": "https://www.nfl.com/news/a-second-report"},
    ]
    assert "fewer_than_two_independent_direct_report_url_candidates" in audit_editorial_acceptance(_frame(), games)["issues"]["g2"]

def test_public_display_strips_search_intermediaries_and_only_retains_direct_sources():
    from scripts.finalize_editorial import _display_media

    items = {
        "g1": [
            {"title": "Cowboys Buccaneers game context",
             "source_url": "https://news.google.com/rss/articles/abc"},
            {"title": "Dallas defensive adjustments vs Tampa Bay",
             "source_url": "https://www.nfl.com/news/cowboys-buccaneers-defensive-adjustments"},
            {"title": "How the Buccaneers attack Dallas coverage",
             "source_url": "https://www.cbssports.com/nfl/news/buccaneers-cowboys-coverage"},
        ]
    }
    visible, counts = _display_media(items)
    assert counts["intermediary_only_urls_rejected"] == 1
    assert counts["games_with_two_independent_direct_report_url_candidates"] == 1
    assert len(visible["g1"]) == 2
    assert all("news.google.com" not in item["source_url"] for item in visible["g1"])


def test_public_display_does_not_invent_source_link_from_publisher_name():
    from scripts.finalize_editorial import _display_media

    media = {"g1": [{"source_name": "Associated Press",
                     "title": "A plausible matchup report",
                     "source_url": "https://www.bing.com/news/apiclick.aspx?id=opaque"}]}
    displayed, counts = _display_media(media)
    assert displayed == {}
    assert counts["games_with_display_reporting"] == 0
    assert counts["intermediary_only_urls_rejected"] == 1

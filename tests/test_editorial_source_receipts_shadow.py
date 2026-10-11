from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from nfl_forecast.editorial_source_receipts_shadow import (
    EvidenceInsufficient, verify_retrieved_article, audit_matchup_receipts
)


GAME = "2026_05_DET_ARI"
TEAMS = {"DET": ["Detroit Lions", "Lions"], "ARI": ["Arizona Cardinals", "Cardinals"]}
AZ_URL = "https://www.azcardinals.com/news/cardinals-rookie-tackle-prepares-for-lions-pass-rush"
DET_URL = "https://www.detroitlions.com/news/lions-cardinals-pass-rush-tactical-preparation"


def _article(url=AZ_URL, title="Cardinals rookie tackle faces Lions pass rush",
             body=None, status=200):
    body = body or (
        "The Arizona Cardinals are preparing their rookie left tackle to face the "
        "Detroit Lions edge pressure this weekend. The rookie tackle will have "
        "veteran help beside him while the Lions bring pressure from the edge. "
        "Protection communication matters for Arizona because Detroit can switch "
        "from a four man rush to an overloaded front after the offense shifts its "
        "formation. The Cardinals plan to use backs and tight ends to help "
        "identify pressure while their receivers occupy deeper coverage. "
        "Detroit expects its interior rush to compress the pocket and limit "
        "the ability of the quarterback to escape through the middle of the "
        "field. The pass protection group must work together throughout the game "
        "as the defense changes its front before the snap and makes the "
        "quarterback adjust his reads and progression. "
    )
    now = datetime.now(timezone.utc) - timedelta(minutes=30)
    return {
        "status_code": status,
        "final_url": url,
        "title": title,
        "article_text": body,
        "published_utc": (now-timedelta(hours=2)).isoformat(),
        "retrieved_utc": now.isoformat(),
    }


def _claim():
    return [{"statement": "Arizona can protect its rookie tackle using veteran support",
             "supporting_excerpt": (
                 "The rookie tackle will have veteran help beside him while the "
                 "Lions bring pressure from the edge"
             )}]


def _verify(url=AZ_URL, title="Cardinals rookie tackle faces Lions pass rush",
            fetched=None, claims=None, teams=None):
    return verify_retrieved_article(
        game_id=GAME, candidate_url=url, candidate_title=title,
        fetched=_article(url, title) if fetched is None else fetched,
        claims=_claim() if claims is None else claims,
        team_aliases=TEAMS if teams is None else teams,
    )


def test_real_resolved_reporting_creates_receipt_but_not_semantic_attestation():
    receipt = _verify()
    assert receipt["game_id"] == GAME
    assert len(receipt["article_content_sha256"]) == 64
    assert receipt["url_title_and_quote_presence_verified"] is True
    assert receipt["semantic_claim_entailment_verified"] is False
    assert receipt["verification_status"] == "quote_present_semantic_review_required"


def test_http_404_fabricated_article_url_is_rejected():
    with pytest.raises(EvidenceInsufficient, match="did not resolve"):
        _verify(fetched=_article(status=404))


def test_wrong_article_title_is_rejected_even_on_real_domain():
    with pytest.raises(EvidenceInsufficient, match="title"):
        _verify(fetched=_article(title="Different news report"))


def test_generic_how_to_watch_fails_direct_reporting_gate():
    url = "https://www.detroitlions.com/news/lions-at-cardinals-how-to-watch-listen-and-follow-2026"
    title = "Lions at Cardinals: How to watch, listen and follow"
    with pytest.raises(EvidenceInsufficient, match="generic viewing"):
        _verify(url=url, title=title, fetched=_article(url=url, title=title))


def test_wrong_team_article_fails_even_with_legitimate_url():
    body = (
        "Baltimore Ravens and Atlanta Falcons are evaluating quarterback protection "
        "and defensive rotations over the next game. "
    ) * 13
    with pytest.raises(EvidenceInsufficient, match="wrong-team"):
        _verify(fetched=_article(body=body))


def test_hallucinated_quote_fails_before_claim_approval():
    with pytest.raises(EvidenceInsufficient, match="does not appear"):
        _verify(claims=[{"statement": "invented fact", "supporting_excerpt":
                         "No quarterback has ever thrown an interception against this team"}])


def test_unapproved_and_redirected_hosts_fail_closed():
    with pytest.raises(EvidenceInsufficient, match="redirected|non-report"):
        _verify(url="https://www.azcardinals.com.evil.example/news/story",
                fetched=_article(url="https://www.azcardinals.com.evil.example/news/story"))
    with pytest.raises(EvidenceInsufficient, match="redirected|non-report"):
        _verify(fetched=_article(url="https://www.azcardinals.com/news/other-story"))


def test_two_independent_sources_cover_both_teams_without_authorizing_publish():
    first = _verify()
    title = "Lions defenders prepare for Arizona attack"
    second = _verify(
        url=DET_URL, title=title,
        fetched=_article(url=DET_URL, title=title),
    )
    packet = audit_matchup_receipts([first, second], game_id=GAME, teams=["DET", "ARI"])
    assert packet["independent_source_count"] == 2
    assert packet["teams_covered"] == ["ARI", "DET"]
    assert packet["editorial_publication_authorized"] is False


def test_duplicate_family_and_wrong_game_packets_rejected():
    first = _verify()
    with pytest.raises(EvidenceInsufficient, match="independent"):
        audit_matchup_receipts([first, first], game_id=GAME, teams=["DET", "ARI"])
    second = dict(first, game_id="2026_05_PHI_JAX")
    with pytest.raises(EvidenceInsufficient, match="mismatched game"):
        audit_matchup_receipts([first, second], game_id=GAME, teams=["DET", "ARI"])


def test_article_publish_timestamp_cannot_postdate_retrieval():
    fake = _article()
    fake["published_utc"] = (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    with pytest.raises(EvidenceInsufficient, match="postdates retrieval"):
        _verify(fetched=fake)


def test_active_cardinals_official_article_domain_is_allowlisted():
    from nfl_forecast.source_policy import is_direct_media_report_url
    assert is_direct_media_report_url("https://www.azcardinals.com/news/3x3-week-5-cardinals-vs-lions")
    assert not is_direct_media_report_url("https://www.azcardinals.com.evil.example/news/same-story")

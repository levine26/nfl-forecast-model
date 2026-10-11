from __future__ import annotations

from datetime import datetime, timezone
import pytest

from nfl_forecast.editorial_article_capture import (
    ArticleCaptureError, capture_report, capture_and_verify_source, locate_quote, require_independent_publishers,
)


JETS_URL = "https://www.newyorkjets.com/news/jets-browns-game-preview-2026"
BROWNS_URL = "https://www.clevelandbrowns.com/news/browns-jets-game-preview-2026"
ARTICLE_TITLE = "Jets-Browns Game Preview | Knowing the Stakes"
NOW = datetime(2026, 10, 10, 23, 0, tzinfo=timezone.utc)
MATCHUP = {"away_name": "Cleveland Browns", "home_name": "New York Jets"}


def article_html(
    title=ARTICLE_TITLE, *,
    body=None,
):
    if body is None:
        body = (
            "The New York Jets prepare to host the Cleveland Browns with coverage and protection "
            "details shaping Sunday's game. Garrett Wilson will meet Denzel Ward in several matchups. "
            "The Jets can counter Cleveland's pressure with underneath timing routes, while Browns "
            "rushers can change their approach by disguising coverage. The quarterbacks each must "
            "handle early downs effectively and avoid rushed throws, because both defenses can "
            "challenge the timing of longer completions. The New York Jets have emphasized faster "
            "starts, while the Cleveland Browns have continued to rely on their physical defense. "
            "The results should depend on protection calls and tackling after short receptions."
        )
    return (
        '<html><head><meta property="article:published_time" content="2026-10-10T18:00:00Z"></head>'
        f'<body><nav>Advertising betting odds schedule.</nav><article><h1>{title}</h1>'
        f'<p>{body}</p></article><footer>All news</footer></body></html>'
    ).encode()


class Response:
    def __init__(self, code=200, body=None, mime="text/html"):
        self.status_code = code
        self.content = article_html() if body is None else body
        self.headers = {"content-type": mime}
        self.closed = False
        self.chunks_seen = 0

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self.content), chunk_size):
            self.chunks_seen += 1
            yield self.content[i:i + chunk_size]

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def capture(url=JETS_URL, *, response=None, title=ARTICLE_TITLE):
    sess = FakeSession(response or Response())
    record = capture_report(
        url, expected_title=title, session=sess, now=NOW, **MATCHUP,
    )
    assert sess.calls[0][1] == {"timeout": 9, "allow_redirects": False, "stream": True}
    return record


def test_captures_actual_html_article_content_not_generic_url_shape():
    record = capture()
    assert record["article_resolution_verified"] is True
    assert record["claim_entailment_verified"] is False
    assert record["quote_location_verified"] is False
    assert record["publisher_family"] == "newyorkjets.com"
    assert len(record["content_sha256"]) == 64
    assert "Advertising betting odds" not in record["body_text"]
    assert record["published_or_updated_raw"] == "2026-10-10T18:00:00Z"


def test_cannot_claim_source_truth_from_a_located_quote():
    record = capture()
    excerpt = "Garrett Wilson will meet Denzel Ward in several matchups."
    quote = locate_quote(record, quote=excerpt)
    assert quote["verification_status"] == "quote_located_entailment_unverified"
    assert quote["content_sha256"] == record["content_sha256"]
    assert record["claim_entailment_verified"] is False
    with pytest.raises(ArticleCaptureError, match="not present"):
        locate_quote(record, quote="A fabricated quote completely absent from the source document.")


def test_rejects_fabricated_url_navigation_page_and_unapproved_host():
    for url in [
        "https://unknown.example.com/news/something",
        "https://www.newyorkjets.com/team/roster",
        "http://www.newyorkjets.com/news/jets-browns-game-preview-2026",
        "https://user:password@www.newyorkjets.com/news/preview",
        "https://www.newyorkjets.com:444/news/preview",
    ]:
        with pytest.raises(ArticleCaptureError):
            capture(url)
    with pytest.raises(ArticleCaptureError, match="source HTTP status 404"):
        capture(response=Response(code=404))


def test_rejects_wrong_team_article_and_nonarticle_shell():
    unrelated = ("The Detroit Lions will play the Chicago Bears in Chicago. " * 15).strip()
    with pytest.raises(ArticleCaptureError, match="does not cover either matchup team"):
        capture(response=Response(body=article_html(body=unrelated)))
    with pytest.raises(ArticleCaptureError, match="navigation shell"):
        capture(response=Response(body=article_html(body="New York Jets Cleveland Browns preview.")))


def test_rejects_generic_betting_or_viewing_title_and_lied_about_title():
    with pytest.raises(ArticleCaptureError, match="generic or missing"):
        capture(
            response=Response(body=article_html(title="How to watch Jets vs Browns")),
            title="How to watch Jets vs Browns",
        )
    with pytest.raises(ArticleCaptureError, match="contradicts cited title"):
        capture(
            response=Response(body=article_html(title="Browns and Jets tactical preview")),
            title="Miami Dolphins and Buffalo Bills offensive scheme report",
        )


def test_rejects_redirects_non_html_and_oversized_response():
    with pytest.raises(ArticleCaptureError, match="HTTP status 302"):
        capture(response=Response(code=302))
    with pytest.raises(ArticleCaptureError, match="did not return HTML"):
        capture(response=Response(mime="application/pdf"))
    with pytest.raises(ArticleCaptureError, match="exceeds"):
        capture(response=Response(body=b"x" * 1_000_001))


def test_requires_two_distinct_successful_publisher_content_receipts():
    one = capture()
    other = dict(one, publisher_family="clevelandbrowns.com")
    require_independent_publishers([one, other])
    with pytest.raises(ArticleCaptureError, match="two independently verified"):
        require_independent_publishers([one, one])
    with pytest.raises(ArticleCaptureError, match="fewer than two"):
        require_independent_publishers([one])
    with pytest.raises(ArticleCaptureError, match="two independently verified"):
        require_independent_publishers([one, dict(other, article_resolution_verified=False)])


def test_article_scoped_title_takes_priority_over_branding_page_h1():
    rich_body = article_html().decode()
    page = rich_body.replace(
        '<body><nav>',
        '<body><h1>New York Jets Official Website</h1><nav>',
    ).encode()
    record = capture(response=Response(body=page))
    assert record["article_title"] == ARTICLE_TITLE


def test_actual_week5_groq_cbs_viewing_betting_source_is_rejected():
    # Original Groq TB_DAL checkpoint was structurally accepted despite this
    # publicly resolving to a viewing/prediction/odds article, not direct reporting.
    url = "https://www.cbssports.com/nfl/news/cowboys-vs-buccaneers-prediction-where-to-watch-tnf/"
    title = "Where to watch Cowboys vs. Buccaneers: Prediction, pick, odds, streaming for TNF"
    with pytest.raises(ArticleCaptureError, match="generic or missing"):
        capture(url=url, response=Response(body=article_html(title=title)), title=title)


def test_streamed_large_response_aborts_before_full_download_and_closes():
    body = b"x" * 2_000_000
    response = Response(body=body)
    with pytest.raises(ArticleCaptureError, match="exceeds"):
        capture(response=response)
    assert response.closed
    assert response.chunks_seen < 25  # never consumes full oversized content


def test_one_sided_reporting_is_accepted_per_source_but_pair_covers_both():
    jets_body = (
        "The New York Jets prepare to adjust defensive looks around their front seven and "
        "change pressure packages to protect the secondary when the passing rhythm shifts. "
        * 7
    )
    browns_body = (
        "The Cleveland Browns have been working on protection calls and passing concepts "
        "because their offensive staff expects complicated coverage changes after the snap. "
        * 7
    )
    one = capture(response=Response(body=article_html(body=jets_body)))
    other = capture(url=BROWNS_URL, response=Response(body=article_html(body=browns_body)))
    assert one["reported_teams"] == ["New York Jets"]
    assert other["reported_teams"] == ["Cleveland Browns"]
    require_independent_publishers(
        [one, other], expected_teams=list(MATCHUP.values()),
    )
    with pytest.raises(ArticleCaptureError, match="both matchup teams"):
        require_independent_publishers(
            [one, dict(other, reported_teams=["New York Jets"])],
            expected_teams=list(MATCHUP.values()),
        )


def test_real_capture_flows_into_single_shadow_validator_and_stays_unverified_semantically():
    paragraph = (
        "The Jets can counter Cleveland's pressure with underneath timing routes, while Browns "
        "rushers can change their approach by disguising coverage."
    )
    assert paragraph in article_html().decode()
    receipt = capture_and_verify_source(
        game_id="2026_05_CLE_NYJ",
        url=JETS_URL,
        expected_title=ARTICLE_TITLE,
        team_aliases={"CLE": ["Cleveland Browns", "Browns"],
                      "NYJ": ["New York Jets", "Jets"]},
        claims=[{"statement": "The Jets have an underneath passing response to pressure",
                 "supporting_excerpt": paragraph}],
        session=FakeSession(Response()),
        now=NOW,
    )
    assert receipt["verification_status"] == "quote_present_semantic_review_required"
    assert receipt["semantic_claim_entailment_verified"] is False
    assert receipt["url_title_and_quote_presence_verified"] is True
    assert len(receipt["http_content_sha256"]) == 64


def test_combined_verifier_rejects_fake_quoted_evidence():
    with pytest.raises(ValueError, match="supporting excerpt"):
        capture_and_verify_source(
            game_id="2026_05_CLE_NYJ",
            url=JETS_URL,
            expected_title=ARTICLE_TITLE,
            team_aliases={"CLE": ["Cleveland Browns", "Browns"],
                          "NYJ": ["New York Jets", "Jets"]},
            claims=[{"statement": "The Jets practice underwater",
                     "supporting_excerpt": "No real paragraph in the original article says that underwater football is required for both teams to play."}],
            session=FakeSession(Response()),
            now=NOW,
        )

from __future__ import annotations

from nfl_forecast.direct_report_resolution import resolve_original_report_url


class _Response:
    def __init__(self, status_code=302, location=None):
        self.status_code = status_code
        self.headers = {"Location": location} if location else {}
        self.closed = False

    def close(self):
        self.closed = True


class _Session:
    def __init__(self, mapping):
        self.mapping = mapping
        self.visited = []
        self.responses = []

    def get(self, url, **kwargs):
        self.visited.append((url, kwargs))
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        response = self.mapping[url]
        self.responses.append(response)
        return response


def test_passthrough_for_direct_original_publisher_candidate_without_fetch():
    session = _Session({})
    url = "https://www.nfl.com/news/example-matchup-report"
    resolved, state = resolve_original_report_url(url, session=session)
    assert (resolved, state) == (url, "direct_url_candidate")
    assert not session.visited


def test_bing_search_result_redirect_resolves_to_original_article():
    gateway = "https://www.bing.com/news/apiclick.aspx?ref=FexRss"
    direct = "https://www.espn.com/nfl/story/_/id/12345/example"
    session = _Session({gateway: _Response(location=direct)})
    resolved, state = resolve_original_report_url(gateway, session=session)
    assert resolved == direct
    assert state == "gateway_redirect_publisher_candidate"
    assert all(response.closed for response in session.responses)


def test_bing_explicit_url_requires_a_safe_direct_report_not_homepage():
    raw = "https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fwww.nfl.com%2Fnews%2Foriginal-report"
    direct, status = resolve_original_report_url(raw, session=_Session({}))
    assert direct == "https://www.nfl.com/news/original-report"
    assert status == "gateway_embedded_publisher_candidate"
    assert resolve_original_report_url(
        "https://www.bing.com/news/apiclick.aspx?url=http%3A%2F%2F127.0.0.1%2Fsecret",
        session=_Session({"https://www.bing.com/news/apiclick.aspx?url=http%3A%2F%2F127.0.0.1%2Fsecret": _Response(200)}),
    )[0] == ""


def test_gateway_never_follows_untrusted_or_internal_redirect():
    gateway = "https://news.google.com/rss/articles/example"
    session = _Session({gateway: _Response(location="http://127.0.0.1/private")})
    direct, state = resolve_original_report_url(gateway, session=session)
    assert direct == "" and state == "unapproved_redirect_destination"
    assert len(session.visited) == 1


def test_follow_only_approved_redirect_hops_and_reject_cycles():
    first = "https://news.google.com/rss/articles/example"
    second = "https://news.google.com/articles/alternate"
    direct = "https://apnews.com/article/example-matchup-report"
    session = _Session({first: _Response(location=second),second:_Response(location=direct)})
    assert resolve_original_report_url(first, session=session)[0] == direct
    assert len(session.visited) == 2
    cycle = _Session({first:_Response(location=second),second:_Response(location=first)})
    assert resolve_original_report_url(first, session=cycle)[1] == "unsafe_or_cyclic_redirect"


def test_wrong_scheme_credentials_port_and_search_homepage_fail():
    for url in (
        "http://www.nfl.com/news/report",
        "https://user:pass@news.google.com/rss/articles/id",
        "https://www.bing.com:444/news/search",
        "https://www.nfl.com/teams/atlanta-falcons/",
        "https://127.0.0.1/path",
    ):
        direct, state = resolve_original_report_url(url, session=_Session({}))
        assert direct == "" and state == "unapproved_discovery_url"

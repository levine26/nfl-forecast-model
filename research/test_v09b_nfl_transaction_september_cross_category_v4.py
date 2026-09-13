from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from research import v09b_nfl_transaction_september_cross_category_v4 as m


def _contract():
    return {
        "scope": {
            "month": 9,
            "url_template": "https://amp.nfl.com/transactions/league/{category}/{season}/{month}",
        }
    }


def test_endpoint_url_uses_frozen_amp_surface():
    assert m._endpoint_url(_contract(), season=2021, category="waivers") == "https://amp.nfl.com/transactions/league/waivers/2021/9"


def test_next_after_values_extracts_only_same_path_and_dedupes():
    html = """
    <a href="/transactions/league/signings/2021/9?after=abc%3D">Next</a>
    <a href="https://www.nfl.com/transactions/league/signings/2021/9?after=abc%3D">duplicate</a>
    <a href="/transactions/league/waivers/2021/9?after=wrong">wrong path</a>
    <a href="/transactions/league/signings/2021/9?before=prev">Previous</a>
    """
    assert m._next_after_values(
        html,
        "https://amp.nfl.com/transactions/league/signings/2021/9",
        "/transactions/league/signings/2021/9",
    ) == ["abc="]


def test_amp_cursor_url_preserves_endpoint_path_and_cursor():
    url = m._amp_cursor_url("https://amp.nfl.com/transactions/league/other/2017/9", "A+B=")
    p = urlparse(url)
    assert p.hostname == "amp.nfl.com"
    assert p.path == "/transactions/league/other/2017/9"
    assert parse_qs(p.query)["after"] == ["A+B="]


def test_validate_final_rejects_host_or_path_escape():
    path = "/transactions/league/trades/2020/9"
    allowed = {"amp.nfl.com", "www.nfl.com"}
    m._validate_final("https://amp.nfl.com" + path, path, allowed)
    with pytest.raises(ValueError):
        m._validate_final("https://example.com" + path, path, allowed)
    with pytest.raises(ValueError):
        m._validate_final("https://amp.nfl.com/transactions/league/trades/2020/10", path, allowed)


def test_evidence_found_requires_exact_name_and_transaction_substring():
    endpoints = [{
        "season": 2021,
        "category": "trades",
        "pages": [{"rows": [{"name": "Bradley Roby", "transaction": "Traded from Texans to Saints"}]}],
    }]
    assert m._evidence_found(endpoints, {"season": 2021, "category": "trades", "name": "Bradley Roby", "transaction_contains": "Traded"})
    assert not m._evidence_found(endpoints, {"season": 2021, "category": "trades", "name": "Brad Roby", "transaction_contains": "Traded"})

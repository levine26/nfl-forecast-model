from __future__ import annotations

import gzip
from urllib.parse import parse_qs, urlparse

import pytest

from research import v09b_nfl_transaction_full_ledger_capture_v5 as m


def _contract():
    return {
        "scope": {
            "url_template": "https://amp.nfl.com/transactions/league/{category}/{year}/{month}",
        }
    }


def test_endpoint_url_preserves_year_month_category():
    assert m._endpoint_url(_contract(), year=2019, month=12, category="reserve-list") == (
        "https://amp.nfl.com/transactions/league/reserve-list/2019/12"
    )


def test_endpoint_url_rejects_unsafe_category():
    with pytest.raises(ValueError):
        m._endpoint_url(_contract(), year=2019, month=12, category="../escape")


def test_amp_cursor_url_roundtrips_cursor():
    url = m._amp_cursor_url(
        "https://amp.nfl.com/transactions/league/signings/2020/10",
        "A+B/C=",
    )
    p = urlparse(url)
    assert p.hostname == "amp.nfl.com"
    assert p.path == "/transactions/league/signings/2020/10"
    assert parse_qs(p.query)["after"] == ["A+B/C="]


def test_next_after_values_is_same_path_only():
    html = """
    <a href="/transactions/league/waivers/2020/10?after=a%3D">Next</a>
    <a href="https://www.nfl.com/transactions/league/waivers/2020/10?after=a%3D">Duplicate</a>
    <a href="/transactions/league/waivers/2020/11?after=b">Wrong month</a>
    """
    assert m._next_after_values(
        html,
        "https://amp.nfl.com/transactions/league/waivers/2020/10",
        "/transactions/league/waivers/2020/10",
    ) == ["a="]


def test_raw_gzip_is_deterministic_and_exact(tmp_path):
    raw = b"source bytes\nwith transaction table\n"
    a = tmp_path / "a.html.gz"
    b = tmp_path / "b.html.gz"
    ra = m._write_raw_gzip(raw, a)
    rb = m._write_raw_gzip(raw, b)
    assert a.read_bytes() == b.read_bytes()
    assert gzip.decompress(a.read_bytes()) == raw
    assert ra["raw_sha256"] == rb["raw_sha256"] == m._sha(raw)
    assert ra["gzip_roundtrip_matches"] is True


def test_validate_final_rejects_host_or_path_escape():
    path = "/transactions/league/trades/2018/4"
    allowed = {"amp.nfl.com", "www.nfl.com"}
    m._validate_final("https://amp.nfl.com" + path, path, allowed)
    with pytest.raises(ValueError):
        m._validate_final("https://example.com" + path, path, allowed)
    with pytest.raises(ValueError):
        m._validate_final("https://amp.nfl.com/transactions/league/trades/2018/5", path, allowed)

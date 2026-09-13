from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from research import v09b_nfl_transaction_pagination_diagnostic_v3 as m


def test_amp_url_preserves_path_and_cursor_verbatim_after_decode():
    cursor = "AAAH4QAAAAkAAAAbAAAAAAAKuXA="
    url = m._amp_url("https://www.nfl.com/transactions/league/signings/2017/9", cursor)
    p = urlparse(url)
    assert p.scheme == "https"
    assert p.hostname == "amp.nfl.com"
    assert p.path == "/transactions/league/signings/2017/9"
    assert parse_qs(p.query)["after"] == [cursor]


def test_amp_url_rejects_non_www_source():
    with pytest.raises(ValueError):
        m._amp_url("https://example.com/transactions/league/signings/2017/9")


def test_validate_final_allows_only_frozen_hosts_and_exact_path():
    path = "/transactions/league/signings/2021/9"
    allowed = {"amp.nfl.com", "www.nfl.com"}
    m._validate_final("https://amp.nfl.com" + path + "?after=x", path, allowed)
    m._validate_final("https://www.nfl.com" + path + "?after=x", path, allowed)
    with pytest.raises(ValueError):
        m._validate_final("https://nfl.com" + path, path, allowed)
    with pytest.raises(ValueError):
        m._validate_final("https://amp.nfl.com/transactions/league/signings/2021/10", path, allowed)


def test_row_key_is_exact_six_field_identity():
    row = {"from":"--","to":"Chiefs","date":"09/01","name":"A Player","position":"LB","transaction":"Practice Squad"}
    assert m._row_key(row) == ("--","Chiefs","09/01","A Player","LB","Practice Squad")

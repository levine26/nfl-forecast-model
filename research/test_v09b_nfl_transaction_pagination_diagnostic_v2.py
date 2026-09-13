from __future__ import annotations

from research.v09b_nfl_transaction_pagination_diagnostic_v2 import _cursor_urls, _row_key


HTML = """
<html><body>
<a href="/transactions/league/signings/2017/9?after=TOKEN%3D">Next Page</a>
<a href="/transactions/league/waivers/2017/9?after=WRONG">Wrong</a>
</body></html>
"""


def test_cursor_discovery_stays_on_exact_endpoint() -> None:
    assert _cursor_urls(HTML, "https://www.nfl.com/transactions/league/signings/2017/9") == [
        "https://www.nfl.com/transactions/league/signings/2017/9?after=TOKEN%3D"
    ]


def test_row_identity_preserves_literal_transaction_fields() -> None:
    row = {
        "from": "--",
        "to": "Cardinals Cardinals",
        "date": "09/30",
        "name": "Vinston Painter",
        "position": "",
        "transaction": "Free Agent Signing",
    }
    assert _row_key(row) == (
        "--", "Cardinals Cardinals", "09/30", "Vinston Painter", "", "Free Agent Signing"
    )

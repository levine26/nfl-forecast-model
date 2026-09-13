from __future__ import annotations

import pytest

from research.v09b_nfl_transaction_ledger_source_probe_v1 import (
    canonical_url,
    discover_pagination_links,
    evidence_found,
    parse_transaction_rows,
    validate_endpoint_identity,
)


HTML = """
<html><body>
<h1>2021 NFL Transactions</h1><h2>Signings — September</h2><h3>September 2021</h3>
<table>
<thead><tr><th>From</th><th>To</th><th>Date</th><th>Name</th><th>Position</th><th>Transaction</th></tr></thead>
<tbody>
<tr><td>--</td><td>Seahawks Seahawks</td><td>09/30</td><td>Phillip Dorsett</td><td></td><td>Practice Squad Veteran</td></tr>
<tr><td>--</td><td>Titans Titans</td><td>09/30</td><td>Johnny Townsend</td><td></td><td>Free Agent Signing</td></tr>
</tbody></table>
<a href="/transactions/league/signings/2021/9?after=ABC%3D">Next</a>
<a href="/transactions/league/waivers/2021/9?after=WRONG">Wrong category</a>
</body></html>
"""


def test_parse_six_column_transaction_rows() -> None:
    rows, header = parse_transaction_rows(HTML)
    assert header is True
    assert len(rows) == 2
    assert rows[0]["name"] == "Phillip Dorsett"
    assert rows[0]["transaction"] == "Practice Squad Veteran"
    assert rows[0]["date"] == "09/30"


def test_pagination_stays_inside_frozen_endpoint() -> None:
    links = discover_pagination_links(
        HTML,
        base_url="https://www.nfl.com/transactions/league/signings/2021/9",
        season=2021,
        month=9,
        category="signings",
        allowed_hosts={"www.nfl.com"},
    )
    assert links == ["https://www.nfl.com/transactions/league/signings/2021/9?after=ABC%3D"]


def test_endpoint_identity_rejects_cross_category_or_extra_query() -> None:
    validate_endpoint_identity(
        "https://www.nfl.com/transactions/league/signings/2021/9?after=ABC",
        season=2021,
        month=9,
        category="signings",
        allowed_hosts={"www.nfl.com"},
    )
    with pytest.raises(ValueError):
        validate_endpoint_identity(
            "https://www.nfl.com/transactions/league/waivers/2021/9?after=ABC",
            season=2021,
            month=9,
            category="signings",
            allowed_hosts={"www.nfl.com"},
        )
    with pytest.raises(ValueError):
        validate_endpoint_identity(
            "https://www.nfl.com/transactions/league/signings/2021/9?page=2",
            season=2021,
            month=9,
            category="signings",
            allowed_hosts={"www.nfl.com"},
        )


def test_semantic_evidence_is_literal_source_text_not_state_machine() -> None:
    rows, _ = parse_transaction_rows(HTML)
    assert evidence_found(
        rows,
        {"name": "Phillip Dorsett", "transaction_contains": "Practice Squad Veteran"},
    ) is True
    assert evidence_found(
        rows,
        {"name": "Phillip Dorsett", "transaction_contains": "Active Roster"},
    ) is False


def test_canonical_url_keeps_only_source_relevant_query() -> None:
    assert canonical_url("HTTPS://WWW.NFL.COM/transactions/league/signings/2021/9/?after=A%3D#frag") == (
        "https://www.nfl.com/transactions/league/signings/2021/9?after=A%3D"
    )

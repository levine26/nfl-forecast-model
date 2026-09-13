from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from research.v09b_nfl_transaction_browser_pagination_v3 import cursor_url


def test_cursor_url_preserves_exact_after_token() -> None:
    token = "AAAH4QAAAAkAAAAbAAAAAAAKuXA="
    url = cursor_url("https://www.nfl.com/transactions/league/signings/2017/9", token)
    assert url.startswith("https://www.nfl.com/transactions/league/signings/2017/9?")
    assert parse_qs(urlparse(url).query)["after"] == [token]


def test_contract_freezes_two_v2_endpoints_and_no_authority() -> None:
    c = json.loads(Path("research/availability/v09b_nfl_transaction_browser_pagination_v3_contract.json").read_text())
    assert len(c["fixed_endpoints"]) == 2
    assert c["fixed_endpoints"][0]["cursor"] == "AAAH4QAAAAkAAAAbAAAAAAAKuXA="
    assert c["fixed_endpoints"][1]["cursor"] == "AAAH5QAAAAkAAAAdAAAAAAAMi0M="
    assert c["browser_requirements"]["javascript_enabled"] is True
    assert c["explicit_non_gates"]["novel_row_advancement_required_for_diagnostic_completion"] is False
    assert c["authority"]["diagnostic_has_source_qualification_authority"] is False
    assert c["authority"]["diagnostic_has_chronology_authority"] is False
    assert c["authority"]["v09b_model_fit_authorized"] is False
    assert c["governance"]["completed_2026_outcomes_used"] == 0

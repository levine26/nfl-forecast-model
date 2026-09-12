from __future__ import annotations

import json
from pathlib import Path

from research.v09b_gamebook_residual_path_audit_v3 import (
    _basename,
    _host,
    _is_gamebook_pdf,
    _is_pdf,
    _path_gsis,
    parse_cdx_directory_payload,
)

CONTRACT_PATH = Path("research/availability/v09b_gamebook_residual_path_audit_v3.json")
V2_RECEIPT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_receipt_v2.json"
)


def test_contract_preserves_v2_and_does_not_add_source_class() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    receipt = json.loads(V2_RECEIPT_PATH.read_text(encoding="utf-8"))
    assert receipt["technical_status"] == "BLOCKED"
    assert receipt["coverage"]["games_missing"] == 70
    assert contract["residual_universe"]["expected_v2_missing_games"] == 70
    assert contract["residual_universe"]["expected_v2_coverage_games"] == 2506
    assert contract["authorized_hosts_exact"] == ["www.nfl.com", "nflcdns.nfl.com"]
    assert contract["directory_query"]["no_gamebook_filename_filter"] is True
    assert contract["non_authorizations"]["new_host_family_authorized"] is False
    assert contract["non_authorizations"]["v09b_model_fit_authorized"] is False
    assert contract["governance"]["game_outcomes_used"] == 0
    assert contract["governance"]["completed_2026_outcomes_used"] == 0


def test_url_classification_is_case_insensitive_and_port_safe() -> None:
    url = "http://www.nfl.com:80/liveupdate/gamecenter/56972/DEN_GameBook.PDF?x=1"
    assert _host(url) == "www.nfl.com"
    assert _path_gsis(url) == "56972"
    assert _basename(url) == "DEN_GameBook.PDF"
    assert _is_pdf(url) is True
    assert _is_gamebook_pdf(url) is True


def test_non_gamebook_pdf_is_diagnostic_only() -> None:
    url = "https://nflcdns.nfl.com/liveupdate/gamecenter/56972/summary.pdf"
    assert _is_pdf(url) is True
    assert _is_gamebook_pdf(url) is False


def test_parse_cdx_directory_payload_keeps_all_files() -> None:
    payload = [
        ["timestamp", "original", "statuscode", "digest", "mimetype", "length"],
        [
            "20161010000000",
            "https://nflcdns.nfl.com/liveupdate/gamecenter/56972/DEN_GameBook.PDF",
            "200",
            "A",
            "application/pdf",
            "1000",
        ],
        [
            "20161010000000",
            "https://nflcdns.nfl.com/liveupdate/gamecenter/56972/summary.json",
            "200",
            "B",
            "application/json",
            "100",
        ],
    ]
    rows = parse_cdx_directory_payload(payload)
    assert len(rows) == 2
    assert rows[0]["digest"] == "A"
    assert rows[1]["mimetype"] == "application/json"

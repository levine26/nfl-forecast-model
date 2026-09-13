from __future__ import annotations

import json
from pathlib import Path


def test_source_contract_keeps_snapshot_below_raw_source_authority() -> None:
    contract = json.loads(
        Path("research/availability/v09b_modern_gamebook_locator_snapshot_contract_v1.json").read_text()
    )
    assert contract["canonical_universe"]["expected_games_total"] == 1296
    assert contract["snapshot"]["combined_sha256"] == "d26b2cab8bdd05c223de0239cfaf70b09b75b6487c8ba2c353bd7749d1730351"
    assert contract["authority"]["snapshot_is_downstream_discovery_authority"] is True
    assert contract["authority"]["snapshot_is_label_authority"] is False
    assert contract["authority"]["modern_raw_source_bytes_qualified"] is False
    assert contract["authority"]["v09b_model_fit_authorized"] is False


def test_generator_source_code_forbids_live_page_discovery() -> None:
    source = Path("research/v09b_modern_gamebook_locator_snapshot_v1.py").read_text()
    assert "requests." not in source
    assert "nfl.com/games/" not in source
    assert "static.www.nfl.com" in source


def test_contract_pins_the_three_v1_live_rediscovery_failures() -> None:
    contract = json.loads(
        Path("research/availability/v09b_modern_gamebook_locator_snapshot_contract_v1.json").read_text()
    )
    assert contract["v1_failure_boundary"]["failed_live_rediscovery_games"] == [
        "2017_01_ARI_DET",
        "2019_15_BUF_PIT",
        "2021_13_BAL_PIT",
    ]
    assert contract["v1_failure_boundary"]["live_page_order_tie_break_allowed"] is False
    assert contract["v1_failure_boundary"]["threshold_relaxation_allowed"] is False

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "groq_research_contract.py"
spec = importlib.util.spec_from_file_location("groq_research_contract", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "g1",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-13",
                "gametime": "13:00",
                "away_team": "BUF",
                "home_team": "HOU",
                "pick": "BUF",
                "final_probability_strategy": "F-ST-01-FROZEN-2026",
                "fst_artifact_id": "F-ST-01-FROZEN-2026",
                "final_home_prob": 0.46,
                "spread_line": -1.5,
            },
            {
                "game_id": "g2",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-13",
                "gametime": "16:25",
                "away_team": "ARI",
                "home_team": "LAC",
                "pick": "LAC",
                "final_probability_strategy": "F-ST-01-FROZEN-2026",
                "fst_artifact_id": "F-ST-01-FROZEN-2026",
                "final_home_prob": 0.81,
                "spread_line": 9.5,
            },
        ]
    )


def test_numeric_probability_and_line_moves_are_reconcilable() -> None:
    before = module.build_contract(_frame())
    updated = _frame()
    updated.loc[updated["game_id"] == "g1", "final_home_prob"] = 0.49
    updated.loc[updated["game_id"] == "g1", "spread_line"] = -2.5
    after = module.build_contract(updated)
    assert module.contract_differences(before, after) == []


def test_pick_flip_requires_fresh_research() -> None:
    before = module.build_contract(_frame())
    updated = _frame()
    updated.loc[updated["game_id"] == "g1", "pick"] = "HOU"
    differences = module.contract_differences(before, module.build_contract(updated))
    assert differences == ["g1: pick changed 'BUF' -> 'HOU'"]


def test_matchup_timing_or_model_identity_change_requires_fresh_research() -> None:
    before = module.build_contract(_frame())
    updated = _frame()
    updated.loc[updated["game_id"] == "g2", "gametime"] = "20:20"
    updated.loc[updated["game_id"] == "g2", "fst_artifact_id"] = "F-ST-02"
    differences = module.contract_differences(before, module.build_contract(updated))
    assert "g2: gametime changed '16:25' -> '20:20'" in differences
    assert "g2: fst_artifact_id changed 'F-ST-01-FROZEN-2026' -> 'F-ST-02'" in differences


def test_added_or_removed_game_requires_fresh_research() -> None:
    before = module.build_contract(_frame())
    updated = _frame().iloc[[0]].copy()
    differences = module.contract_differences(before, module.build_contract(updated))
    assert differences == ["g2: removed from canonical slate"]


def test_duplicate_game_id_fails_closed() -> None:
    duplicated = pd.concat([_frame(), _frame().iloc[[0]]], ignore_index=True)
    try:
        module.build_contract(duplicated)
    except ValueError as exc:
        assert "duplicate game_id" in str(exc)
    else:
        raise AssertionError("duplicate game_id must fail closed")


def test_missing_contract_field_fails_closed() -> None:
    frame = _frame().drop(columns=["pick"])
    try:
        module.build_contract(frame)
    except ValueError as exc:
        assert "missing contract fields" in str(exc)
        assert "pick" in str(exc)
    else:
        raise AssertionError("missing contract field must fail closed")

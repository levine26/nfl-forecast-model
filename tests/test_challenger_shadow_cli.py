from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lock_challenger_shadow.py"
SPEC = importlib.util.spec_from_file_location("lock_challenger_shadow_cli", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_read_shadow_history_preserves_boolean_grade_compatibility(tmp_path: Path):
    path = tmp_path / "prediction_history_shadow.csv"
    path.write_text(
        "game_id,winner_correct\n"
        "2026_01_AWAY_HOME,\n",
        encoding="utf-8",
    )

    history = MODULE._read_csv(path)

    assert history["winner_correct"].dtype == object
    assert pd.isna(history.at[0, "winner_correct"])
    history.at[0, "winner_correct"] = False
    assert history.at[0, "winner_correct"] is False

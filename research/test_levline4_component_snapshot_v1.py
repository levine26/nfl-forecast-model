from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from research.levline4_component_snapshot_v1 import (
    COMPONENTS,
    build_component_snapshot,
    write_capture,
)


def _frames() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    rng = np.random.default_rng(26)
    n = 120
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = (x1 + 0.35 * x2 + rng.normal(scale=0.55, size=n) > 0).astype(int)
    historical = pd.DataFrame({
        "game_id": [f"h-{idx}" for idx in range(n)],
        "season": np.where(np.arange(n) < 60, 2024, 2025),
        "home_win": y,
        "f1": x1,
        "f2": x2,
    })
    current = pd.DataFrame({
        "game_id": ["2026_02_A_B", "2026_02_C_D"],
        "season": [2026, 2026],
        "week": [2, 2],
        "gameday": ["2026-09-20", "2026-09-20"],
        "gametime": ["13:00", "16:25"],
        "away_team": ["A", "C"],
        "home_team": ["B", "D"],
        "spread_line": [-1.5, 2.5],
        "total_line": [44.5, 47.0],
        "home_win": [pd.NA, pd.NA],
        "f1": [0.2, -0.4],
        "f2": [0.6, -0.1],
    })
    return historical, current, ["f1", "f2"]


def _models() -> dict[str, LogisticRegression]:
    return {
        name: LogisticRegression(C=0.4 + idx * 0.2, max_iter=1000, random_state=26)
        for idx, name in enumerate(COMPONENTS)
    }


def test_component_snapshot_preserves_four_models_and_disagreement_state() -> None:
    historical, current, features = _frames()
    generated = datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc)
    snapshot, status = build_component_snapshot(
        historical,
        current,
        features,
        seed=26,
        generated_utc=generated,
        source_sha="abc123",
        model_templates=_models(),
    )

    assert len(snapshot) == 2
    for component in COMPONENTS:
        values = snapshot[f"{component}_home_prob"]
        assert values.between(0.0, 1.0, inclusive="neither").all()
    matrix = snapshot[[f"{name}_home_prob" for name in COMPONENTS]].to_numpy()
    assert np.allclose(snapshot["component_mean_home_prob"], matrix.mean(axis=1))
    assert np.allclose(snapshot["component_std_home_prob"], matrix.std(axis=1))
    assert np.allclose(snapshot["component_range_home_prob"], matrix.max(axis=1) - matrix.min(axis=1))
    assert snapshot["component_home_votes"].between(0, 4).all()
    assert snapshot["training_last_season"].eq(2025).all()
    assert snapshot["completed_2026_outcomes_used_in_model_fitting"].eq(0).all()
    assert snapshot["research_only"].all()
    assert not snapshot["production_authorized"].any()
    assert status["winner_switch_rule_defined"] is False
    assert status["threshold_defined"] is False
    assert status["production_authorized"] is False


def test_component_snapshot_rejects_2026_training_outcome() -> None:
    historical, current, features = _frames()
    historical.loc[0, "season"] = 2026
    with pytest.raises(ValueError, match="restricted to seasons <= 2025"):
        build_component_snapshot(
            historical,
            current,
            features,
            seed=26,
            model_templates=_models(),
        )


def test_component_snapshot_rejects_graded_current_game() -> None:
    historical, current, features = _frames()
    current.loc[0, "home_win"] = 1
    with pytest.raises(ValueError, match="refuses already-graded current games"):
        build_component_snapshot(
            historical,
            current,
            features,
            seed=26,
            model_templates=_models(),
        )


def test_capture_writer_is_append_only_and_content_addressed(tmp_path) -> None:
    historical, current, features = _frames()
    snapshot, status = build_component_snapshot(
        historical,
        current,
        features,
        seed=26,
        generated_utc=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
        source_sha="abcdef1234567890",
        model_templates=_models(),
    )
    latest = write_capture(tmp_path, snapshot, status)
    assert latest["sha256"]
    assert (tmp_path / "manifest.jsonl").exists()
    assert (tmp_path / "status.json").exists()
    assert (tmp_path / "captures" / f"{latest['capture_id']}.csv").exists()
    with pytest.raises(RuntimeError, match="append-only capture already exists"):
        write_capture(tmp_path, snapshot, status)

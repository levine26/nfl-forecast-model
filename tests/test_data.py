from __future__ import annotations

import pandas as pd
import pytest

from nfl_forecast import data


def _schedule() -> pd.DataFrame:
    return pd.DataFrame([
        {"season": 2024, "game_id": "2024_01_A_B"},
        {"season": 2025, "game_id": "2025_01_A_B"},
        {"season": 2026, "game_id": "2026_01_A_B"},
    ])


def test_load_core_data_falls_back_only_when_newest_pbp_asset_is_unpublished(monkeypatch):
    calls: list[list[int]] = []

    def fake_load_pbp(seasons):
        requested = list(seasons)
        calls.append(requested)
        if 2026 in requested:
            raise ConnectionError(
                "Failed to download https://github.com/nflverse/nflverse-data/releases/"
                "download/pbp/play_by_play_2026.parquet: 404 Client Error: Not Found"
            )
        return pd.DataFrame([{"season": 2024}, {"season": 2025}])

    monkeypatch.setattr(data.pd, "read_csv", lambda *args, **kwargs: _schedule())
    monkeypatch.setattr(data.nfl, "load_pbp", fake_load_pbp)
    monkeypatch.setattr(data.nfl, "load_team_stats", lambda seasons: None)

    bundle = data.load_core_data([2024, 2025, 2026])

    assert calls == [[2024, 2025, 2026], [2024, 2025]]
    assert bundle.schedules["season"].tolist() == [2024, 2025, 2026]
    assert bundle.pbp["season"].tolist() == [2024, 2025]


def test_load_core_data_does_not_mask_non_404_download_failures(monkeypatch):
    monkeypatch.setattr(data.pd, "read_csv", lambda *args, **kwargs: _schedule())
    monkeypatch.setattr(
        data.nfl,
        "load_pbp",
        lambda seasons: (_ for _ in ()).throw(ConnectionError("TLS connection reset")),
    )

    with pytest.raises(ConnectionError, match="TLS connection reset"):
        data.load_core_data([2024, 2025, 2026])


def test_load_core_data_does_not_mask_missing_historical_pbp(monkeypatch):
    monkeypatch.setattr(data.pd, "read_csv", lambda *args, **kwargs: _schedule())
    monkeypatch.setattr(
        data.nfl,
        "load_pbp",
        lambda seasons: (_ for _ in ()).throw(
            ConnectionError(
                "Failed to download https://github.com/nflverse/nflverse-data/releases/"
                "download/pbp/play_by_play_2025.parquet: 404 Client Error: Not Found"
            )
        ),
    )

    with pytest.raises(ConnectionError, match="play_by_play_2025"):
        data.load_core_data([2024, 2025, 2026])

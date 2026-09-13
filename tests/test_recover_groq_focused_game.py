from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.recover_groq_focused_game import choose_chatgpt_dir


GAME_ID = "2026_01_BUF_HOU"


def _bundle(root: Path, stamp: str, games: list[str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "producer": "chatgpt-consumer-session",
                "research_mode": "live-web-search",
                "forecast_path_identity": "F-ST-01-FROZEN-2026",
                "generated_utc": stamp,
                "game_ids": games,
            }
        ),
        encoding="utf-8",
    )
    for game_id in games:
        (root / f"{game_id}.json").write_text('{"games": {}}', encoding="utf-8")


def test_prefers_newer_game_scoped_fallback_bundle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 9, 13, 4, 30, tzinfo=timezone.utc)
    _bundle(Path("inputs/chatgpt_media/current"), "2026-09-13T02:30:00Z", [GAME_ID])
    _bundle(Path("inputs/chatgpt_media/fallback"), "2026-09-13T04:00:00Z", [GAME_ID])

    assert choose_chatgpt_dir(GAME_ID, now) == Path("inputs/chatgpt_media/fallback")


def test_uses_current_bundle_when_fallback_does_not_cover_game(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 9, 13, 4, 30, tzinfo=timezone.utc)
    _bundle(Path("inputs/chatgpt_media/current"), "2026-09-13T04:00:00Z", [GAME_ID])
    _bundle(Path("inputs/chatgpt_media/fallback"), "2026-09-13T04:15:00Z", ["2026_01_ARI_LAC"])

    assert choose_chatgpt_dir(GAME_ID, now) == Path("inputs/chatgpt_media/current")


def test_returns_sentinel_when_no_fresh_chatgpt_bundle_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc)
    _bundle(Path("inputs/chatgpt_media/current"), "2026-09-13T01:00:00Z", [GAME_ID])

    assert choose_chatgpt_dir(GAME_ID, now) == Path("inputs/chatgpt_media/__no_fresh_bundle__")

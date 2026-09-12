from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from nfl_forecast.editorial_provider_fallback import recover_focused_payload


GAME_ID = "2026_01_ARI_LAC"


def _chatgpt_entry() -> dict:
    return {
        "games": {
            GAME_ID: {
                "headline": "Chargers can stress Arizona in two different places",
                "paragraph1": "Arizona enters the matchup with pressure points in protection and the secondary, while Los Angeles has enough front and coverage flexibility to test both. The Cardinals need to keep the down-and-distance menu manageable and avoid leaving replacement pieces isolated. The Chargers, meanwhile, can force the issue by making Arizona sort movement up front before asking the reshuffled defensive backfield to hold up on longer-developing concepts.",
                "model_rationale": "Los Angeles can attack two weakened structural areas at once, making Arizona solve protection and coverage problems on the same series instead of hiding either one.",
                "sources": [
                    {"name": "NFL.com", "title": "Week 1 injury report", "url": "https://www.nfl.com/news/example"},
                    {"name": "CBS Sports", "title": "Week 1 injury tracker", "url": "https://www.cbssports.com/nfl/example"},
                ],
            }
        }
    }


def _write_manifest(root: Path, generated_utc: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "producer": "chatgpt-consumer-session",
        "research_mode": "live-web-search",
        "forecast_path_identity": "F-ST-01-FROZEN-2026",
        "generated_utc": generated_utc,
        "game_ids": [GAME_ID],
    }))
    (root / f"{GAME_ID}.json").write_text(json.dumps(_chatgpt_entry()))


def _provider_payload(headline: str = "Validated prior headline") -> dict:
    return {
        "games": {
            GAME_ID: {
                "headline": headline,
                "paragraph1": _chatgpt_entry()["games"][GAME_ID]["paragraph1"],
                "paragraph2": "Football context: Arizona protection against Los Angeles pressure remains the central matchup mechanism. The pick: Los Angeles Chargers moneyline.",
                "sources": _chatgpt_entry()["games"][GAME_ID]["sources"],
            }
        }
    }


def test_fresh_chatgpt_is_preferred_for_failed_groq_game(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    now = datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc)
    chatgpt = tmp_path / "chatgpt"
    _write_manifest(chatgpt, "2026-09-12T15:30:00Z")
    output = tmp_path / "focused.txt"
    status = tmp_path / "status.json"

    recovered, source = recover_focused_payload(
        game_id=GAME_ID,
        output_path=output,
        reason="groq_http_429",
        chatgpt_dir=chatgpt,
        provider_artifact=tmp_path / "missing.json",
        status_path=status,
        now=now,
    )

    assert recovered is True
    assert source == "chatgpt"
    assert json.loads(output.read_text())["games"][GAME_ID]["headline"].startswith("Chargers")
    recorded = json.loads(status.read_text())["groq_provider_fallback"]
    assert recorded["status"] == "healthy"
    assert recorded["games"][GAME_ID]["requires_chatgpt_refresh"] is False


def test_stale_chatgpt_uses_last_validated_game_and_flags_refresh(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "456")
    now = datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc)
    chatgpt = tmp_path / "chatgpt"
    _write_manifest(chatgpt, "2026-09-12T04:00:00Z")
    provider = tmp_path / "provider.json"
    provider.write_text(json.dumps(_provider_payload()))
    output = tmp_path / "focused.txt"
    status = tmp_path / "status.json"

    recovered, source = recover_focused_payload(
        game_id=GAME_ID,
        output_path=output,
        reason="focused_validation_failed",
        chatgpt_dir=chatgpt,
        provider_artifact=provider,
        status_path=status,
        now=now,
    )

    assert recovered is True
    assert source == "last_validated_editorial"
    payload = json.loads(output.read_text())["games"][GAME_ID]
    assert payload["headline"] == "Validated prior headline"
    recorded = json.loads(status.read_text())["groq_provider_fallback"]
    assert recorded["status"] == "degraded"
    assert recorded["games"][GAME_ID]["requires_chatgpt_refresh"] is True
    assert recorded["failed_games"] == [GAME_ID]


def test_deleted_worktree_artifact_can_recover_committed_last_good(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "git-head")
    repo = tmp_path / "repo"
    (repo / "outputs").mkdir(parents=True)
    provider = repo / "outputs" / "copilot_media_reads.json"
    provider.write_text(json.dumps(_provider_payload("Committed last-good headline")))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "outputs/copilot_media_reads.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "last good"], cwd=repo, check=True)
    provider.unlink()
    monkeypatch.chdir(repo)

    output = repo / "focused.txt"
    status = repo / "status.json"
    recovered, source = recover_focused_payload(
        game_id=GAME_ID,
        output_path=output,
        reason="provider_down",
        chatgpt_dir=repo / "no-chatgpt",
        provider_artifact=Path("outputs/copilot_media_reads.json"),
        status_path=status,
        now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
    )

    assert recovered is True
    assert source == "last_validated_editorial"
    assert json.loads(output.read_text())["games"][GAME_ID]["headline"] == "Committed last-good headline"
    assert json.loads(status.read_text())["groq_provider_fallback"]["games"][GAME_ID]["requires_chatgpt_refresh"] is True


def test_missing_game_fallback_stays_fail_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "789")
    recovered, source = recover_focused_payload(
        game_id=GAME_ID,
        output_path=tmp_path / "focused.txt",
        reason="provider_down",
        chatgpt_dir=tmp_path / "none",
        provider_artifact=tmp_path / "none.json",
        status_path=tmp_path / "status.json",
        now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
    )
    assert recovered is False
    assert source == "missing"
    recorded = json.loads((tmp_path / "status.json").read_text())["groq_provider_fallback"]
    assert recorded["games"][GAME_ID]["fallback_source"] == "missing"
    assert recorded["games"][GAME_ID]["requires_chatgpt_refresh"] is True

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ingest_chatgpt_media_payloads.py"
spec = importlib.util.spec_from_file_location("ingest_chatgpt_media_payloads", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _manifest(game_ids: list[str], generated: datetime) -> dict:
    return {
        "schema_version": 1,
        "producer": module.EXPECTED_PRODUCER,
        "research_mode": module.EXPECTED_RESEARCH_MODE,
        "forecast_path_identity": module.EXPECTED_FORECAST_PATH,
        "generated_utc": generated.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "game_ids": game_ids,
    }


def test_manifest_requires_exact_live_web_research_contract(tmp_path: Path):
    now = datetime(2026, 9, 12, 4, 0, tzinfo=timezone.utc)
    game_ids = ["A-B", "C-D"]
    (tmp_path / "manifest.json").write_text(json.dumps(_manifest(game_ids, now)), encoding="utf-8")

    payload = module.validate_manifest(tmp_path, game_ids, now=now + timedelta(minutes=10))
    assert payload["producer"] == "chatgpt-consumer-session"
    assert payload["research_mode"] == "live-web-search"
    assert payload["forecast_path_identity"] == "F-ST-01-FROZEN-2026"


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda data: data.update(producer="other"), "producer"),
        (lambda data: data.update(research_mode="offline"), "research_mode"),
        (lambda data: data.update(forecast_path_identity="changed"), "forecast_path_identity"),
        (lambda data: data.update(game_ids=["C-D", "A-B"]), "canonical slate order"),
    ],
)
def test_manifest_fails_closed_on_contract_changes(tmp_path: Path, mutator, match: str):
    now = datetime(2026, 9, 12, 4, 0, tzinfo=timezone.utc)
    data = _manifest(["A-B", "C-D"], now)
    mutator(data)
    (tmp_path / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        module.validate_manifest(tmp_path, ["A-B", "C-D"], now=now)


def test_manifest_rejects_stale_research(tmp_path: Path):
    now = datetime(2026, 9, 12, 8, 30, tzinfo=timezone.utc)
    generated = now - timedelta(hours=module.MAX_MANIFEST_AGE_HOURS, minutes=1)
    (tmp_path / "manifest.json").write_text(json.dumps(_manifest(["A-B"], generated)), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest stale"):
        module.validate_manifest(tmp_path, ["A-B"], now=now)


def test_discover_payloads_requires_exactly_one_file_per_game(tmp_path: Path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "A-B.json").write_text("{}", encoding="utf-8")
    (tmp_path / "C-D.txt").write_text("{}", encoding="utf-8")
    found = module.discover_payloads(tmp_path, ["A-B", "C-D"])
    assert list(found) == ["A-B", "C-D"]

    (tmp_path / "A-B.txt").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate focused payload"):
        module.discover_payloads(tmp_path, ["A-B", "C-D"])


def test_discover_payloads_rejects_unknown_or_missing_games(tmp_path: Path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "A-B.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="missing focused payloads"):
        module.discover_payloads(tmp_path, ["A-B", "C-D"])

    (tmp_path / "X-Y.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not in canonical slate"):
        module.discover_payloads(tmp_path, ["A-B"])


def test_ingest_routes_every_game_through_existing_focused_and_full_slate_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    game_ids = ["A-B", "C-D"]
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    now = datetime.now(timezone.utc)
    (bundle / "manifest.json").write_text(json.dumps(_manifest(game_ids, now)), encoding="utf-8")
    for gid in game_ids:
        (bundle / f"{gid}.json").write_text(json.dumps({"games": {gid: {}}}), encoding="utf-8")

    predictions = tmp_path / "predictions.csv"
    pd.DataFrame({"game_id": game_ids}).to_csv(predictions, index=False)
    previews = tmp_path / "previews.json"
    evidence = tmp_path / "evidence.json"
    output = tmp_path / "published.json"
    previews.write_text("{}", encoding="utf-8")
    evidence.write_text("{}", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(command, *, cwd, check):
        assert cwd == ROOT
        assert check is True
        calls.append(list(command))

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.ingest(
        input_dir=bundle,
        predictions=predictions,
        previews=previews,
        evidence=evidence,
        output=output,
    )

    scripts = [call[1] for call in calls]
    assert scripts == [
        "scripts/validate_single_copilot_game.py",
        "scripts/validate_single_copilot_game.py",
        "scripts/merge_copilot_game_payloads.py",
        "scripts/compose_copilot_media_reads.py",
        "scripts/render_levline_paragraphs.py",
        "scripts/validate_copilot_media_reads.py",
    ]
    focused_ids = [calls[0][calls[0].index("--game-id") + 1], calls[1][calls[1].index("--game-id") + 1]]
    assert focused_ids == game_ids
    assert str(output) in calls[-1]


def test_publish_cleans_scratch_and_refuses_post_validation_main_race():
    workflow = (ROOT / ".github" / "workflows" / "chatgpt_media_ingest.yml").read_text(encoding="utf-8")
    publish = workflow.split("- name: Publish editorial-only outputs", 1)[1]
    intended_add = "git add outputs/copilot_media_reads.json outputs/game_previews.json outputs/context_source_status.json"
    commit = 'git commit -m "Refresh ChatGPT-ingested Sunday Signal Reads"'
    clean = "git reset --hard HEAD"
    fetch = "git fetch origin main"
    base = "validated_base=$(git rev-parse HEAD^)"
    guard = 'if [ "$(git rev-parse origin/main)" != "$validated_base" ]; then'
    push = "git push origin HEAD:main"

    assert intended_add in publish
    assert "git pull --rebase origin main" not in publish
    assert publish.index(intended_add) < publish.index(commit) < publish.index(clean) < publish.index(fetch)
    assert publish.index(fetch) < publish.index(base) < publish.index(guard) < publish.index(push)

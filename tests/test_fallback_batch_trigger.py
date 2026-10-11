"""Avoid workflow cancellation storms from consecutive per-game recovery commits."""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/chatgpt_failed_game_ingest.yml"


def test_fallback_push_runs_on_manifest_batch_only():
    content = WORKFLOW.read_text(encoding="utf-8")
    push = content.split("  push:\n", 1)[1].split("  workflow_dispatch:", 1)[0]
    assert '"inputs/chatgpt_media/fallback/manifest.json"' in push
    assert '"inputs/chatgpt_media/fallback/**"' not in push


def test_explicit_dispatch_remains_for_operator_recovery():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "  workflow_dispatch:" in content
    assert "  cancel-in-progress: true" in content
    # Concurrent publish workers remain serialized; only complete batch commits
    # should initiate automatic recovery.

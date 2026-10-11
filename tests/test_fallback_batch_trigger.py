"""Editorial recovery remains archived but cannot self-trigger in forecast-only production."""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/chatgpt_failed_game_ingest.yml"


def test_fallback_is_manual_only_and_never_triggered_by_batch_commits():
    content = WORKFLOW.read_text(encoding="utf-8")
    triggers = content.split("\non:", 1)[1].split("\npermissions:", 1)[0]
    assert "  workflow_dispatch:" in triggers
    assert "  push:" not in triggers
    assert "  workflow_run:" not in triggers
    assert "  schedule:" not in triggers
    assert "  pull_request:" not in triggers


def test_archived_operator_dispatch_retains_serialization():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "  workflow_dispatch:" in content
    assert "  cancel-in-progress: true" in content

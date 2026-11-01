from __future__ import annotations

"""Keep successful Pages builds from starving during bursty forecast triggers."""

from pathlib import Path


DASHBOARD = Path(__file__).resolve().parents[1] / ".github/workflows/dashboard.yml"


def _workflow() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_production_pages_run_is_not_cancelled_by_subsequent_refresh():
    text = _workflow()
    # GitHub Actions cancels *running* builds on group collisions only when
    # cancel-in-progress evaluates true. Production may have one pending newer
    # run, but the active build/deploy must finish atomically.
    concurrency = text.split("\nconcurrency:\n", 1)[1].split("\njobs:\n", 1)[0]
    assert "'pages-production'" in concurrency
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in concurrency
    assert "cancel-in-progress: true" not in concurrency


def test_pr_checks_still_have_independent_cancellable_group():
    concurrency = _workflow().split("\nconcurrency:\n", 1)[1].split("\njobs:\n", 1)[0]
    assert "pages-pr-{0}" in concurrency
    assert "pages-noop-{0}" in concurrency
    assert "github.event_name == 'pull_request'" in concurrency


def test_build_gate_includes_this_regression_and_deploy_needs_build():
    content = _workflow()
    assert "          tests/test_dashboard_production_concurrency.py\n" in content
    assert "  deploy:\n" in content
    assert "    needs: build\n" in content
    assert "    environment:\n      name: github-pages\n" in content


def test_fast_official_lock_receipt_triggers_pages_without_noop_deploy_storm():
    content = _workflow()
    trigger = content.split("  workflow_run:\n", 1)[1].split("  workflow_dispatch:", 1)[0]
    assert "'Sunday Signal fast official T-120 lock'" in trigger
    # GitHub's Actions token suppresses downstream push events; this event
    # explicitly republishes persisted receipts after a successful lock run.
    assert "github.event.workflow_run.conclusion == 'success'" in content
    assert content.count("github.event.workflow_run.head_sha != github.sha") == 2
    assert content.count("github.event.workflow_run.name != 'Sunday Signal fast official T-120 lock'") == 2
    # A no-op five-minute heartbeat must not start a costly Pages build.
    assert "github.event.workflow_run.head_sha != github.sha" in content.split("  build:\n", 1)[1].split("  deploy:\n", 1)[0]

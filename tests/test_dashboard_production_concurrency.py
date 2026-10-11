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

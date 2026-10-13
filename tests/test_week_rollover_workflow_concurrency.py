from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def test_daily_full_model_refresh_never_cancels_active_publish():
    yml = (ROOT / "weekly.yml").read_text(encoding="utf-8")
    concurrency = yml.split("\nconcurrency:", 1)[1].split("\njobs:", 1)[0]
    assert "cancel-in-progress: false" in concurrency


def test_market_rollover_skips_duplicate_full_model_dispatch():
    yml = (ROOT / "market_refresh.yml").read_text(encoding="utf-8")
    assert "gh run list --workflow weekly.yml --branch main" in yml
    assert 'if [ "$active" -gt 0 ]; then' in yml
    assert "gh workflow run weekly.yml --ref main" in yml
    assert "steps.rollover.outputs.required == 'true'" in yml


def test_research_only_main_races_do_not_force_another_model_fit():
    yml = (ROOT / "weekly.yml").read_text(encoding="utf-8")
    assert 'advance_files=$(git diff --name-only "$base_sha" origin/main)' in yml
    assert "challenger_outputs/" in yml
    assert "git rebase origin/main" in yml
    assert "git rebase --abort" in yml
    assert "git fetch origin main" in yml

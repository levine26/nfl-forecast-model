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

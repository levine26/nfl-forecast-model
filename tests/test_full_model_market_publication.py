from pathlib import Path


def test_full_model_publishes_only_after_market_provenance_is_reobserved():
    workflow = Path(".github/workflows/weekly.yml").read_text()
    publish = workflow.split("- name: Generate and publish outputs", 1)[1]

    model = publish.index("python scripts/run_week.py --season 2026 --snapshot EARLY")
    refresh = publish.index("python scripts/refresh_market.py --season 2026")
    status_guard = publish.index('status.get("market_provenance_missing_games", 1) != 0')
    staged = publish.index("git add outputs/")
    committed = publish.index('git commit -m "Update NFL forecasts"')
    assert model < refresh < status_guard < staged < committed
    assert 'status.get("status") != "healthy"' in publish
    assert 'status.get("slate_completeness_verified") is not True' in publish
    assert 'status.get("fst_fallback_count", 1) != 0' in publish
    assert "Refusing mixed-generation or unqualified market publication" in publish

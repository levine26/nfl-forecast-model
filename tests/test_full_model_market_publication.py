from pathlib import Path


def test_full_model_publishes_only_after_market_provenance_is_reobserved():
    workflow = Path(".github/workflows/weekly.yml").read_text()
    publish = workflow.split("- name: Generate and publish outputs", 1)[1]
    validator = Path("scripts/validate_market_publication.py").read_text()

    model = publish.index("python scripts/run_week.py --season 2026 --snapshot EARLY")
    refresh = publish.index("python scripts/refresh_market.py --season 2026")
    status_guard = publish.index("python scripts/validate_market_publication.py --output-dir outputs")
    staged = publish.index("git add outputs/")
    committed = publish.index('git commit -m "Update NFL forecasts"')
    assert model < refresh < status_guard < staged < committed

    # Full-model publication still fails closed for any unqualified future game.
    assert 'status.get("slate_completeness_verified") is True' in validator
    assert 'status.get("fst_fallback_count") == 0' in validator
    assert 'status.get("market_provenance_missing_games") == missing_provenance' in validator
    assert "unlocked forecast lacks fresh observed market provenance" in validator
    assert "locked public forecast drifted from immutable receipt" in validator
    assert "Status label contradicts verified market provenance" in validator

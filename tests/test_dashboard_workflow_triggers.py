from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / ".github" / "workflows" / "dashboard.yml"


def test_dashboard_redeploys_on_forecasts_not_editorial_producers():
    content = DASHBOARD.read_text(encoding="utf-8")
    assert "workflow_run:" in content
    for workflow in ("Daily NFL model refresh", "Hourly NFL market refresh", "Pregame NFL refresh"):
        assert workflow in content
    assert "outputs/**" in content
    assert "game_previews.json" not in content
    assert "context_source_status.json" not in content
    assert "Sunday Signal Groq media writer" not in content
    assert "Sunday Signal ChatGPT" not in content


def test_failed_forecast_producer_cannot_deploy_pages():
    content = DASHBOARD.read_text(encoding="utf-8")
    deploy = content.split("  deploy:", 1)[1]
    assert "github.event.workflow_run.conclusion == 'success'" in deploy
    assert "uses: actions/deploy-pages@v4" in deploy

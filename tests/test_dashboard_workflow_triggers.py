from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / ".github" / "workflows" / "dashboard.yml"


def test_dashboard_redeploys_after_successful_free_ingestion():
    text = DASHBOARD.read_text(encoding="utf-8")

    assert "workflow_run:" in text
    assert "- 'Sunday Signal ChatGPT free ingestion'" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "outputs/**" in text
    assert "game_previews.json" in text
    assert "context_source_status.json" in text


def test_failed_producer_cannot_deploy_pages():
    text = DASHBOARD.read_text(encoding="utf-8")
    deploy = text.split("  deploy:", 1)[1]

    assert "github.event.workflow_run.conclusion == 'success'" in deploy
    assert "uses: actions/deploy-pages@v4" in deploy

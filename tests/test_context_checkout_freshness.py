from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "context.yml"


def test_current_main_checkout_precedes_context_setup_and_research():
    source = WORKFLOW.read_text(encoding="utf-8")
    checkout = source.index("- uses: actions/checkout@v4")
    fresh = source.index("- name: Rebase context acquisition on current production main")
    python_setup = source.index("- uses: actions/setup-python@v5", checkout)
    research = source.index("- name: Smoke-test contextual evidence generation")
    assert checkout < fresh < python_setup < research
    block = source[fresh:python_setup]
    assert "if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'" in block
    assert "git fetch origin main" in block
    assert "git reset --hard origin/main" in block


def test_contextual_push_remains_race_guarded_and_fail_closed():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "validated_base=$(git rev-parse HEAD^)" in source
    assert "git push origin HEAD:main" in source
    assert "python -m scripts.sync_market_reads --output-dir outputs --check" in source
    assert "Main advanced during all three contextual publication attempts" in source

from pathlib import Path


WORKFLOW = Path(".github/workflows/context.yml")


def test_production_context_refreshes_main_before_install_or_generation():
    content = WORKFLOW.read_text(encoding="utf-8")
    checkout = content.index("      - uses: actions/checkout@v4")
    entry = content.index("      - name: Start contextual research from latest committed main")
    fetch = content.index("git fetch origin main", entry)
    reset = content.index("git reset --hard origin/main", entry)
    python = content.index("      - uses: actions/setup-python@v5", entry)
    assert checkout < entry < fetch < reset < python
    assert "github.ref == 'refs/heads/main' && github.event_name != 'pull_request'" in content[entry:python]
    assert "git pull --rebase" not in content[entry:python]

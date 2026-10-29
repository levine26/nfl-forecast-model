"""Guard the production full-model publisher against broken nested shell heredocs."""

from pathlib import Path
import subprocess
import textwrap


def test_full_model_publish_shell_is_parseable():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/weekly.yml").read_text()
    step = workflow.split("      - name: Generate and publish outputs\n", 1)[1]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1])
    assert "python scripts/refresh_market.py --season 2026" in script
    assert "market_provenance_missing_games" in script
    assert "\nPY\n" in script, "Python heredoc delimiter must begin in column zero"
    check = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True, check=False)
    assert check.returncode == 0, check.stderr

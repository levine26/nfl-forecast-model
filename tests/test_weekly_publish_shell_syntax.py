"""Guard the production full-model publisher against broken nested shell heredocs."""

from pathlib import Path
import subprocess
import textwrap


def test_full_model_publish_shell_is_parseable():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/weekly.yml").read_text()
    step = workflow.split("      - name: Generate and publish outputs\n", 1)[1]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1])
    assert "python scripts/refresh_market.py --season 2026" in script
    assert "python scripts/validate_market_publication.py --output-dir outputs" in script
    validator = (Path(__file__).resolve().parents[1] / "scripts/validate_market_publication.py").read_text()
    assert "market_provenance_missing_games" in validator
    assert "python - <<'PY'" not in script, "Removed nested heredoc must not remain in publish step"
    check = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True, check=False)
    assert check.returncode == 0, check.stderr

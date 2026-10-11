"""Regression: recover Groq success-game HUMAN authority across different forecast hashes.

The producer and consumer run on different commits after failed-game state is
persisted. An evidence/forecast hash mismatch must not silently discard valid
provider checkpoints; a matching GitHub run artifact takes precedence.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = (ROOT / ".github/workflows/groq_media_writer.yml").read_text(encoding="utf-8")
FALLBACK = (ROOT / ".github/workflows/chatgpt_failed_game_ingest.yml").read_text(encoding="utf-8")


def test_failed_groq_run_archives_its_validated_successful_games() -> None:
    assert "if: always() && github.event_name != 'pull_request'" in WRITER
    assert "Archive game-scoped Groq checkpoints for exact-run recovery" in WRITER
    assert "uses: actions/upload-artifact@v4" in WRITER
    assert "name: groq-validated-game-checkpoints-${{ github.run_id }}" in WRITER
    assert "path: /tmp/groq-validated-checkpoint/" in WRITER


def test_fallback_recovers_only_the_authoritative_groq_run_artifact() -> None:
    assert "id: groq_producer" in FALLBACK
    assert "(status.get('groq_provider_fallback') or {}).get('run_id')" in FALLBACK
    assert "run_id.isdecimal()" in FALLBACK
    assert "output.write(f'run_id={run_id}\\n')" in FALLBACK
    assert "uses: actions/download-artifact@v4" in FALLBACK
    assert "name: groq-validated-game-checkpoints-${{ steps.groq_producer.outputs.run_id }}" in FALLBACK
    assert "run-id: ${{ steps.groq_producer.outputs.run_id }}" in FALLBACK
    assert "github-token: ${{ github.token }}" in FALLBACK
    assert FALLBACK.index("Restore checkpoint artifact from authoritative Groq run") < FALLBACK.index(
        "Overlay ChatGPT only onto Groq-failed games"
    )


def test_cache_survives_forecast_hash_drift_but_prose_remains_fail_closed() -> None:
    # The first prefix is preferred; the broad same-OS prefix recovers the
    # latest provider run after contextual evidence changes the exact hash.
    prefix = "            groq-validated-${{ runner.os }}-\n"
    assert prefix in WRITER
    assert prefix in FALLBACK
    assert "strict_bootstrap=checkpoint_path is not None" in (
        ROOT / "scripts/ingest_chatgpt_failed_games.py"
    ).read_text(encoding="utf-8")
    assert "Missing valid producing Groq run id" in FALLBACK
    assert "continue-on-error: true" in FALLBACK  # Old runs had no uploaded artifact.

from pathlib import Path


def test_groq_workflow_recovers_failed_games_without_replacing_successes() -> None:
    text = Path('.github/workflows/groq_media_writer.yml').read_text(encoding='utf-8')

    assert 'recover_groq_focused_game.py' in text
    assert 'groq_provider_request_failed' in text
    assert 'focused_validation_failed' in text
    assert 'full_slate_validation_failed' in text
    assert 'invoking immediate game-scoped ChatGPT recovery' in text
    assert 'refusing broad replacement of successful Groq games' in text
    assert 'Groq/ChatGPT hybrid responses passed the LevLine 3.0 full-slate publication validator.' in text


def test_groq_fallback_keeps_model_boundary_explicit() -> None:
    recovery = Path('scripts/recover_groq_focused_game.py').read_text(encoding='utf-8')

    assert 'F-ST-01-FROZEN-2026' not in recovery or 'CHATGPT_FORECAST_PATH' in recovery
    assert 'train_model' not in recovery
    assert 'grading.py' not in recovery
    assert 'fst_production.py' not in recovery

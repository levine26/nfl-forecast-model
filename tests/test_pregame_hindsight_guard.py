from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "validate_single_copilot_game.py"
spec = importlib.util.spec_from_file_location("validate_single_copilot_game_hindsight", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rejects_current_game_postgame_hindsight():
    text = (
        "The Giants' running game proved too much for Dallas, while New York's defense "
        "secured the win with better third-down execution."
    )
    assert module._paragraph_has_postgame_hindsight(text)


def test_allows_clearly_historical_context_in_pregame_preview():
    text = (
        "Last season, the Giants' running game proved too much in the first meeting. "
        "This week Dallas must set firmer edges while New York tries to create the same matchup stress."
    )
    assert not module._paragraph_has_postgame_hindsight(text)


def test_allows_forward_looking_matchup_language():
    text = (
        "New York's running game could stress Dallas on early downs, while the Cowboys need "
        "their pass protection to hold up long enough for the downfield game to develop."
    )
    assert not module._paragraph_has_postgame_hindsight(text)

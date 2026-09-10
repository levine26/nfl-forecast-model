import json
import re
from pathlib import Path

from nfl_forecast.editorial_finalize import _editorial_uniqueness_text


def _ngrams(text: str, n: int = 7) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", _editorial_uniqueness_text(text).lower())
    return {" ".join(words[i:i+n]) for i in range(max(0, len(words)-n+1))}


def test_game_files_do_not_repeat_visible_prose_across_matchups():
    previews = json.loads(Path('outputs/game_previews.json').read_text())
    owners: dict[str, set[str]] = {}
    for game_id, preview in previews.items():
        paragraphs = preview.get('paragraphs') or []
        visible = [preview.get('headline') or '', paragraphs[0] if paragraphs else '', preview.get('case_for_pick') or '', preview.get('case_for_opponent') or '', preview.get('what_could_make_us_wrong') or '']
        for gram in _ngrams(' '.join(visible)):
            owners.setdefault(gram, set()).add(str(game_id))
    repeated = {gram: games for gram, games in owners.items() if len(games) > 1}
    assert not repeated, f'repeated game-file prose: {list(repeated.items())[:8]}'


def test_standardized_factual_scaffolding_is_ignored_but_substantive_duplicate_is_not():
    standardized = (
        "The official NFL injury report lists Example Player as did not participate in practice. "
        "No game status designation is posted yet, so this is treated as availability context rather than an assumption the player will be inactive."
    )
    assert _ngrams(standardized) == set()

    substantive = "The protection plan has to survive pressure without giving away the explosive throw."
    assert _ngrams(substantive)


def test_known_template_phrases_are_absent():
    text = Path('outputs/game_previews.json').read_text().lower()
    banned = [
        'there is actual memory in this quarterback matchup',
        'prior meetings give',
        'this is a geometry game',
        'the answer on the other side',
        'the case also has a second leg',
        'the supporting thread is',
        'the extra wrinkle is',
    ]
    assert not [phrase for phrase in banned if phrase in text]

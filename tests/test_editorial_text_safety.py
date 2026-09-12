from __future__ import annotations

from nfl_forecast.editorial_text_safety import (
    sanitize_preview_text,
    sanitize_public_evidence,
    sanitize_public_text,
)


def test_injury_description_gets_sentence_boundary_before_guardrail() -> None:
    raw = (
        "The official NFL injury report lists Garrett Williams (CB) as Out. "
        "Achilles LevLine does not make up an injury point value for it."
    )
    fixed = sanitize_public_text(raw)
    assert "Achilles. LevLine does not make up an injury point value for it." in fixed
    assert "Achilles LevLine" not in fixed


def test_existing_punctuation_is_not_duplicated() -> None:
    raw = "Achilles. LevLine does not make up an injury point value for it."
    assert sanitize_public_text(raw) == raw


def test_standardized_status_language_is_preserved() -> None:
    raw = "The official NFL injury report lists Player X as Questionable. Limited participant in practice."
    assert sanitize_public_text(raw) == raw


def test_evidence_and_preview_sanitizers_touch_only_malformed_public_text() -> None:
    evidence = {
        "g1": [
            {
                "summary": "Player is Out. Achilles LevLine does not make up an injury point value for it.",
                "source_name": "NFL.com official injury report",
            },
            {"summary": "Normal football analysis remains unchanged."},
        ]
    }
    previews = {
        "g1": {
            "paragraphs": [
                "Player is Out. Achilles LevLine does not make up an injury point value for it.",
                "LevLine paragraph stays unchanged.",
            ],
            "key_factors": [
                {"summary": "Player is Out. Achilles LevLine does not make up an injury point value for it."}
            ],
            "notebook": [{"summary": "Normal notebook copy."}],
        }
    }

    clean_evidence, evidence_repairs = sanitize_public_evidence(evidence)
    clean_previews, preview_repairs = sanitize_preview_text(previews)

    assert evidence_repairs == 1
    assert preview_repairs == 2
    assert "Achilles. LevLine" in clean_evidence["g1"][0]["summary"]
    assert clean_evidence["g1"][1]["summary"] == "Normal football analysis remains unchanged."
    assert "Achilles. LevLine" in clean_previews["g1"]["paragraphs"][0]
    assert clean_previews["g1"]["paragraphs"][1] == "LevLine paragraph stays unchanged."
    assert clean_previews["g1"]["notebook"][0]["summary"] == "Normal notebook copy."

from nfl_forecast.editorial_quality import assess_human_read, human_read_length_valid


GOOD_HEADLINE = "Falcons rush challenges depleted Saints linebackers"
GOOD_READ = (
    "Atlanta arrives with Bijan Robinson attacking the middle of opposing fronts, "
    "and Michael Penix Jr. can punish linebackers who crash downhill by finding "
    "Drake London downfield. New Orleans has to survive those runs without isolating "
    "its injured second level, while Kellen Moore can counter with Alvin Kamara "
    "behind his blockers and Juwan Johnson stretching the red zone. "
    "The Saints need sustained drives to deny Robinson extra possessions, and "
    "the Falcons must account for Kamara's receiving routes when they pressure the quarterback."
)


def test_accepts_real_matchup_mechanics_without_forcing_a_template():
    assert assess_human_read(GOOD_HEADLINE, GOOD_READ) == []


def test_rejects_current_style_mechanical_injury_stitching():
    bad = (
        "Bears–Packers centers on CHI: Keyshaun Elliott — Out. "
        "The official NFL injury report lists Keyshaun Elliott as Out. "
        "For Bears, that detail changes Bears' choices against Packers; "
        "Packers can exploit it only by forcing Bears off schedule."
    )
    failures = assess_human_read("Bears–Packers centers on an injury report", bad)
    assert "mechanical matchup opening" in failures
    assert "interchangeable causal assertion" in failures
    assert "mechanically stitched conclusion" in failures


def test_rejects_reusable_low_information_quarterback_copy():
    text = (
        "Quarterback play will decide this matchup. Both teams must execute "
        "well in the passing game and show who wants it more in a difficult game."
    )
    failures = assess_human_read("An important test awaits", text)
    assert any("insufficient distinct tactical mechanisms" in issue or
               "no concrete tactical" in issue for issue in failures)


def test_rejects_forecast_model_language_in_human_layer():
    text = GOOD_READ + " LevLine gives the Falcons a better moneyline percentage."
    assert any("model or betting" in issue for issue in
               assess_human_read(GOOD_HEADLINE, text))


def test_tactical_interaction_is_required_even_with_jargon():
    text = (
        "Josh Allen plays quarterback. The Bills feature passing and rushing. "
        "The Rams have coverage and a strong pass rush. "
        "The offensive line has protection statistics. "
        "Both teams have defensive statistics and interesting personnel."
    )
    assert "no concrete tactical action-and-counteraction explanation" in assess_human_read(
        "Bills and Rams football preview", text
    )


def test_fast_and_first_are_not_false_positive_fst_mentions():
    text = GOOD_READ + " Atlanta's fast tempo forces the defense to react first."
    issues = assess_human_read(GOOD_HEADLINE, text)
    assert not any("model or betting" in issue for issue in issues)


def test_literal_fst_name_is_rejected_in_human_matchup_paragraph():
    text = GOOD_READ + " The F-ST model confirms that football analysis."
    issues = assess_human_read(GOOD_HEADLINE, text)
    assert any("model or betting" in issue for issue in issues)


def test_human_paragraph_length_contract_has_exact_55_to_100_bounds():
    for size in (54, 101):
        assert not human_read_length_valid("football " * size)
    for size in (55, 75, 100):
        assert human_read_length_valid("football " * size)

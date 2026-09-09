import pandas as pd

from nfl_forecast.power_editorial_v2 import build_power_editorial_v2


def test_power_commentary_surfaces_conflict_instead_of_forcing_support():
    power = pd.DataFrame([
        {"rank":1,"team":"A","elo_plus":1700,"off_epa":-.20,"def_epa_allowed":.20,"pass_epa":-.25,"recent_win_pct":.20,"movement":"→"},
        {"rank":2,"team":"B","elo_plus":1650,"off_epa":.20,"def_epa_allowed":-.20,"pass_epa":.25,"recent_win_pct":.80,"movement":"▲1"},
        {"rank":3,"team":"C","elo_plus":1600,"off_epa":.00,"def_epa_allowed":.00,"pass_epa":.00,"recent_win_pct":.50,"movement":"▼1"},
        {"rank":4,"team":"D","elo_plus":1500,"off_epa":.10,"def_epa_allowed":-.10,"pass_epa":.12,"recent_win_pct":.70,"movement":"→"},
        {"rank":5,"team":"E","elo_plus":1450,"off_epa":.05,"def_epa_allowed":-.05,"pass_epa":.06,"recent_win_pct":.60,"movement":"→"},
        {"rank":6,"team":"F","elo_plus":1400,"off_epa":-.05,"def_epa_allowed":.05,"pass_epa":-.04,"recent_win_pct":.40,"movement":"→"},
        {"rank":7,"team":"G","elo_plus":1350,"off_epa":-.10,"def_epa_allowed":.10,"pass_epa":-.12,"recent_win_pct":.30,"movement":"→"},
        {"rank":8,"team":"H","elo_plus":1300,"off_epa":-.15,"def_epa_allowed":.15,"pass_epa":-.18,"recent_win_pct":.25,"movement":"→"},
    ])
    payload = build_power_editorial_v2(power)
    top = payload["teams"][0]
    assert top["team"] == "A"
    assert top["tension"] == "efficiency_weaker_than_elo"
    assert "shakier" in top["why_here"]
    assert "1th" not in str(payload)
    assert payload["editorial_version"] == "power-v2"


def test_ordinal_suffixes_are_human():
    power = pd.DataFrame([
        {"rank":1,"team":"A","elo_plus":1700,"off_epa":.4,"def_epa_allowed":-.4,"pass_epa":.4,"recent_win_pct":.9,"movement":"→"},
        {"rank":2,"team":"B","elo_plus":1600,"off_epa":.3,"def_epa_allowed":-.3,"pass_epa":.3,"recent_win_pct":.8,"movement":"→"},
        {"rank":3,"team":"C","elo_plus":1500,"off_epa":.2,"def_epa_allowed":-.2,"pass_epa":.2,"recent_win_pct":.7,"movement":"→"},
    ])
    text = str(build_power_editorial_v2(power))
    assert "1st" in text
    assert "2nd" in text
    assert "3rd" in text

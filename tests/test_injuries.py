import pandas as pd

from nfl_forecast.injuries import parse_nfl_injury_html, practice_status_evidence


HTML = '''
<html><body>
  <h3>Patriots</h3>
  <table>
    <tr><th>Player</th><th>Position</th><th>Injuries</th><th>Practice Status</th><th>Game Status</th></tr>
    <tr><td>TreVeyon Henderson</td><td>RB</td><td>Hamstring</td><td>Did Not Participate In Practice</td><td></td></tr>
    <tr><td>Ben Brown</td><td>C</td><td>Ankle</td><td>Limited Participation in Practice</td><td>Questionable</td></tr>
  </table>
  <h3>Seahawks</h3>
  <table>
    <tr><th>Player</th><th>Position</th><th>Injuries</th><th>Practice Status</th><th>Game Status</th></tr>
    <tr><td>Nick Emmanwori</td><td>S</td><td>Knee</td><td>Limited Participation in Practice</td><td></td></tr>
  </table>
</body></html>
'''


def test_parse_nfl_injury_html_maps_team_and_status():
    rows = parse_nfl_injury_html(HTML, "https://www.nfl.com/injuries/league/2026/reg1")
    assert set(rows) == {"NE", "SEA"}
    assert rows["NE"][0]["name"] == "TreVeyon Henderson"
    assert rows["NE"][0]["practice_status"] == "Did Not Participate In Practice"
    assert rows["NE"][1]["game_status"] == "Questionable"
    assert rows["NE"][1]["status"] == "Questionable"


def test_practice_only_evidence_never_calls_dnp_an_out():
    rows = parse_nfl_injury_html(HTML, "https://www.nfl.com/injuries/league/2026/reg1")
    predictions = pd.DataFrame([{
        "game_id": "2026_01_NE_SEA",
        "away_team": "NE",
        "home_team": "SEA",
    }])
    evidence = practice_status_evidence(predictions, rows)["2026_01_NE_SEA"]
    text = " ".join(item["summary"] for item in evidence)
    assert "TreVeyon Henderson" in text
    assert "Nick Emmanwori" in text
    assert "rather than an assumption the player will be inactive" in text
    assert all(item["source_name"] == "NFL.com official injury report" for item in evidence)

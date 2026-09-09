from pathlib import Path

path = Path('src/nfl_forecast/editorial_voice.py')
text = path.read_text()
old = '''        if "nflverse schedule sample" in lowered or "need variance in the high-leverage parts" in lowered:\n            return False\n        return True\n'''
new = '''        fam = family(item)\n        if ("nflverse schedule sample" in lowered and fam != "rivalry") or "need variance in the high-leverage parts" in lowered:\n            return False\n        return True\n'''
if old not in text:
    raise SystemExit('usable block not found')
text = text.replace(old, new)
needle = '''        if not summary:\n            return ""\n        if fam == "pressure":\n'''
insert = '''        if not summary:\n            return ""\n        if fam == "qb_opponent_history":\n            match = re.search(\n                r"^In the nflverse play-by-play sample since 2021, (.+?) has ([0-9]+) meaningful games against ([A-Z]{2,4}); the most recent was (.+?)\\. Over ([0-9]+) charted dropbacks in those games, (?:he|she|they) averaged ([+\\-][0-9.]+) EPA/dropback with a ([0-9.]+)% positive-EPA rate",\n                summary,\n            )\n            if match:\n                quarterback, games, opponent, latest, dropbacks, epa, positive = match.groups()\n                return f"{quarterback}–{opponent} recent sample: {games} meaningful games, {dropbacks} dropbacks, {epa} EPA/dropback, {positive}% positive-EPA; latest: {latest}."\n        if fam == "rivalry":\n            match = re.search(\n                r"^Since 2021, ([A-Za-z0-9]+) and ([A-Za-z0-9]+) have played ([0-9]+) completed games in the nflverse schedule sample: ([A-Za-z0-9]+) is ([0-9]+-[0-9]+)\\. The most recent finished (.+?)\\.$",\n                summary,\n            )\n            if match:\n                team_a, team_b, games, leader, record, latest = match.groups()\n                return f"{team_a}-{team_b} since 2021: {games} meetings, {leader} {record}; latest: {latest}."\n        if fam == "pressure":\n'''
if needle not in text:
    raise SystemExit('specific summary insertion point not found')
text = text.replace(needle, insert)
path.write_text(text)

from pathlib import Path

voice = Path('src/nfl_forecast/editorial_voice.py')
text = voice.read_text()
if 'import re\n' not in text:
    text = text.replace('from collections import defaultdict\n', 'from collections import defaultdict\nimport re\n')
marker = 'def polish_preview_slate(previews: dict[str, dict], predictions: pd.DataFrame) -> dict[str, dict]:'
if marker not in text:
    raise SystemExit('polish_preview_slate marker missing')
new_tail = r'''def polish_preview_slate(previews: dict[str, dict], predictions: pd.DataFrame) -> dict[str, dict]:
    """Make each game file evidence-led instead of template-led."""
    def advantage(item: dict[str, Any] | None) -> str | None:
        if not item:
            return None
        meta = item.get("metadata") or {}
        value = item.get("advantage_team") or meta.get("advantage_team")
        return str(value) if value else None

    def family(item: dict[str, Any] | None) -> str:
        if not item:
            return "context"
        meta = item.get("metadata") or {}
        return _clean_family(meta.get("family") or item.get("family") or item.get("category"))

    def candidates(preview: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key in ("key_factors", "matchup_meter", "notebook"):
            for item in preview.get(key) or []:
                if isinstance(item, dict):
                    rows.append(item)
        return rows

    def detail(preview: dict[str, Any], title: Any) -> dict[str, Any] | None:
        wanted = str(title or "").strip()
        return next((item for item in candidates(preview) if str(item.get("title") or "").strip() == wanted), None) if wanted else None

    def usable(item: dict[str, Any] | None) -> bool:
        if not item:
            return False
        summary = str(item.get("summary") or "").strip()
        lowered = summary.lower()
        if len(summary.split()) < 7:
            return False
        if "nflverse schedule sample" in lowered or "need variance in the high-leverage parts" in lowered:
            return False
        return True

    def specific_summary(item: dict[str, Any]) -> str:
        summary = str(item.get("summary") or "").strip()
        fam = family(item)
        if not summary:
            return ""
        if fam == "pressure":
            match = re.search(r"^([A-Z]{2,4}) gave up sacks on ([0-9.]+)% of pass plays last season; ([A-Z]{2,4}) got home on ([0-9.]+)%", summary)
            if match:
                protected, allowed, rusher, created = match.groups()
                return f"{protected} protection allowed a {allowed}% sack rate; {rusher}'s rush produced {created}%."
        if fam == "explosives":
            match = re.search(r"^([A-Z]{2,4}) hit a 20\+ yard pass on ([0-9.]+)% of pass plays; ([A-Z]{2,4}) allowed one on ([0-9.]+)%", summary)
            if match:
                offense, created, defense, allowed = match.groups()
                return f"{offense} generated a 20+ yard completion on {created}% of passes; {defense} allowed 20+ on {allowed}%."
        if fam == "early_down":
            match = re.search(r"^([A-Z]{2,4}) threw on ([0-9.]+)% of first- and second-down plays and averaged ([+\-][0-9.]+) EPA per early-down pass\. ([A-Z]{2,4}) allowed ([+\-][0-9.]+)", summary)
            if match:
                offense, rate, epa, defense, allowed = match.groups()
                return f"{offense} early downs: {rate}% pass rate and {epa} EPA per pass; {defense} allowed {allowed}."
        sentences = [part.strip() for part in summary.split(". ") if part.strip()]
        if not sentences:
            return summary
        kept = sentences[:2] if fam in {"international_event", "rivalry", "international_travel"} else sentences[:1]
        result = ". ".join(kept)
        if summary.endswith(".") and not result.endswith("."):
            result += "."
        return result

    def beat(item: dict[str, Any]) -> str:
        title = str(item.get("title") or "").strip().rstrip('.:')
        summary = specific_summary(item)
        return summary if not title or title.lower() in summary.lower()[: max(90, len(title) + 15)] else f"{title}: {summary}"

    special_families = {"international_event", "rivalry", "international_travel"}
    for game_id in sorted(previews):
        preview = previews[game_id]
        row = _pick_row(predictions, game_id)
        if row is None:
            continue
        home, away, pick = str(row.get("home_team")), str(row.get("away_team")), str(row.get("pick"))
        opponent = away if pick == home else home
        spine = preview.get("story_spine") or {}
        all_items = candidates(preview)

        selected: list[dict[str, Any]] = []
        special = next((item for item in all_items if family(item) in special_families and usable(item)), None)
        if special:
            selected.append(special)
        for title in (spine.get("primary_title"), spine.get("secondary_title")):
            item = detail(preview, title)
            if usable(item) and item not in selected:
                selected.append(item)
        for item in preview.get("key_factors") or []:
            if usable(item) and item not in selected:
                selected.append(item)
            if len(selected) >= 3:
                break

        if selected:
            preview["headline"] = str(selected[0].get("title") or f"{away}-{home}").strip()
            lead = " ".join(beat(item) for item in selected[:2]).strip()
        else:
            preview["headline"] = f"{away}-{home} matchup file"
            lead = f"{away}-{home}: sourced lead unavailable."
        paragraphs = list(preview.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = lead
        else:
            paragraphs = [lead]
        preview["paragraphs"] = paragraphs

        support = next((item for item in all_items if usable(item) and advantage(item) == pick), None)
        counter = next((item for item in all_items if usable(item) and advantage(item) == opponent), None)
        neutral = [item for item in selected if usable(item)]
        pick_item = support or (neutral[0] if neutral else None)
        opponent_item = counter or (neutral[1] if len(neutral) > 1 else None)
        preview["case_for_pick"] = beat(pick_item) if pick_item else f"{pick} in {away}-{home}: featured evidence unavailable."
        preview["case_for_opponent"] = beat(opponent_item) if opponent_item else f"{opponent} in {away}-{home}: featured counter unavailable."
        preview["what_could_make_us_wrong"] = (
            f"{opponent}'s counter in {away}-{home}: {specific_summary(counter)}" if counter
            else f"{away}-{home}: no sourced {opponent} counter clears the publication threshold."
        )
        preview["editorial_voice"] = {
            "evidence_led": True,
            "game_specific": True,
            "lead_items": [str(item.get("title") or "") for item in selected[:2]],
        }
    return previews
'''
voice.write_text(text[: text.index(marker)] + new_tail)

finalize = Path('src/nfl_forecast/editorial_finalize.py')
text = finalize.read_text()
old_banned = '''BANNED = (\n    "two distinct levers", "real matchup counter-signal", "the answer on the other side", "cleaner path gets much narrower",\n)'''
new_banned = '''BANNED = (\n    "two distinct levers", "real matchup counter-signal", "the answer on the other side", "cleaner path gets much narrower",\n    "there is actual memory in this quarterback matchup", "prior meetings give", "this is a geometry game",\n    "the case also has a second leg", "the supporting thread is", "the extra wrinkle is",\n)'''
if old_banned not in text:
    raise SystemExit('BANNED block missing')
text = text.replace(old_banned, new_banned)
# Preserve headlines explicitly set by the game-specific editorial pass.
old_headline = '''        if not is_special:\n            primary_title = str((preview.get("story_spine") or {}).get("primary_title") or "")\n            primary = by_title.get(primary_title)\n            if primary is None:\n                primary = next((item for item in items if _advantage(item) == pick), None)\n            preview["headline"] = _headline(pick, opponent, primary)'''
new_headline = '''        is_game_specific = bool((preview.get("editorial_voice") or {}).get("game_specific"))\n        if not is_special and not is_game_specific:\n            primary_title = str((preview.get("story_spine") or {}).get("primary_title") or "")\n            primary = by_title.get(primary_title)\n            if primary is None:\n                primary = next((item for item in items if _advantage(item) == pick), None)\n            preview["headline"] = _headline(pick, opponent, primary)'''
if old_headline not in text:
    raise SystemExit('headline rewrite block missing')
text = text.replace(old_headline, new_headline)
needle = '''    found = [phrase for phrase in BANNED if phrase in public]\n    if found:\n        raise ValueError(f"publication still contains banned template phrases: {found}")\n    if len(headlines) != len(set(headlines)):\n'''
replacement = '''    found = [phrase for phrase in BANNED if phrase in public]\n    if found:\n        raise ValueError(f"publication still contains banned template phrases: {found}")\n\n    ngram_games: dict[str, set[str]] = {}\n    for game_id, preview in previews.items():\n        paragraphs = preview.get("paragraphs") or []\n        texts = [str(preview.get("headline") or "")]\n        if paragraphs:\n            texts.append(str(paragraphs[0]))\n        texts.extend([\n            str(preview.get("case_for_pick") or ""),\n            str(preview.get("case_for_opponent") or ""),\n            str(preview.get("what_could_make_us_wrong") or ""),\n        ])\n        words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", " ".join(texts).lower())\n        for index in range(max(0, len(words) - 6)):\n            gram = " ".join(words[index:index+7])\n            ngram_games.setdefault(gram, set()).add(str(game_id))\n    repeated = {gram: sorted(games) for gram, games in ngram_games.items() if len(games) > 1}\n    if repeated:\n        sample = list(repeated.items())[:5]\n        raise ValueError(f"publication repeats game-file prose across matchups: {sample}")\n\n    if len(headlines) != len(set(headlines)):\n'''
if needle not in text:
    raise SystemExit('final QA insertion point missing')
finalize.write_text(text.replace(needle, replacement))

# Keep the standalone regression test aligned with the production guard.
test = Path('tests/test_editorial_uniqueness.py')
if test.exists():
    t = test.read_text()
    t = t.replace("visible = [paragraphs[0] if paragraphs else '', preview.get('case_for_pick') or '', preview.get('case_for_opponent') or '']", "visible = [preview.get('headline') or '', paragraphs[0] if paragraphs else '', preview.get('case_for_pick') or '', preview.get('case_for_opponent') or '', preview.get('what_could_make_us_wrong') or '']")
    test.write_text(t)

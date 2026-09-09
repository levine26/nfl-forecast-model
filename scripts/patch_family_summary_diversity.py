from pathlib import Path

# Tighten the public evidence renderer so reusable source-language tails cannot
# survive the final seven-word cross-game publication gate.
path = Path('src/nfl_forecast/editorial_voice.py')
text = path.read_text()
needle = '''        sentences = [part.strip() for part in summary.split(". ") if part.strip()]\n        if not sentences:\n            return summary\n        kept = sentences[:2] if fam in {"international_event", "rivalry", "international_travel"} else sentences[:1]\n        result = ". ".join(kept)\n        if summary.endswith(".") and not result.endswith("."):\n            result += "."\n        return result\n'''
replacement = '''        title = str(item.get("title") or _label(fam)).strip().rstrip('.:')\n\n        # Some downstream evidence enrichers intentionally replace raw statistical\n        # summaries with short football interpretations. Those interpretations are\n        # useful in detail cards, but their reusable sentence tails must never leak\n        # back into the public game-file cases. Keep the public renderer anchored to\n        # the matchup title and the actual side of the evidence.\n        if fam == "pressure":\n            tilt = re.search(r"pressure matchup tilts ([A-Z]{2,4})", summary, re.I)\n            if tilt:\n                return f"{title}: pass-rush leverage favors {tilt.group(1).upper()}."\n        if fam == "explosives":\n            tilt = re.search(r"chunk-play path tilts ([A-Z]{2,4})", summary, re.I)\n            if tilt:\n                return f"{title}: explosive-pass leverage favors {tilt.group(1).upper()}."\n        if fam == "early_down":\n            tilt = re.search(r"early-down leverage tilts ([A-Z]{2,4})", summary, re.I)\n            if tilt:\n                return f"{title}: early-down leverage favors {tilt.group(1).upper()}."\n        if fam in {"staff_impact", "coaching", "personnel", "injury", "history", "qb_opponent_history"}:\n            return f"{title}: {_label(fam)} context."\n        if fam == "rivalry":\n            return f"{title}: rivalry history."\n\n        sentences = [part.strip() for part in summary.split(". ") if part.strip()]\n        if not sentences:\n            return summary\n        if fam in {"international_event", "international_travel"}:\n            kept = sentences[:2]\n            result = ". ".join(kept)\n            if summary.endswith(".") and not result.endswith("."):\n                result += "."\n            return result\n\n        # Fail closed on unparsed public evidence: use a compact title-anchored\n        # formulation instead of importing an arbitrary reusable source sentence.\n        return f"{title}: {_label(fam)} evidence."\n'''
if needle not in text:
    raise SystemExit('specific_summary fallback block missing')
path.write_text(text.replace(needle, replacement))

# Ordinary rivalry history belongs in the notebook/detail layer. It must not
# overwrite a slate-aware Read with the same schedule-sample sentence used by
# other divisional matchups. Exceptional event context may still be promoted.
path = Path('scripts/polish_publication.py')
text = path.read_text()
needle = '''            elif rivalry:\n                preview["headline"] = _expand(rivalry.get("title") or preview.get("headline") or f"{away}-{home}")\n                special_first = _expand(rivalry.get("summary") or "")\n\n            if special_first:\n'''
replacement = '''            # Ordinary rivalry notes stay in the notebook/detail layer; only a\n            # genuinely exceptional event story may replace the slate-aware lead.\n\n            if special_first:\n'''
if needle not in text:
    raise SystemExit('ordinary rivalry promotion block missing')
path.write_text(text.replace(needle, replacement))

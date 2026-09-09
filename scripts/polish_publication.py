from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import pandas as pd

from nfl_forecast.context import NFLVERSE_SCHEDULE_URL
from nfl_forecast.source_policy import probe_advanced_sources
from nfl_forecast.story_context import build_story_context


TEAM_NICK = {
    "ARI":"Cardinals","ATL":"Falcons","BAL":"Ravens","BUF":"Bills","CAR":"Panthers","CHI":"Bears","CIN":"Bengals","CLE":"Browns",
    "DAL":"Cowboys","DEN":"Broncos","DET":"Lions","GB":"Packers","HOU":"Texans","IND":"Colts","JAX":"Jaguars","JAC":"Jaguars",
    "KC":"Chiefs","LA":"Rams","LAC":"Chargers","LV":"Raiders","MIA":"Dolphins","MIN":"Vikings","NE":"Patriots","NO":"Saints",
    "NYG":"Giants","NYJ":"Jets","PHI":"Eagles","PIT":"Steelers","SEA":"Seahawks","SF":"49ers","TB":"Buccaneers","TEN":"Titans","WAS":"Commanders",
}
BANNED_PUBLICATION_PHRASES = [
    "two distinct levers",
    "real matchup counter-signal",
    "the answer on the other side",
    "cleaner path gets much narrower",
]


def _read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text())
    except Exception:
        return fallback


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _num(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def _nick(team: str) -> str:
    return TEAM_NICK.get(str(team), str(team))


def _expand(text: str) -> str:
    out = str(text or "")
    for abbr, name in sorted(TEAM_NICK.items(), key=lambda pair: len(pair[0]), reverse=True):
        out = re.sub(rf"\b{re.escape(abbr)}\b", name, out)
    out = out.replace("qb history", "quarterback history").replace("YAC", "yards after catch")
    return out


def _weighted(meetings: list[dict], field: str, weight_field: str = "dropbacks") -> float | None:
    pairs = []
    for row in meetings:
        value = _num(row.get(field)); weight = _num(row.get(weight_field))
        if value is not None and weight is not None and weight > 0:
            pairs.append((value, weight))
    if not pairs:
        return None
    return sum(v*w for v,w in pairs) / sum(w for _,w in pairs)


def normalize_qb_history(evidence: dict[str, list[dict]]) -> list[dict]:
    """Make recent PBP history explicit and stop presenting it as a career count.

    A meaningful game requires at least 10 charted dropbacks. Short cameos are
    retained in the audit but are excluded from the displayed meeting count.
    """
    audit = []
    for game_id, items in evidence.items():
        for item in items:
            meta = item.get("metadata") or {}
            if meta.get("family") != "qb_opponent_history":
                continue
            meetings = list(meta.get("meetings") or [])
            meaningful = [row for row in meetings if (_num(row.get("dropbacks")) or 0) >= 10]
            cameos = [row for row in meetings if (_num(row.get("dropbacks")) or 0) < 10]
            if not meaningful:
                item["strength"] = "Weak"
                item["summary"] = "Recent nflverse play-by-play contains only a short quarterback cameo against this opponent, so Sunday Signal does not present it as a prior start or meaningful meeting."
                meta.update({"recent_sample_games": 0, "excluded_cameos": len(cameos), "verification_scope": "recent_pbp_not_career"})
                item["metadata"] = meta
                continue

            title = str(item.get("title") or "")
            qb = title.split(" vs ", 1)[0].strip() if " vs " in title else "The quarterback"
            opponent = title.split(" vs ", 1)[1].split(":", 1)[0].strip() if " vs " in title else "the opponent"
            seasons = [int(row["season"]) for row in meaningful if _num(row.get("season")) is not None]
            start = min(seasons) if seasons else 2021
            latest = sorted(meaningful, key=lambda row: ((row.get("season") or 0), (row.get("week") or 0)), reverse=True)[0]
            dropbacks = int(sum(int(_num(row.get("dropbacks")) or 0) for row in meaningful))
            epa = _weighted(meaningful, "epa_per_dropback")
            success = _weighted(meaningful, "success_rate")
            latest_label = latest.get("human_label") or latest.get("label") or "the most recent meeting"
            plural = "game" if len(meaningful) == 1 else "games"
            cameo_text = f" A further {len(cameos)} short cameo{'s' if len(cameos) != 1 else ''} under 10 dropbacks is excluded from that game count." if cameos else ""
            performance = ""
            if epa is not None and success is not None:
                performance = f" Over {dropbacks} charted dropbacks in those games, he averaged {epa:+.2f} EPA/dropback with a {success:.0%} positive-EPA rate."
            item["summary"] = (
                f"In the nflverse play-by-play sample since {start}, {qb} has {len(meaningful)} meaningful {plural} against {opponent}; "
                f"the most recent was {latest_label}.{performance}{cameo_text} This is a recent analytical sample, not a career meeting count."
            )
            item["sample_size"] = dropbacks
            item["strength"] = "Strong" if len(meaningful) >= 5 and dropbacks >= 150 else "Moderate" if len(meaningful) >= 3 and dropbacks >= 75 else "Weak"
            meta.update({
                "games": len(meaningful),
                "recent_sample_games": len(meaningful),
                "recent_sample_start_season": start,
                "excluded_cameos": len(cameos),
                "meetings": meaningful,
                "cameos": cameos,
                "latest_meeting": latest,
                "epa_per_dropback": epa,
                "success_rate": success,
                "verification_scope": "recent_pbp_not_career",
            })
            item["metadata"] = meta
            audit.append({
                "game_id": game_id,
                "quarterback": qb,
                "opponent": opponent,
                "meaningful_recent_games": len(meaningful),
                "excluded_cameos": len(cameos),
                "sample_start_season": start,
                "dropbacks": dropbacks,
                "career_count_published": False,
            })
    return audit


def _family(item: dict) -> str:
    return str((item.get("metadata") or {}).get("family") or item.get("category") or "").lower()


def _advantage(item: dict) -> str | None:
    value = (item.get("metadata") or {}).get("advantage_team")
    return str(value) if value else None


def _pick_prob(row: pd.Series, field: str) -> float | None:
    value = _num(row.get(field))
    if value is None:
        return None
    return value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value


def _best(items: list[dict], predicate) -> dict | None:
    candidates = [item for item in items if predicate(item)]
    order = {"Strong": 3, "Moderate": 2, "Weak": 1}
    candidates.sort(key=lambda item: (order.get(str(item.get("strength")), 0), int(item.get("sample_size") or 0)), reverse=True)
    return candidates[0] if candidates else None


def rewrite_previews(predictions: pd.DataFrame, previews: dict[str, dict], evidence: dict[str, list[dict]]) -> None:
    rows = {str(row.game_id): row for _, row in predictions.iterrows()}
    for game_id, preview in previews.items():
        row = rows.get(str(game_id))
        if row is None:
            continue
        items = list(evidence.get(str(game_id), []))
        pick = str(row.get("pick")); home = str(row.get("home_team")); away = str(row.get("away_team"))
        opponent = away if pick == home else home
        pick_name, opponent_name = _nick(pick), _nick(opponent)
        event = _best(items, lambda item: _family(item) == "international_event")
        rivalry = _best(items, lambda item: _family(item) == "rivalry")
        travel = _best(items, lambda item: _family(item) == "international_travel")
        supporting = _best(items, lambda item: _advantage(item) == pick and _family(item) not in {"rivalry", "international_event", "international_travel"})
        counter = _best(items, lambda item: _advantage(item) == opponent and _family(item) not in {"rivalry", "international_event", "international_travel"})

        # `run_context.py` already owns the slate-aware public voice. Downstream
        # enrichment must not replace those case sections with raw evidence
        # summaries, because those summaries intentionally share family-level
        # scaffolding. Story-desk can still promote a genuinely special event or
        # rivalry and enrich the notebook without touching the composed cases.
        if bool((preview.get("editorial_voice") or {}).get("game_specific")):
            special_first = None
            if event and {away, home} == {"SF", "LA"}:
                preview["headline"] = "Rams-49ers takes a 154-game rivalry to Melbourne"
                special_first = (
                    "The Rams and 49ers have played 154 times, but never like this. Their season opens at the Melbourne Cricket Ground in the NFL's first regular-season game in Australia, "
                    "after the longest single-game city-to-city travel haul in league history. San Francisco leads the all-time series 79-72-3, so the opponent is familiar even if almost everything around the game is new."
                )
            if special_first:
                paragraphs = list(preview.get("paragraphs") or [])
                if paragraphs:
                    paragraphs[0] = special_first.strip()
                else:
                    paragraphs = [special_first.strip()]
                preview["paragraphs"] = paragraphs

            notebook = list(preview.get("notebook") or [])
            existing_titles = {str(item.get("title") or "") for item in notebook}
            for item in (event, rivalry, travel):
                if not item:
                    continue
                title = _expand(item.get("title") or "Notebook")
                if title in existing_titles:
                    continue
                notebook.append({
                    "title": title,
                    "summary": _expand(item.get("summary") or ""),
                    "source_url": item.get("source_url"),
                })
                existing_titles.add(title)
            preview["notebook"] = notebook[:5]
            preview["editorial_version"] = "story-desk-v3"
            continue

        final_pick = _pick_prob(row, "final_home_prob")
        pure_pick = _pick_prob(row, "pure_home_prob")
        market_pick = _pick_prob(row, "market_home_prob")

        if event and {away, home} == {"SF", "LA"}:
            preview["headline"] = "Rams-49ers takes a 154-game rivalry to Melbourne"
            first = (
                "The Rams and 49ers have played 154 times, but never like this. Their season opens at the Melbourne Cricket Ground in the NFL's first regular-season game in Australia, "
                "after the longest single-game city-to-city travel haul in league history. San Francisco leads the all-time series 79-72-3, so the opponent is familiar even if almost everything around the game is new."
            )
        elif rivalry:
            preview["headline"] = _expand(preview.get("headline") or f"{away}-{home}")
            first = _expand(rivalry.get("summary") or "")
            if supporting:
                first += " " + _expand(supporting.get("summary") or "")
        elif supporting:
            preview["headline"] = _expand(preview.get("headline") or f"Why LevLine likes {pick_name}")
            first = _expand(supporting.get("summary") or "")
            if counter:
                first += " " + _expand(counter.get("summary") or "")
        else:
            preview["headline"] = _expand(preview.get("headline") or f"{pick_name} gets the current LevLine edge")
            first = f"LevLine currently makes the {pick_name} the more likely winner, but there is no single explanatory matchup strong enough to carry the whole argument by itself."

        gap = None if pure_pick is None or market_pick is None else (pure_pick - market_pick) * 100
        if market_pick is None:
            second = f"LevLine has the {pick_name} at {_pct(final_pick)}. The market probability is unavailable for this run, so the published number is being carried by the football model."
        elif gap is not None and abs(gap) >= 4:
            direction = "more bullish" if gap > 0 else "more cautious"
            second = f"The disagreement with the market is part of the story: PURE has the {pick_name} at {_pct(pure_pick)}, versus {_pct(market_pick)} from the market. LevLine lands at {_pct(final_pick)}, {abs(gap):.1f} percentage points {direction} before the 75/25 blend."
        else:
            second = f"The football model and market are broadly in the same neighborhood: PURE has the {pick_name} at {_pct(pure_pick)}, the market at {_pct(market_pick)}, and LevLine publishes {_pct(final_pick)}."

        preview["paragraphs"] = [first.strip(), second.strip()]
        preview["case_for_pick"] = _expand((supporting or {}).get("summary") or f"The central probability and score projection favor the {pick_name}.")
        preview["case_for_opponent"] = _expand((counter or {}).get("summary") or f"The {opponent_name} need variance in the high-leverage parts of the game to outrun the central projection.")

        disagreement = _num(row.get("model_disagreement"))
        if disagreement is not None and disagreement >= 0.10:
            preview["what_could_make_us_wrong"] = f"The five football engines are unusually spread out here ({disagreement*100:.1f} percentage points of standard deviation). That is the first reason to treat the {pick_name} forecast with caution."
        elif counter:
            preview["what_could_make_us_wrong"] = f"The clearest way the {opponent_name} can break the forecast is the matchup flagged in {_expand(counter.get('title') or _family(counter)).lower()}."
        else:
            preview["what_could_make_us_wrong"] = "Turnovers, fourth-down decisions and explosive plays remain the fastest ways for a single game to outrun a central forecast."

        notebook = [item for item in (event, rivalry, travel) if item]
        preview["notebook"] = [
            {"title": _expand(item.get("title") or "Notebook"), "summary": _expand(item.get("summary") or ""), "source_url": item.get("source_url")}
            for item in notebook
        ]
        preview["editorial_version"] = "story-desk-v2"


def require_publication_quality(previews: dict[str, dict]) -> None:
    failures = []
    leads = []
    for game_id, preview in previews.items():
        public_text = " ".join([
            str(preview.get("headline") or ""),
            " ".join(preview.get("paragraphs") or []),
            str(preview.get("case_for_pick") or ""),
            str(preview.get("case_for_opponent") or ""),
            str(preview.get("what_could_make_us_wrong") or ""),
        ]).lower()
        for phrase in BANNED_PUBLICATION_PHRASES:
            if phrase in public_text:
                failures.append(f"{game_id}: banned template phrase '{phrase}'")
        paragraphs = preview.get("paragraphs") or []
        if paragraphs:
            leads.append(paragraphs[0].strip())
    if len(leads) != len(set(leads)):
        failures.append("top-level Read paragraphs are not unique")
    if failures:
        raise SystemExit("Publication polish gate failed: " + "; ".join(failures))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--probe-advanced", action="store_true")
    args = parser.parse_args()
    out = Path(args.output_dir)
    predictions = pd.read_csv(out / "this_week.csv")
    evidence = _read_json(out / "contextual_evidence.json", {})
    previews = _read_json(out / "game_previews.json", {})
    status = _read_json(out / "context_source_status.json", {})

    try:
        schedules = pd.read_csv(NFLVERSE_SCHEDULE_URL, low_memory=False)
    except Exception:
        schedules = None

    story = build_story_context(predictions, schedules)
    added = 0
    for game_id, items in story.items():
        existing = evidence.setdefault(game_id, [])
        titles = {str(item.get("title")) for item in existing}
        for item in items:
            if str(item.get("title")) not in titles:
                existing.append(item); titles.add(str(item.get("title"))); added += 1

    qb_audit = normalize_qb_history(evidence)
    rewrite_previews(predictions, previews, evidence)
    require_publication_quality(previews)

    status["story_desk"] = {
        "status": "healthy",
        "story_items_added": added,
        "games_with_notebook": sum(1 for p in previews.values() if p.get("notebook")),
        "editorial_version": "story-desk-v2",
        "guardrail": "Rivalry, event, history and fun-fact context is explanatory only and never changes LevLine numerically.",
    }
    status["qb_history_verification"] = {
        "status": "healthy",
        "recent_samples_audited": len(qb_audit),
        "career_counts_published": False,
        "meaningful_game_threshold_dropbacks": 10,
        "guardrail": "Displayed counts are explicitly recent nflverse PBP samples; short cameos do not count as meaningful games and no limited sample is presented as a career total.",
    }
    if args.probe_advanced:
        status["advanced_sources"] = probe_advanced_sources(args.season)

    _write_json(out / "contextual_evidence.json", evidence)
    _write_json(out / "game_previews.json", previews)
    _write_json(out / "context_source_status.json", status)
    _write_json(out / "qb_history_audit.json", qb_audit)


if __name__ == "__main__":
    main()

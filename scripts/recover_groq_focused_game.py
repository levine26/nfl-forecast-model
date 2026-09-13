from __future__ import annotations

"""Immediately recover one Groq-failed Sunday Signal game.

This is an editorial-only bridge. It prefers the freshest validated ChatGPT bundle that
contains the failed game, first considering the game-scoped fallback bundle and then the
full-slate current bundle. If no fresh ChatGPT payload exists, the existing provider
fallback module may reuse the last already-validated human Read as a continuity bridge
and explicitly leave requires_chatgpt_refresh=true.

The script never changes predictions, probabilities, locks, grading, model artifacts, or
market inputs.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from nfl_forecast.editorial_provider_fallback import (
    CHATGPT_FORECAST_PATH,
    CHATGPT_MAX_AGE_HOURS,
    CHATGPT_PRODUCER,
    CHATGPT_RESEARCH_MODE,
    recover_focused_payload,
)


def _manifest_time(root: Path, game_id: str, now: datetime) -> datetime | None:
    manifest_path = root / "manifest.json"
    payload_path = root / f"{game_id}.json"
    if not manifest_path.is_file() or not payload_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("producer") != CHATGPT_PRODUCER:
        return None
    if manifest.get("research_mode") != CHATGPT_RESEARCH_MODE:
        return None
    if manifest.get("forecast_path_identity") != CHATGPT_FORECAST_PATH:
        return None
    games = manifest.get("game_ids")
    if not isinstance(games, list) or game_id not in {str(value) for value in games}:
        return None
    try:
        generated = datetime.fromisoformat(str(manifest.get("generated_utc") or "").replace("Z", "+00:00"))
    except Exception:
        return None
    if generated.tzinfo is None:
        return None
    generated = generated.astimezone(timezone.utc)
    age_hours = (now - generated).total_seconds() / 3600.0
    if age_hours < -0.1 or age_hours > CHATGPT_MAX_AGE_HOURS:
        return None
    return generated


def choose_chatgpt_dir(game_id: str, now: datetime | None = None) -> Path:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    candidates = [
        Path("inputs/chatgpt_media/fallback"),
        Path("inputs/chatgpt_media/current"),
    ]
    fresh: list[tuple[datetime, Path]] = []
    for root in candidates:
        stamp = _manifest_time(root, game_id, current)
        if stamp is not None:
            fresh.append((stamp, root))
    if not fresh:
        return Path("inputs/chatgpt_media/__no_fresh_bundle__")
    fresh.sort(key=lambda item: item[0], reverse=True)
    return fresh[0][1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--provider-artifact", default="outputs/copilot_media_reads.json")
    parser.add_argument("--status-path", default="outputs/context_source_status.json")
    args = parser.parse_args()

    game_id = str(args.game_id)
    chosen = choose_chatgpt_dir(game_id)
    recovered, source = recover_focused_payload(
        game_id=game_id,
        output_path=args.output,
        reason=args.reason,
        chatgpt_dir=chosen,
        provider_artifact=args.provider_artifact,
        status_path=args.status_path,
    )
    print(f"{game_id}: immediate Groq recovery source={source} chatgpt_dir={chosen}")
    if not recovered:
        raise SystemExit(f"{game_id}: no safe editorial recovery payload available")


if __name__ == "__main__":
    main()

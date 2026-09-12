from __future__ import annotations

"""Overlay fresh ChatGPT research only onto games where Groq failed.

The normal full-slate ChatGPT ingestion remains available for a deliberate complete
handoff. This recovery path is narrower: the manifest may name only games that the
latest Groq run explicitly marked as needing ChatGPT refresh. Successful Groq games are
preserved from the already-validated provider artifact. The merged slate is then run
through the same deterministic composition, rendering, source, uniqueness, and
full-slate validators before it can be published.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import pandas as pd

from compose_copilot_media_reads import _extract_json
from nfl_forecast.editorial_provider_fallback import (
    CHATGPT_FORECAST_PATH,
    CHATGPT_MAX_AGE_HOURS,
    CHATGPT_PRODUCER,
    CHATGPT_RESEARCH_MODE,
    _qualitative_rationale,
)

MANIFEST_NAME = "manifest.json"


def _parse_utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("fallback manifest generated_utc must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _failure_targets(status: dict[str, Any]) -> set[str]:
    section = status.get("groq_provider_fallback") if isinstance(status, dict) else None
    games = section.get("games") if isinstance(section, dict) else None
    if not isinstance(games, dict):
        return set()
    return {
        str(gid)
        for gid, item in games.items()
        if isinstance(item, dict)
        and item.get("provider_result") == "failed"
        and bool(item.get("requires_chatgpt_refresh"))
    }


def validate_fallback_manifest(
    root: Path,
    canonical_game_ids: list[str],
    status: dict[str, Any],
    *,
    now: datetime | None = None,
) -> list[str]:
    path = root / MANIFEST_NAME
    if not path.is_file():
        raise ValueError(f"missing required fallback manifest: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fallback manifest must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("fallback manifest schema_version must be 1")
    if payload.get("producer") != CHATGPT_PRODUCER:
        raise ValueError(f"fallback manifest producer must be {CHATGPT_PRODUCER}")
    if payload.get("research_mode") != CHATGPT_RESEARCH_MODE:
        raise ValueError(f"fallback manifest research_mode must be {CHATGPT_RESEARCH_MODE}")
    if payload.get("forecast_path_identity") != CHATGPT_FORECAST_PATH:
        raise ValueError(f"fallback manifest forecast_path_identity must be {CHATGPT_FORECAST_PATH}")

    game_ids = payload.get("game_ids")
    if not isinstance(game_ids, list) or not game_ids:
        raise ValueError("fallback manifest game_ids must be a non-empty list")
    target_ids = [str(gid) for gid in game_ids]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError("fallback manifest contains duplicate game_ids")
    canonical = set(map(str, canonical_game_ids))
    if not set(target_ids).issubset(canonical):
        raise ValueError("fallback manifest contains a game outside the canonical slate")

    allowed = _failure_targets(status)
    unauthorized = sorted(set(target_ids) - allowed)
    if unauthorized:
        raise ValueError(
            "ChatGPT fallback may replace only Groq-failed games requiring refresh: "
            + ", ".join(unauthorized)
        )

    generated = _parse_utc(payload.get("generated_utc"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_hours = (current - generated).total_seconds() / 3600.0
    if age_hours < -0.1 or age_hours > CHATGPT_MAX_AGE_HOURS:
        raise ValueError(f"fallback manifest stale: age_hours={age_hours:.2f}")

    for gid in target_ids:
        file = root / f"{gid}.json"
        if not file.is_file():
            raise ValueError(f"missing ChatGPT fallback payload for {gid}: {file}")
    return target_ids


def _base_raw_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "headline": str(entry.get("headline") or "").strip(),
        "paragraph1": str(entry.get("paragraph1") or "").strip(),
        "model_rationale": _qualitative_rationale(entry),
        "sources": entry.get("sources") or [],
    }


def build_mixed_raw_payload(
    *,
    canonical_game_ids: list[str],
    base_artifact: dict[str, Any],
    chatgpt_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    games = base_artifact.get("games") if isinstance(base_artifact, dict) else None
    if not isinstance(games, dict):
        raise ValueError("base validated provider artifact is missing games")
    output: dict[str, dict[str, Any]] = {}
    for gid in canonical_game_ids:
        if gid in chatgpt_entries:
            output[gid] = chatgpt_entries[gid]
            continue
        entry = games.get(gid)
        if not isinstance(entry, dict):
            raise ValueError(f"base validated provider artifact missing successful game {gid}")
        raw = _base_raw_entry(entry)
        if not raw["headline"] or not raw["paragraph1"] or not raw["sources"]:
            raise ValueError(f"base validated provider artifact has unusable game {gid}")
        output[gid] = raw
    return {"games": output}


def mark_chatgpt_recovered(status: dict[str, Any], game_ids: list[str], *, now: datetime | None = None) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    result = dict(status)
    section = dict(result.get("groq_provider_fallback") or {})
    games = dict(section.get("games") or {})
    for gid in game_ids:
        item = dict(games.get(gid) or {})
        item.update({
            "fallback_source": "chatgpt",
            "requires_chatgpt_refresh": False,
            "chatgpt_refreshed_at_utc": current.isoformat(),
        })
        games[gid] = item
    section["games"] = games
    section["failed_games"] = sorted(games)
    section["status"] = (
        "degraded"
        if any(bool(item.get("requires_chatgpt_refresh")) for item in games.values() if isinstance(item, dict))
        else "healthy"
    )
    result["groq_provider_fallback"] = section
    return result


def _run(repo_root: Path, args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=repo_root, check=True)


def ingest(
    *,
    input_dir: Path,
    predictions: Path,
    previews: Path,
    evidence: Path,
    provider_artifact: Path,
    status_path: Path,
    output: Path,
) -> list[str]:
    repo_root = Path(__file__).resolve().parents[1]
    resolve = lambda path: path if path.is_absolute() else repo_root / path
    input_root = resolve(input_dir)
    prediction_path = resolve(predictions)
    preview_path = resolve(previews)
    evidence_path = resolve(evidence)
    provider_path = resolve(provider_artifact)
    context_status_path = resolve(status_path)
    output_path = resolve(output)

    frame = pd.read_csv(prediction_path)
    if "game_id" not in frame.columns:
        raise ValueError("canonical predictions are missing game_id")
    game_ids = list(frame["game_id"].astype(str))
    status = json.loads(context_status_path.read_text(encoding="utf-8"))
    targets = validate_fallback_manifest(input_root, game_ids, status)
    base = json.loads(provider_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chatgpt-failed-game-ingest-") as tmp:
        work = Path(tmp)
        accepted = work / "accepted"
        accepted.mkdir()
        chatgpt_entries: dict[str, dict[str, Any]] = {}

        for gid in targets:
            staged = accepted / f"{gid}.txt"
            shutil.copyfile(input_root / f"{gid}.json", staged)
            _run(repo_root, [
                "scripts/validate_single_copilot_game.py",
                "--input", str(staged),
                "--game-id", gid,
                "--predictions", str(prediction_path),
                "--accepted-dir", str(accepted),
            ])
            payload = _extract_json(staged.read_text(encoding="utf-8"))
            chatgpt_entries[gid] = payload["games"][gid]

        raw = work / "mixed-raw.json"
        composed = work / "composed.json"
        rendered = work / "rendered.json"
        raw.write_text(
            json.dumps(build_mixed_raw_payload(
                canonical_game_ids=game_ids,
                base_artifact=base,
                chatgpt_entries=chatgpt_entries,
            ), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        _run(repo_root, [
            "scripts/compose_copilot_media_reads.py",
            "--input", str(raw),
            "--predictions", str(prediction_path),
            "--previews", str(preview_path),
            "--evidence", str(evidence_path),
            "--output", str(composed),
        ])
        _run(repo_root, [
            "scripts/render_levline_paragraphs.py",
            "--input", str(composed),
            "--predictions", str(prediction_path),
            "--previews", str(preview_path),
            "--output", str(rendered),
        ])
        _run(repo_root, [
            "scripts/validate_copilot_media_reads.py",
            "--input", str(rendered),
            "--predictions", str(prediction_path),
            "--output", str(output_path),
        ])

    updated_status = mark_chatgpt_recovered(status, targets)
    context_status_path.write_text(json.dumps(updated_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"validated ChatGPT fallback for {len(targets)} Groq-failed games without replacing successful Groq games")
    return targets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="inputs/chatgpt_media/fallback")
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--previews", default="outputs/game_previews.json")
    parser.add_argument("--evidence", default="outputs/contextual_evidence.json")
    parser.add_argument("--provider-artifact", default="outputs/copilot_media_reads.json")
    parser.add_argument("--status", default="outputs/context_source_status.json")
    parser.add_argument("--output", default="outputs/copilot_media_reads.json")
    args = parser.parse_args()
    ingest(
        input_dir=Path(args.input_dir),
        predictions=Path(args.predictions),
        previews=Path(args.previews),
        evidence=Path(args.evidence),
        provider_artifact=Path(args.provider_artifact),
        status_path=Path(args.status),
        output=Path(args.output),
    )


if __name__ == "__main__":
    main()

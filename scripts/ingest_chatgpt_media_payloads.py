from __future__ import annotations

"""Ingest a complete ChatGPT-researched editorial slate through existing launch gates.

This module is intentionally editorial-only. It never computes or modifies forecast,
market, pick, lock, grading, or F-ST data. A bundle supplies only the human-analysis
fields already accepted from the external media writer, then reuses the repository's
focused and full-slate validators unchanged.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable

import pandas as pd


MANIFEST_NAME = "manifest.json"
EXPECTED_PRODUCER = "chatgpt-consumer-session"
EXPECTED_RESEARCH_MODE = "live-web-search"
EXPECTED_FORECAST_PATH = "F-ST-01-FROZEN-2026"
MAX_MANIFEST_AGE_HOURS = 4.0
_ALLOWED_PAYLOAD_SUFFIXES = {".json", ".txt"}


def _parse_utc(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("manifest generated_utc is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("manifest generated_utc must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_manifest(
    root: Path,
    expected_game_ids: Iterable[str],
    *,
    now: datetime | None = None,
) -> dict:
    """Validate provenance/freshness for one complete free-ingestion bundle."""
    path = root / MANIFEST_NAME
    if not path.is_file():
        raise ValueError(f"missing required ingestion manifest: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ingestion manifest must be a JSON object")

    if payload.get("schema_version") != 1:
        raise ValueError("ingestion manifest schema_version must be 1")
    if payload.get("producer") != EXPECTED_PRODUCER:
        raise ValueError(f"ingestion manifest producer must be {EXPECTED_PRODUCER}")
    if payload.get("research_mode") != EXPECTED_RESEARCH_MODE:
        raise ValueError(f"ingestion manifest research_mode must be {EXPECTED_RESEARCH_MODE}")
    if payload.get("forecast_path_identity") != EXPECTED_FORECAST_PATH:
        raise ValueError(f"ingestion manifest forecast_path_identity must be {EXPECTED_FORECAST_PATH}")

    expected = [str(gid) for gid in expected_game_ids]
    manifest_games = payload.get("game_ids")
    if not isinstance(manifest_games, list) or [str(gid) for gid in manifest_games] != expected:
        raise ValueError("ingestion manifest game_ids must exactly match the canonical slate order")
    if len(set(expected)) != len(expected):
        raise ValueError("canonical prediction slate contains duplicate game ids")

    generated = _parse_utc(payload.get("generated_utc"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_hours = (current - generated).total_seconds() / 3600.0
    if age_hours < -0.1 or age_hours > MAX_MANIFEST_AGE_HOURS:
        raise ValueError(f"ingestion manifest stale: age_hours={age_hours:.2f}")
    return payload


def discover_payloads(root: Path, expected_game_ids: Iterable[str]) -> dict[str, Path]:
    """Require exactly one focused payload file for every canonical matchup."""
    expected = [str(gid) for gid in expected_game_ids]
    expected_set = set(expected)
    found: dict[str, Path] = {}

    if not root.is_dir():
        raise ValueError(f"ingestion input directory does not exist: {root}")

    for path in sorted(root.iterdir()):
        if path.name == MANIFEST_NAME:
            continue
        if not path.is_file():
            raise ValueError(f"unexpected non-file in ingestion bundle: {path.name}")
        if path.suffix.lower() not in _ALLOWED_PAYLOAD_SUFFIXES:
            raise ValueError(f"unexpected ingestion bundle file: {path.name}")
        gid = path.stem
        if gid not in expected_set:
            raise ValueError(f"payload game id is not in canonical slate: {gid}")
        if gid in found:
            raise ValueError(f"duplicate focused payload for {gid}")
        found[gid] = path

    missing = [gid for gid in expected if gid not in found]
    if missing:
        raise ValueError("missing focused payloads: " + ", ".join(missing))
    return found


def _run(repo_root: Path, args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=repo_root, check=True)


def ingest(
    *,
    input_dir: Path,
    predictions: Path,
    previews: Path,
    evidence: Path,
    output: Path,
) -> None:
    """Validate, merge, compose, render, and full-slate validate one bundle."""
    repo_root = Path(__file__).resolve().parents[1]
    prediction_path = predictions if predictions.is_absolute() else repo_root / predictions
    preview_path = previews if previews.is_absolute() else repo_root / previews
    evidence_path = evidence if evidence.is_absolute() else repo_root / evidence
    input_root = input_dir if input_dir.is_absolute() else repo_root / input_dir
    output_path = output if output.is_absolute() else repo_root / output

    frame = pd.read_csv(prediction_path)
    if "game_id" not in frame.columns:
        raise ValueError("canonical predictions are missing game_id")
    game_ids = list(frame["game_id"].astype(str))
    validate_manifest(input_root, game_ids)
    payloads = discover_payloads(input_root, game_ids)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chatgpt-media-ingest-") as tmp:
        work = Path(tmp)
        accepted = work / "accepted"
        accepted.mkdir()
        raw = work / "raw.json"
        composed = work / "composed.json"
        rendered = work / "rendered.json"

        for gid in game_ids:
            staged = accepted / f"{gid}.txt"
            shutil.copyfile(payloads[gid], staged)
            _run(
                repo_root,
                [
                    "scripts/validate_single_copilot_game.py",
                    "--input",
                    str(staged),
                    "--game-id",
                    gid,
                    "--predictions",
                    str(prediction_path),
                    "--accepted-dir",
                    str(accepted),
                ],
            )

        _run(
            repo_root,
            [
                "scripts/merge_copilot_game_payloads.py",
                "--input-dir",
                str(accepted),
                "--predictions",
                str(prediction_path),
                "--output",
                str(raw),
            ],
        )
        _run(
            repo_root,
            [
                "scripts/compose_copilot_media_reads.py",
                "--input",
                str(raw),
                "--predictions",
                str(prediction_path),
                "--previews",
                str(preview_path),
                "--evidence",
                str(evidence_path),
                "--output",
                str(composed),
            ],
        )
        _run(
            repo_root,
            [
                "scripts/render_levline_paragraphs.py",
                "--input",
                str(composed),
                "--predictions",
                str(prediction_path),
                "--previews",
                str(preview_path),
                "--output",
                str(rendered),
            ],
        )
        _run(
            repo_root,
            [
                "scripts/validate_copilot_media_reads.py",
                "--input",
                str(rendered),
                "--predictions",
                str(prediction_path),
                "--output",
                str(output_path),
            ],
        )

    print(f"validated and ingested {len(game_ids)} ChatGPT-researched games -> {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="inputs/chatgpt_media/current")
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--previews", default="outputs/game_previews.json")
    parser.add_argument("--evidence", default="outputs/contextual_evidence.json")
    parser.add_argument("--output", default="outputs/copilot_media_reads.json")
    args = parser.parse_args()
    ingest(
        input_dir=Path(args.input_dir),
        predictions=Path(args.predictions),
        previews=Path(args.previews),
        evidence=Path(args.evidence),
        output=Path(args.output),
    )


if __name__ == "__main__":
    main()

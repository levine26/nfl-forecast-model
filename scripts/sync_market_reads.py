from __future__ import annotations

"""Atomically synchronize Sunday Signal's deterministic Read with published forecasts.

Never reruns context research, regenerates provider prose, or changes model/lock inputs.
The only allowed JSON mutation is paragraphs[1], using the existing canonical
LevLine editorial renderer. Validation precedes file replacement.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import tempfile

from nfl_forecast.editorial_model_read import render_model_paragraph
from nfl_forecast.public_forecast import build_public_forecasts
from scripts.render_levline_paragraphs import _factor

_CONTEXT = re.compile(r"(Football context: .+?)\s+The pick: .+? moneyline\.$", re.DOTALL)


class ReadSyncError(RuntimeError):
    """Do not publish forecasts and stale or incomplete editorial Reads together."""


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ReadSyncError(f"missing canonical forecast source: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ReadSyncError(f"empty canonical forecast source: {path}")
    return rows


def _preserved_context(paragraph: str, preview: dict, row: dict) -> str:
    match = _CONTEXT.search(paragraph)
    if match:
        return match.group(1).strip()
    pick = str(row["pick"])
    opponent = str(row["away_team"] if pick == row["home_team"] else row["home_team"])
    return _factor(preview, pick, opponent)


def _near(actual: object, expected: object) -> bool:
    try:
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-12)
    except (ValueError, TypeError):
        return False


def synchronize_reads(
    predictions: list[dict[str, str]],
    official: list[dict[str, str]],
    previews: dict,
    *,
    now_utc: datetime | None = None,
) -> tuple[dict, int]:
    """Validate an entire slate and return a complete, editorial-preserving replacement.

    Callers must NOT write a partial result if any game fails.
    """
    if not isinstance(previews, dict) or not predictions:
        raise ReadSyncError("missing or malformed game previews/current slate")
    ids = [str(row.get("game_id") or "").strip() for row in predictions]
    if not all(ids) or len(set(ids)) != len(ids) or set(previews) != set(ids):
        raise ReadSyncError("missing, extra, or duplicate game previews/canonical prediction rows")

    # The public bridge independently validates lock/lifecycle coherence, probability
    # sign, presentation spread and score. Locked games MUST use the lock snapshot.
    public = build_public_forecasts(predictions, official, now_utc=now_utc)
    by_id = {str(game["game_id"]): game for game in public["games"]}
    if len(by_id) != len(ids):
        raise ReadSyncError("duplicate canonical public forecast games")

    result: dict[str, dict] = {}
    changed = 0
    for row in predictions:
        gid = str(row["game_id"])
        game = by_id[gid]
        preview = previews[gid]
        if not isinstance(preview, dict):
            raise ReadSyncError(f"{gid}: malformed preview entry")
        paragraphs = preview.get("paragraphs")
        if not isinstance(paragraphs, list) or len(paragraphs) != 2:
            raise ReadSyncError(f"{gid}: Read must contain exactly two paragraphs")
        if any(not isinstance(p, str) or not p.strip() for p in paragraphs):
            raise ReadSyncError(f"{gid}: Read has an empty or malformed paragraph")
        if not isinstance(preview.get("headline"), str) or not preview["headline"].strip():
            raise ReadSyncError(f"{gid}: required human headline missing")
        if game["official_winner"] != row.get("pick") or not _near(
            game["official_home_win_probability"], row.get("final_home_prob")
        ):
            raise ReadSyncError(f"{gid}: this_week differs from the authoritative locked/public forecast")
        if game["provenance"]["model_version"] != row.get("model_version") or (
            game["provenance"]["artifact_id"] != (row.get("fst_artifact_id") or None)
        ):
            raise ReadSyncError(f"{gid}: frozen model version/artifact differs from public forecast")
        if not _near(game["football_only_home_win_probability"], row.get(
            "fst_pure_home_prob") or row.get("pure_home_prob")
        ):
            raise ReadSyncError(f"{gid}: football-only signal differs from public forecast")
        market = row.get("market_home_prob")
        if str(market).strip() and not _near(game["market_home_win_probability"], market):
            raise ReadSyncError(f"{gid}: market signal differs from public forecast")

        # Keep reporter/provider text, headline, sources, attribution and all other
        # editorial fields byte-for-byte equivalent as Python values.
        context = _preserved_context(paragraphs[1], preview, row)
        fresh = render_model_paragraph(row, context)
        expected_pick = f"The pick: {fresh.rsplit('The pick: ', 1)[-1]}"
        if not fresh.endswith(expected_pick) or fresh.count("The pick: ") != 1:
            raise ReadSyncError(f"{gid}: deterministic composer violated pick sentence")
        updated = dict(preview)
        updated["paragraphs"] = [paragraphs[0], fresh]
        result[gid] = updated
        changed += int(fresh != paragraphs[1])

    return result, changed


def synchronize_file(output_dir: Path, *, check: bool = False) -> int:
    predictions = _csv_rows(output_dir / "this_week.csv")
    official = _csv_rows(output_dir / "prediction_history.csv")
    previews_path = output_dir / "game_previews.json"
    if not previews_path.is_file():
        raise ReadSyncError(f"missing editorial preview source: {previews_path}")
    previews = json.loads(previews_path.read_text(encoding="utf-8"))
    updated, changed = synchronize_reads(predictions, official, previews)
    if check and changed:
        raise ReadSyncError(f"{changed}/{len(predictions)} Sunday Signal Reads disagree with canonical forecasts")
    if changed and not check:
        serialized = json.dumps(updated, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        # Verify the serialized payload before replacing the only published preview.
        if json.loads(serialized) != updated:
            raise ReadSyncError("preview serialization roundtrip failed")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=previews_path.parent,
            prefix=".game_previews.", suffix=".tmp", delete=False,
        ) as temporary:
            temporary.write(serialized)
            name = temporary.name
        try:
            os.replace(name, previews_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize/read-gate full-slate deterministic editorial from canonical public forecasts")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changes = synchronize_file(args.output_dir, check=args.check)
    except (ReadSyncError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"FAIL CLOSED: Sunday Signal Read/forecast publication: {exc}\n")
    print(f"Sunday Signal Read contract OK: {args.output_dir} | changed={changes} | check={args.check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Restore the most recent launch-grade Sunday Signal editorial snapshot from git history.

This is a recovery-only bridge for post-kickoff artifact contraction. It never changes
LevLine/F-ST predictions. It finds the newest ancestor whose previews, contextual evidence,
provider Reads, and launch status cover the entire frozen editorial roster, trims that
snapshot to the authorized roster, preserves the *current* Groq failed-game state, and
writes the recovered editorial artifacts back to the working tree for deterministic
failed-game overlay/validation.
"""

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any


ARTIFACTS = {
    "previews": "outputs/game_previews.json",
    "media": "outputs/copilot_media_reads.json",
    "evidence": "outputs/contextual_evidence.json",
    "status": "outputs/context_source_status.json",
}


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stderr=subprocess.DEVNULL,
    )


def _show_json(repo_root: Path, sha: str, path: str) -> dict[str, Any] | None:
    try:
        raw = _git(repo_root, "show", f"{sha}:{path}")
    except subprocess.CalledProcessError:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _coverage(payload: dict[str, Any], *, nested_games: bool = False) -> set[str]:
    if nested_games:
        games = payload.get("games")
        return set(games) if isinstance(games, dict) else set()
    return set(payload)


def snapshot_covers(
    *,
    roster_ids: set[str],
    previews: dict[str, Any],
    media: dict[str, Any],
    evidence: dict[str, Any],
    status: dict[str, Any],
) -> bool:
    if not roster_ids:
        return False
    if not roster_ids.issubset(_coverage(previews)):
        return False
    if not roster_ids.issubset(_coverage(media, nested_games=True)):
        return False
    if not roster_ids.issubset(_coverage(evidence)):
        return False

    provider = status.get("copilot_media") or {}
    finalizer = status.get("editorial_finalizer") or {}
    reporting = status.get("media_reporting") or {}
    if provider.get("status") != "healthy":
        return False
    if finalizer.get("status") != "healthy":
        return False
    if reporting.get("status") != "healthy":
        return False
    if int(provider.get("games_applied") or 0) < len(roster_ids):
        return False
    if int(finalizer.get("games") or 0) < len(roster_ids):
        return False
    if int(reporting.get("games_with_trusted_reporting") or 0) < len(roster_ids):
        return False
    return True


def _trim_game_map(payload: dict[str, Any], roster_ids: list[str]) -> dict[str, Any]:
    return {gid: payload[gid] for gid in roster_ids if gid in payload}


def trim_snapshot(
    *,
    roster_ids: list[str],
    previews: dict[str, Any],
    media: dict[str, Any],
    evidence: dict[str, Any],
    historical_status: dict[str, Any],
    current_status: dict[str, Any],
    source_commit: str = "",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected = len(roster_ids)
    trimmed_previews = _trim_game_map(previews, roster_ids)
    trimmed_evidence = _trim_game_map(evidence, roster_ids)

    historical_games = media.get("games")
    if not isinstance(historical_games, dict):
        raise RuntimeError("historical provider artifact is missing games")
    trimmed_media = dict(media)
    trimmed_media["games"] = _trim_game_map(historical_games, roster_ids)

    status = dict(historical_status)
    # Preserve the current unresolved-target truth. Historical provider health must never
    # erase games that the latest Groq pass explicitly marked for ChatGPT recovery.
    if "groq_provider_fallback" in current_status:
        status["groq_provider_fallback"] = current_status["groq_provider_fallback"]

    provider = dict(status.get("copilot_media") or {})
    provider.update({
        "status": "healthy",
        "games_applied": expected,
        "games_expected": expected,
    })
    status["copilot_media"] = provider

    finalizer = dict(status.get("editorial_finalizer") or {})
    finalizer.update({
        "status": "healthy",
        "games": expected,
        "unique_headlines": expected,
    })
    status["editorial_finalizer"] = finalizer

    reporting = dict(status.get("media_reporting") or {})
    reporting.update({
        "status": "healthy",
        "games": expected,
        "games_with_display_reporting": expected,
        "games_with_reporting": expected,
        "games_with_trusted_reporting": expected,
    })
    if "games_with_substantive_reporting" in reporting:
        reporting["games_with_substantive_reporting"] = min(
            expected,
            int(reporting.get("games_with_substantive_reporting") or 0),
        )
    reporting["last_good_snapshot_reused"] = True
    if source_commit:
        reporting["last_good_snapshot_source_commit"] = source_commit
    reporting["last_good_snapshot_guardrail"] = (
        "Post-kickoff recovery restored only previously launch-grade editorial artifacts "
        "for the frozen roster; current Groq failure targets remain authoritative."
    )
    status["media_reporting"] = reporting

    for section_name in ("previews", "evidence"):
        section = status.get(section_name)
        if isinstance(section, dict) and "games" in section:
            section = dict(section)
            section["games"] = expected
            status[section_name] = section

    return trimmed_previews, trimmed_media, trimmed_evidence, status


def find_last_good_snapshot(
    repo_root: Path,
    roster_ids: list[str],
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidates = _git(
        repo_root,
        "rev-list",
        "HEAD",
        "--",
        ARTIFACTS["media"],
        ARTIFACTS["previews"],
        ARTIFACTS["evidence"],
        ARTIFACTS["status"],
    ).splitlines()
    wanted = set(roster_ids)
    for sha in candidates:
        previews = _show_json(repo_root, sha, ARTIFACTS["previews"])
        media = _show_json(repo_root, sha, ARTIFACTS["media"])
        evidence = _show_json(repo_root, sha, ARTIFACTS["evidence"])
        status = _show_json(repo_root, sha, ARTIFACTS["status"])
        if not all(isinstance(x, dict) for x in (previews, media, evidence, status)):
            continue
        if snapshot_covers(
            roster_ids=wanted,
            previews=previews,
            media=media,
            evidence=evidence,
            status=status,
        ):
            return sha, previews, media, evidence, status
    raise RuntimeError(
        f"no launch-grade historical editorial snapshot covers all {len(roster_ids)} roster games"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--roster",
        type=Path,
        default=Path("inputs/sunday_signal/editorial_slate_roster.json"),
    )
    parser.add_argument(
        "--status",
        type=Path,
        default=Path("outputs/context_source_status.json"),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    roster_path = args.roster if args.roster.is_absolute() else repo_root / args.roster
    status_path = args.status if args.status.is_absolute() else repo_root / args.status

    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    roster_ids = [str(x) for x in roster.get("game_ids") or []]
    if not roster_ids or len(roster_ids) != len(set(roster_ids)):
        raise RuntimeError("editorial roster must contain unique game_ids")

    current_status = json.loads(status_path.read_text(encoding="utf-8"))
    sha, previews, media, evidence, historical_status = find_last_good_snapshot(
        repo_root,
        roster_ids,
    )
    trimmed = trim_snapshot(
        roster_ids=roster_ids,
        previews=previews,
        media=media,
        evidence=evidence,
        historical_status=historical_status,
        current_status=current_status,
        source_commit=sha,
    )
    for (name, path), payload in zip(ARTIFACTS.items(), trimmed):
        target = repo_root / path
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(
        f"restored launch-grade editorial snapshot {sha[:12]} for "
        f"{len(roster_ids)} frozen roster games"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

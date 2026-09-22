from __future__ import annotations

"""Restore the most recent launch-grade Sunday Signal editorial base from git history.

Post-kickoff production artifacts can contract as the live slate shrinks. Failed-game
ChatGPT recovery must preserve successful provider Reads rather than replacing them.
This helper scans ancestors for the newest editorial packet that fully covers the
persisted weekend roster, proves the provider/finalizer/reporting state was healthy,
prunes the packet to the authorized roster, and restores only the editorial base
artifacts. It never restores forecast probabilities or Groq failure state.
"""

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any


MEDIA_PATH = "outputs/copilot_media_reads.json"
PREVIEWS_PATH = "outputs/game_previews.json"
EVIDENCE_PATH = "outputs/contextual_evidence.json"
STATUS_PATH = "outputs/context_source_status.json"


def _git_text(repo_root: Path, commit: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        text=True,
        stderr=subprocess.DEVNULL,
    )


def _git_json(repo_root: Path, commit: str, path: str) -> dict[str, Any]:
    value = json.loads(_git_text(repo_root, commit, path))
    if not isinstance(value, dict):
        raise ValueError(f"{commit}:{path} must be a JSON object")
    return value


def _roster_ids(payload: dict[str, Any]) -> list[str]:
    ids = payload.get("game_ids")
    if not isinstance(ids, list):
        raise ValueError("editorial roster must contain game_ids")
    out = [str(value) for value in ids if str(value).strip()]
    if not out or len(out) != len(set(out)):
        raise ValueError("editorial roster game_ids must be non-empty and unique")
    return out


def packet_is_launch_grade(
    *,
    roster_ids: list[str],
    media: dict[str, Any],
    previews: dict[str, Any],
    evidence: dict[str, Any],
    status: dict[str, Any],
) -> bool:
    required = set(roster_ids)
    games = media.get("games")
    if not isinstance(games, dict):
        return False
    if not required.issubset(games):
        return False
    if not required.issubset(previews):
        return False
    if not required.issubset(evidence):
        return False

    finalizer = status.get("editorial_finalizer")
    provider = status.get("copilot_media")
    reporting = status.get("media_reporting")
    if not isinstance(finalizer, dict) or finalizer.get("status") != "healthy":
        return False
    if not isinstance(provider, dict) or provider.get("status") != "healthy":
        return False
    if not isinstance(reporting, dict) or reporting.get("status") != "healthy":
        return False

    expected = len(required)
    if int(finalizer.get("games") or 0) < expected:
        return False
    if int(finalizer.get("unique_headlines") or 0) < expected:
        return False
    if int(provider.get("games_applied") or 0) < expected:
        return False
    if int(reporting.get("games_with_trusted_reporting") or 0) < expected:
        return False
    return True


def prune_packet(
    *,
    roster_ids: list[str],
    media: dict[str, Any],
    previews: dict[str, Any],
    evidence: dict[str, Any],
    status: dict[str, Any],
    source_commit: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    ordered = list(roster_ids)
    pruned_media = dict(media)
    pruned_media["games"] = {gid: media["games"][gid] for gid in ordered}
    pruned_previews = {gid: previews[gid] for gid in ordered}
    pruned_evidence = {gid: evidence[gid] for gid in ordered}

    reporting = dict(status.get("media_reporting") or {})
    expected = len(ordered)
    for key in (
        "games",
        "games_with_reporting",
        "games_with_trusted_reporting",
        "games_with_display_reporting",
    ):
        reporting[key] = expected
    if "games_with_substantive_reporting" in reporting:
        reporting["games_with_substantive_reporting"] = min(
            expected, int(reporting.get("games_with_substantive_reporting") or 0)
        )
    reporting["status"] = "healthy"
    reporting["last_good_ancestor_reused"] = source_commit
    reporting["fallback_snapshot_guardrail"] = (
        "Successful provider Reads are restored only from a previously launch-grade "
        "ancestor that covers the exact persisted weekend roster."
    )
    snapshot = {
        "games": expected,
        "source_commit": source_commit,
        "media_reporting": reporting,
    }
    return pruned_media, pruned_previews, pruned_evidence, snapshot


def find_last_good_packet(
    repo_root: Path,
    roster_ids: list[str],
    *,
    max_commits: int = 250,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    commits = subprocess.check_output(
        ["git", "rev-list", f"--max-count={max_commits}", "HEAD"],
        cwd=repo_root,
        text=True,
    ).splitlines()
    for commit in commits:
        try:
            media = _git_json(repo_root, commit, MEDIA_PATH)
            previews = _git_json(repo_root, commit, PREVIEWS_PATH)
            evidence = _git_json(repo_root, commit, EVIDENCE_PATH)
            status = _git_json(repo_root, commit, STATUS_PATH)
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
            continue
        if packet_is_launch_grade(
            roster_ids=roster_ids,
            media=media,
            previews=previews,
            evidence=evidence,
            status=status,
        ):
            return commit, media, previews, evidence, status
    raise RuntimeError(
        f"no launch-grade ancestor found for all {len(roster_ids)} authorized games "
        f"within the last {max_commits} commits"
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--roster",
        type=Path,
        default=Path("inputs/sunday_signal/editorial_slate_roster.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--reporting-snapshot",
        type=Path,
        default=Path("/tmp/chatgpt-preserved-media-reporting.json"),
    )
    parser.add_argument("--max-commits", type=int, default=250)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    roster_path = args.roster if args.roster.is_absolute() else repo_root / args.roster
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    if not isinstance(roster, dict):
        raise SystemExit("editorial roster must be a JSON object")
    roster_ids = _roster_ids(roster)

    commit, media, previews, evidence, status = find_last_good_packet(
        repo_root,
        roster_ids,
        max_commits=args.max_commits,
    )
    media, previews, evidence, snapshot = prune_packet(
        roster_ids=roster_ids,
        media=media,
        previews=previews,
        evidence=evidence,
        status=status,
        source_commit=commit,
    )

    out = args.output_dir if args.output_dir.is_absolute() else repo_root / args.output_dir
    _write_json(out / "copilot_media_reads.json", media)
    _write_json(out / "game_previews.json", previews)
    _write_json(out / "contextual_evidence.json", evidence)
    _write_json(args.reporting_snapshot, snapshot)

    print(
        f"restored last-good Sunday Signal editorial base: commit={commit} "
        f"games={len(roster_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Audit main-branch advances that occur while Groq researches a slate.

Groq paragraph-one research is reusable when only deterministic forecast/diagnostic
outputs advance *and* the non-numeric forecast identity supplied to the provider stays
stable. Numeric probability/line/score movement is intentionally reconcilable because
the published LevLine paragraph is regenerated from latest main after this audit.

A pick flip, matchup/kickoff change, slate change, or production-model identity change
requires fresh provider research because the provider's qualitative rationale was built
for a different semantic forecast contract.
"""

import io
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


RESEARCH_SENSITIVE_OUTPUTS = frozenset(
    {
        "outputs/contextual_evidence.json",
        "outputs/game_previews.json",
        "outputs/context_source_status.json",
        "outputs/copilot_media_reads.json",
    }
)
FORECAST_CONTRACT_FIELDS = (
    "season",
    "week",
    "gameday",
    "gametime",
    "away_team",
    "home_team",
    "pick",
    "final_probability_strategy",
    "fst_artifact_id",
)


@dataclass(frozen=True)
class MainAdvanceAudit:
    changed: tuple[str, ...]
    research_sensitive: tuple[str, ...]
    non_output: tuple[str, ...]

    @property
    def safe_to_reconcile(self) -> bool:
        return not self.research_sensitive and not self.non_output


def audit_main_advance(paths: Iterable[str]) -> MainAdvanceAudit:
    changed = tuple(sorted({str(path).strip() for path in paths if str(path).strip()}))
    research_sensitive = tuple(path for path in changed if path in RESEARCH_SENSITIVE_OUTPUTS)
    non_output = tuple(path for path in changed if not path.startswith("outputs/"))
    return MainAdvanceAudit(
        changed=changed,
        research_sensitive=research_sensitive,
        non_output=non_output,
    )


def _clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    if text.endswith(".0"):
        head = text[:-2]
        if head.lstrip("-").isdigit():
            return head
    return text


def _forecast_contract(frame: pd.DataFrame) -> dict[str, dict[str, str]]:
    required = ("game_id", *FORECAST_CONTRACT_FIELDS)
    missing = [field for field in required if field not in frame.columns]
    if missing:
        raise ValueError("canonical predictions missing research-contract fields: " + ", ".join(missing))

    game_ids = frame["game_id"].map(_clean)
    if (game_ids == "").any():
        raise ValueError("canonical predictions contain a blank game_id")
    duplicates = sorted(game_ids[game_ids.duplicated()].unique())
    if duplicates:
        raise ValueError("canonical predictions contain duplicate game_id values: " + ", ".join(duplicates))

    games: dict[str, dict[str, str]] = {}
    for _, row in frame.iterrows():
        gid = _clean(row.get("game_id"))
        games[gid] = {field: _clean(row.get(field)) for field in FORECAST_CONTRACT_FIELDS}
    return games


def forecast_contract_differences(before: pd.DataFrame, after: pd.DataFrame) -> list[str]:
    """Return semantic changes that invalidate already-completed Groq research."""
    old_games = _forecast_contract(before)
    new_games = _forecast_contract(after)
    differences: list[str] = []

    old_ids = set(old_games)
    new_ids = set(new_games)
    for gid in sorted(old_ids - new_ids):
        differences.append(f"{gid}: removed from canonical slate")
    for gid in sorted(new_ids - old_ids):
        differences.append(f"{gid}: added to canonical slate")

    for gid in sorted(old_ids & new_ids):
        for field in FORECAST_CONTRACT_FIELDS:
            old_value = old_games[gid][field]
            new_value = new_games[gid][field]
            if old_value != new_value:
                differences.append(f"{gid}: {field} changed {old_value!r} -> {new_value!r}")
    return differences


def _origin_main_forecast() -> pd.DataFrame:
    result = subprocess.run(
        ["git", "show", "origin/main:outputs/this_week.csv"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return pd.read_csv(io.StringIO(result.stdout))


def _audit_forecast_contract() -> list[str]:
    current_path = Path("outputs/this_week.csv")
    if not current_path.is_file():
        raise FileNotFoundError("research-time outputs/this_week.csv is missing")
    current = pd.read_csv(current_path)
    latest = _origin_main_forecast()
    return forecast_contract_differences(current, latest)


def main() -> int:
    audit = audit_main_advance(sys.stdin.read().splitlines())
    if audit.research_sensitive:
        print("Main advanced in Groq research/publication inputs; refusing stale research:", file=sys.stderr)
        for path in audit.research_sensitive:
            print(path, file=sys.stderr)
    if audit.non_output:
        print("Main advanced outside deterministic outputs; refusing stale research:", file=sys.stderr)
        for path in audit.non_output:
            print(path, file=sys.stderr)
    if not audit.safe_to_reconcile:
        return 1

    if "outputs/this_week.csv" in audit.changed:
        try:
            differences = _audit_forecast_contract()
        except Exception as exc:
            print(
                f"Could not verify Groq research forecast contract after main advanced: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return 1
        if differences:
            print(
                "Main changed the non-numeric forecast contract used by Groq; fresh research is required:",
                file=sys.stderr,
            )
            for difference in differences:
                print(difference, file=sys.stderr)
            return 1
        print("Groq research forecast contract is unchanged; numeric forecast movement may be re-rendered safely.")

    print(f"Reconcilable deterministic-output advance: {len(audit.changed)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

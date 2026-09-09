from __future__ import annotations

"""CLI for immutable research-only LevLine challenger T-120 shadow scoring."""

import argparse
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_shadow import lock_shadow, normalize_history


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-locks", default="outputs/prediction_history.csv")
    parser.add_argument("--challenger-week", default="challenger_outputs/this_week_shadow.csv")
    parser.add_argument(
        "--shadow-history", default="challenger_outputs/prediction_history_shadow.csv"
    )
    args = parser.parse_args()

    production_locks_path = Path(args.production_locks)
    challenger_week_path = Path(args.challenger_week)
    shadow_history_path = Path(args.shadow_history)
    if not production_locks_path.exists():
        raise SystemExit(f"Missing production lock history: {production_locks_path}")
    if not challenger_week_path.exists():
        raise SystemExit(f"Missing challenger week: {challenger_week_path}")

    existing = _read_csv(shadow_history_path)
    history, added, precommit_skips = lock_shadow(
        _read_csv(production_locks_path),
        _read_csv(challenger_week_path),
        normalize_history(existing),
    )
    shadow_history_path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(shadow_history_path, index=False)
    print(f"challenger_shadow_locks_added={added}")
    print(f"challenger_shadow_precommit_skips={precommit_skips}")
    print(f"challenger_shadow_locks_total={len(history)}")


if __name__ == "__main__":
    main()

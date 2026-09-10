from __future__ import annotations

"""Research-only fixed matchup interactions for LevLine V09D-EWMA-INTERACTIONS-002.

The four features below are pre-registered in issue #93. Every constituent is an
existing pregame EWMA produced by the leakage-safe shifted feature pipeline. This
module does not fit models or access outcomes.
"""

import pandas as pd

INTERACTION_SPECS = {
    "pass": ("pass_epa_ewma", "def_pass_epa_allowed_ewma"),
    "rush": ("rush_epa_ewma", "def_rush_epa_allowed_ewma"),
    "overall_epa": ("off_epa_ewma", "def_epa_allowed_ewma"),
    "success": ("success_rate_ewma", "def_success_allowed_ewma"),
}

INTERACTION_COLUMNS = [f"diff_matchup_interaction_{name}" for name in INTERACTION_SPECS]


def add_predeclared_matchup_interactions(games: pd.DataFrame) -> pd.DataFrame:
    """Append exactly four home-vs-away nonlinear matchup interaction differentials."""
    out = games.copy()
    required: set[str] = set()
    for offense, defense in INTERACTION_SPECS.values():
        required.update(
            {
                f"home_{offense}",
                f"away_{offense}",
                f"home_{defense}",
                f"away_{defense}",
            }
        )
    missing = sorted(required - set(out.columns))
    if missing:
        raise ValueError(f"v0.9D matchup constituents unavailable: {missing}")

    for name, (offense, defense) in INTERACTION_SPECS.items():
        home_attack = pd.to_numeric(out[f"home_{offense}"], errors="coerce")
        away_defense_allowed = pd.to_numeric(out[f"away_{defense}"], errors="coerce")
        away_attack = pd.to_numeric(out[f"away_{offense}"], errors="coerce")
        home_defense_allowed = pd.to_numeric(out[f"home_{defense}"], errors="coerce")
        out[f"diff_matchup_interaction_{name}"] = (
            home_attack * away_defense_allowed - away_attack * home_defense_allowed
        )
    return out


def matchup_interaction_columns(frame: pd.DataFrame) -> list[str]:
    present = [column for column in INTERACTION_COLUMNS if column in frame.columns]
    if present != INTERACTION_COLUMNS:
        missing = [column for column in INTERACTION_COLUMNS if column not in frame.columns]
        raise RuntimeError(f"Expected exactly four pre-registered v0.9D interactions; missing {missing}")
    extras = sorted(
        column
        for column in frame.columns
        if column.startswith("diff_matchup_interaction_") and column not in INTERACTION_COLUMNS
    )
    if extras:
        raise RuntimeError(f"Undeclared v0.9D matchup interactions found: {extras}")
    return list(INTERACTION_COLUMNS)

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
V2_DIR = ROOT / "research" / "props" / "v2"
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))
SCRIPT = V2_DIR / "props_dynamic_role_v2.py"


def _module():
    spec = importlib.util.spec_from_file_location("props_dynamic_role_v2_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(player="p1", position="WR", team="ARI"):
    values = [0.20, 0.24, 0.26, 0.78, 0.86, 0.90]
    rows = []
    for i, share in enumerate(values, start=1):
        season = 2022 if i <= 3 else 2023
        week = i if season == 2022 else i - 3
        rows.append(
            {
                "game_id": f"g{i}",
                "season": season,
                "week": week,
                "team": team,
                "player_id": player,
                "position": position,
                "offense_pct": share,
                "offense_snaps": int(round(70 * share)),
            }
        )
    # Enough unrelated pre-target transitions for a stable pooled estimate.
    for j in range(60):
        rows.append(
            {
                "game_id": f"x{j}",
                "season": 2022,
                "week": (j % 17) + 1,
                "team": "BUF",
                "player_id": f"x{j//10}",
                "position": "WR",
                "offense_pct": 0.65 + 0.02 * ((j % 5) - 2),
                "offense_snaps": 45,
            }
        )
    return pd.DataFrame(rows)


def test_v2_reacts_to_role_inflection_without_target_game_rows():
    module = _module()
    snaps = _rows()
    # This target-week row is deliberately extreme and must be excluded.
    snaps = pd.concat(
        [
            snaps,
            pd.DataFrame(
                [
                    {
                        "game_id": "target",
                        "season": 2023,
                        "week": 4,
                        "team": "ARI",
                        "player_id": "p1",
                        "position": "WR",
                        "offense_pct": 0.01,
                        "offense_snaps": 1,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    current = pd.DataFrame([{"player_id": "p1", "position": "WR", "team": "ARI"}])
    adjustments, audit = module.build_dynamic_role_v2_adjustments(
        snaps,
        current,
        season=2023,
        week=4,
        team="ARI",
        mode="full",
    )
    est = audit["estimates"][0]
    assert audit["target_game_rows_used"] == 0
    assert audit["prop_outcomes_used_for_state_fit"] == 0
    assert est["history_games"] == 6
    assert est["posterior_snap_share"] > est["long_run_snap_share"]
    assert adjustments["p1"]["route_role_multiplier"] > 0.5
    assert adjustments["p1"]["target_role_multiplier"] > 1.0


def test_state_variances_are_fit_only_through_prior_season():
    module = _module()
    history = pd.DataFrame(
        [
            {"game_id":"a1","season":2021,"week":1,"team":"A","player_id":"p","position":"WR","snap_share":0.7},
            {"game_id":"a2","season":2021,"week":2,"team":"A","player_id":"p","position":"WR","snap_share":0.72},
            {"game_id":"a3","season":2022,"week":1,"team":"A","player_id":"p","position":"WR","snap_share":0.71},
            {"game_id":"a4","season":2022,"week":2,"team":"A","player_id":"p","position":"WR","snap_share":0.73},
            {"game_id":"future1","season":2023,"week":1,"team":"A","player_id":"p","position":"WR","snap_share":0.05},
            {"game_id":"future2","season":2023,"week":2,"team":"A","player_id":"p","position":"WR","snap_share":0.99},
        ]
    )
    fit_a = module.fit_role_dynamics(history, trained_through_season=2022)
    mutated = history.copy()
    mutated.loc[mutated["season"].eq(2023), "snap_share"] = [0.99, 0.01]
    fit_b = module.fit_role_dynamics(mutated, trained_through_season=2022)
    assert fit_a["WR"].process_variance == pytest.approx(fit_b["WR"].process_variance)
    assert fit_a["WR"].observation_variance == pytest.approx(fit_b["WR"].observation_variance)


def test_new_player_falls_back_without_inventing_role():
    module = _module()
    current = pd.DataFrame([{"player_id": "new", "position": "WR", "team": "ARI"}])
    adjustments, audit = module.build_dynamic_role_v2_adjustments(
        _rows(),
        current,
        season=2023,
        week=4,
        team="ARI",
    )
    assert adjustments == {}
    assert audit["fallback_player_ids"] == ["new"]


def test_uncertainty_is_reported_for_latent_state():
    module = _module()
    current = pd.DataFrame([{"player_id": "p1", "position": "WR", "team": "ARI"}])
    _, audit = module.build_dynamic_role_v2_adjustments(
        _rows(),
        current,
        season=2023,
        week=4,
        team="ARI",
    )
    est = audit["estimates"][0]
    assert est["posterior_logit_sd"] > 0
    assert 0 < est["posterior_snap_share"] < 1

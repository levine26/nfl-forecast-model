from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_levline_markets_live.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_levline_markets_live_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_target_week_requires_one_canonical_period(tmp_path):
    module = _module()
    slate = tmp_path / "this_week.csv"
    slate.write_text(
        "game_id,season,week\n"
        "g1,2026,2\n"
        "g2,2026,2\n",
        encoding="utf-8",
    )
    assert module.resolve_target_week(slate) == (2026, 2)

    slate.write_text(
        "game_id,season,week\n"
        "g1,2026,2\n"
        "g2,2026,3\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exactly one season/week"):
        module.resolve_target_week(slate)


def test_validate_priors_requires_explicit_route_and_unknown_availability(tmp_path):
    module = _module()
    priors = tmp_path / "priors.json"
    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90, "TE": 0.75},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    loaded = module.validate_priors(priors)
    assert loaded["route_prior_means"]["WR"] == 0.90

    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing TE"):
        module.validate_priors(priors)


def test_validate_priors_rejects_implicit_or_invalid_unknown_prior(tmp_path):
    module = _module()
    priors = tmp_path / "priors.json"
    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 0.90, "TE": 0.75},
                "availability_beta_priors": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="availability_beta_priors.UNKNOWN"):
        module.validate_priors(priors)

    priors.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.55, "WR": 1.2, "TE": 0.75},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 9.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="within"):
        module.validate_priors(priors)

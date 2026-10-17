from __future__ import annotations

import json
from pathlib import Path

from research.avoid_noop_challenger_calibration_churn import (
    is_precision_only_rewrite, restore_prior_bytes_if_no_material_change,
)


def data():
    return {
        "calibration": {
            "fst": {"games": 38, "calibration_intercept": -0.1880565320556954,
                    "calibration_slope": 0.6576321703195586},
            "market": {"games": 38, "calibration_intercept": -0.22224453836278146,
                       "calibration_slope": 0.690121792687696},
        },
        "paired": {"games": 38, "fst_wins": 23},
    }


def test_actual_observed_solver_roundoff_restores_prior_byte_identical_receipt(tmp_path):
    before = data()
    after = data()
    after["calibration"]["fst"]["calibration_intercept"] = -0.18805653205569528
    after["calibration"]["fst"]["calibration_slope"] = 0.6576321703195582
    after["calibration"]["market"]["calibration_intercept"] = -0.2222445383627814
    original_bytes = (json.dumps(before, indent=2, sort_keys=True) + "\n").encode()
    path = tmp_path / "prospective_evaluation.json"
    path.write_text(json.dumps(after, indent=2, sort_keys=True) + "\n")
    assert is_precision_only_rewrite(after, before)
    assert restore_prior_bytes_if_no_material_change(path, original_bytes)
    assert path.read_bytes() == original_bytes
    assert not restore_prior_bytes_if_no_material_change(path, original_bytes)


def test_research_game_count_and_any_material_metric_change_never_suppressed(tmp_path):
    old = data()
    new = data()
    new["calibration"]["fst"]["calibration_slope"] += 5e-6
    assert not is_precision_only_rewrite(new, old)
    new = data()
    new["paired"]["fst_wins"] += 1
    assert not is_precision_only_rewrite(new, old)
    p = tmp_path / "evaluation.json"
    p.write_text(json.dumps(new))
    old_data = json.dumps(old).encode()
    assert not restore_prior_bytes_if_no_material_change(p, old_data)
    assert json.loads(p.read_text())["paired"]["fst_wins"] == 24


def test_only_calibration_fields_may_be_tolerated():
    old = data()
    new = data()
    new["paired"]["other_numeric_metric"] = 1e-16
    assert not is_precision_only_rewrite(new, old)
    new = data()
    new["calibration"]["fst"]["games"] = 39
    assert not is_precision_only_rewrite(new, old)
    new = data()
    new["calibration"]["fst"]["calibration_slope"] += 1e-9
    assert not is_precision_only_rewrite(new, old)


def test_workflow_stabilizes_before_git_add_and_commit():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/challenger_shadow_lock.yml").read_text()
    marker = "research/avoid_noop_challenger_calibration_churn.py"
    assert marker in workflow
    # Bash must receive exactly one trailing backslash to continue the CLI arguments.
    assert (marker + " " + chr(92) + "\n") in workflow
    assert (marker + " " + chr(92) * 2 + "\n") not in workflow
    assert workflow.index("scripts/run_challenger_fst_evaluation.py") < workflow.index(marker)
    assert workflow.index(marker) < workflow.index("git add challenger_outputs/prediction_history_shadow.csv")
    assert "git diff --cached --quiet" in workflow
    assert "No new challenger shadow lock, grade, or prospective evaluation to publish." in workflow

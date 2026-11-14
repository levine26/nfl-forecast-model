from __future__ import annotations

"""Suppress research JSON commit churn caused only by sub-picopoint solver noise.

This operates solely on a derived challenger evaluation *display receipt*.
No probabilities, official prediction locks, training artifacts or numerical
evaluations are recomputed or altered. Only reuse the exact previously
committed JSON bytes if the freshly computed artifact has no material change.
"""

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
from typing import Any

CALIBRATION_FIELDS = ("calibration_intercept", "calibration_slope")
CALIBRATION_ABS_TOLERANCE = 1e-12


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def is_precision_only_rewrite(current: dict, previous: dict) -> bool:
    """True only when every difference is negligible calibration roundoff."""
    if not isinstance(current, dict) or not isinstance(previous, dict):
        return False
    normalized = deepcopy(current)
    a = normalized.get("calibration")
    b = previous.get("calibration")
    if isinstance(a, dict) and isinstance(b, dict):
        for candidate, current_values in a.items():
            historical_values = b.get(candidate)
            if not isinstance(current_values, dict) or not isinstance(historical_values, dict):
                continue
            for name in CALIBRATION_FIELDS:
                if name not in current_values or name not in historical_values:
                    continue
                cur = _numeric(current_values[name])
                prior = _numeric(historical_values[name])
                if (cur is not None and prior is not None
                        and abs(cur - prior) <= CALIBRATION_ABS_TOLERANCE):
                    current_values[name] = historical_values[name]
    return normalized == previous


def restore_prior_bytes_if_no_material_change(path: Path, previous_bytes: bytes) -> bool:
    """Keep evaluated metrics byte-identical when the only changes are noise."""
    generated_bytes = path.read_bytes()
    if generated_bytes == previous_bytes:
        return False
    generated = json.loads(generated_bytes)
    previous = json.loads(previous_bytes)
    if is_precision_only_rewrite(generated, previous):
        path.write_bytes(previous_bytes)
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("challenger_outputs/fst/prospective_evaluation.json"))
    parser.add_argument("--previous-ref", default="HEAD")
    args = parser.parse_args()
    if not args.path.is_file():
        parser.exit(1, f"Missing generated challenger evaluation: {args.path}\n")
    source = subprocess.run(
        ["git", "show", f"{args.previous_ref}:{args.path.as_posix()}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if source.returncode != 0:
        print("No prior committed challenger evaluation; retain newly generated receipt.")
        return 0
    try:
        restored = restore_prior_bytes_if_no_material_change(args.path, source.stdout)
    except (ValueError, TypeError) as exc:
        parser.exit(1, f"Invalid challenger evaluation JSON; no normalization: {exc}\n")
    if restored:
        print("Research evaluation unchanged except <=1e-12 calibration roundoff; restored exact committed bytes to prevent empty main churn.")
    else:
        print("Research evaluation contains material changes or is already identical; preserve generated evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

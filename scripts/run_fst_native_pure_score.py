from __future__ import annotations

"""Score current F-ST nested PURE on the runner's native CPU architecture.

This helper is intentionally narrow. Historical reconstruction/provenance remains in
``run_challenger_fst_shadow.py`` under the recovered forensic runtime; only current-game
base-model fitting is isolated here so a forced historical OpenBLAS core type cannot
execute unsupported instructions on a heterogeneous hosted runner.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.fst_nested_pure import fit_future_nested_stack


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--base-oof", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    historical = pd.read_pickle(args.historical)
    base_oof = pd.read_pickle(args.base_oof)
    current = pd.read_pickle(args.current)
    features = json.loads(args.features.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not features or not all(isinstance(x, str) for x in features):
        raise RuntimeError("Native F-ST scoring requires a non-empty feature-name list")

    probability = fit_future_nested_stack(
        historical,
        base_oof,
        current,
        features,
        seed=args.seed,
    )
    values = np.asarray(probability, dtype=float)
    if len(values) != len(current) or not np.isfinite(values).all():
        raise RuntimeError("Native F-ST scoring returned invalid current-game probabilities")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, values, allow_pickle=False)


if __name__ == "__main__":
    main()

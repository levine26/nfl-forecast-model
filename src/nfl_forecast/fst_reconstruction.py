from __future__ import annotations

"""Fail-closed reconstruction contract for the already-frozen F-ST-01 model.

The immutable candidate is the registered artifact. Historical reconstruction is
only a verification mechanism: training identity must match exactly, an
independent optimizer refit must agree within a fixed floating-point tolerance,
and scoring must use the registered coefficient literals rather than the refit.
"""

import json
import math
import os
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Any

from threadpoolctl import threadpool_info

from .challenger_fst import FrozenStackFit

REFIT_ABS_TOLERANCE = 1e-12
EXACT_IDENTITY_FIELDS = (
    "candidate_id",
    "training_data_sha256",
    "training_games",
    "training_first_season",
    "training_last_season",
)
NUMERICAL_REFIT_FIELDS = (
    "intercept",
    "market_logit_coefficient",
    "pure_logit_coefficient",
)
REQUIRED_PYTHON_VERSION = "3.11.16"
REQUIRED_ENVIRONMENT = {
    "OPENBLAS_CORETYPE": "SKYLAKEX",
    "OPENBLAS_NUM_THREADS": "4",
    "OMP_NUM_THREADS": "4",
    "MKL_NUM_THREADS": "4",
    "NUMEXPR_NUM_THREADS": "4",
}
REQUIRED_PACKAGE_VERSIONS = {
    "nflreadpy": "0.1.5",
    "polars": "1.44.2",
    "pandas": "3.0.5",
    "numpy": "2.4.6",
    "scikit-learn": "1.9.0",
    "scipy": "1.17.1",
    "xgboost": "3.2.0",
    "catboost": "1.2.10",
    "pyarrow": "25.0.1",
    "duckdb": "1.5.5",
    "joblib": "1.6.0",
    "threadpoolctl": "3.6.0",
}


def require_fst_reconstruction_runtime() -> dict[str, Any]:
    """Verify the recovered numerical runtime before historical reconstruction."""

    failures: list[str] = []
    actual_python = platform.python_version()
    if actual_python != REQUIRED_PYTHON_VERSION:
        failures.append(
            f"python={actual_python} (required {REQUIRED_PYTHON_VERSION})"
        )

    package_versions: dict[str, str] = {}
    for package, expected in REQUIRED_PACKAGE_VERSIONS.items():
        try:
            actual = version(package)
        except Exception as exc:  # pragma: no cover - diagnostic fail-closed path
            actual = f"unavailable:{exc!r}"
        package_versions[package] = actual
        if actual != expected:
            failures.append(f"{package}={actual} (required {expected})")

    environment = {key: os.environ.get(key) for key in REQUIRED_ENVIRONMENT}
    for key, expected in REQUIRED_ENVIRONMENT.items():
        if environment[key] != expected:
            failures.append(f"{key}={environment[key]!r} (required {expected!r})")

    pools = threadpool_info()
    blas_pools = [pool for pool in pools if pool.get("user_api") == "blas"]
    if not blas_pools:
        failures.append("no BLAS threadpool detected")
    for pool in blas_pools:
        architecture = str(pool.get("architecture") or "")
        if architecture.lower() != "skylakex":
            failures.append(
                f"BLAS architecture={architecture!r} (required 'SkylakeX')"
            )
        if int(pool.get("num_threads") or 0) != 4:
            failures.append(
                f"BLAS num_threads={pool.get('num_threads')!r} (required 4)"
            )

    report = {
        "python_version": actual_python,
        "required_python_version": REQUIRED_PYTHON_VERSION,
        "package_versions": package_versions,
        "required_package_versions": REQUIRED_PACKAGE_VERSIONS,
        "environment": environment,
        "required_environment": REQUIRED_ENVIRONMENT,
        "threadpools": pools,
        "matches": not failures,
        "failures": failures,
    }
    if failures:
        raise RuntimeError(
            "F-ST recovered reconstruction runtime mismatch: " + "; ".join(failures)
        )
    return report


def frozen_fit_from_identity(expected_identity: dict[str, Any]) -> FrozenStackFit:
    """Materialize the authoritative frozen fit from registered literals only."""

    required = set(EXACT_IDENTITY_FIELDS + NUMERICAL_REFIT_FIELDS)
    missing = sorted(required - set(expected_identity))
    if missing:
        raise ValueError(f"F-ST frozen identity missing fields: {missing}")
    return FrozenStackFit(
        intercept=float(expected_identity["intercept"]),
        market_logit_coefficient=float(expected_identity["market_logit_coefficient"]),
        pure_logit_coefficient=float(expected_identity["pure_logit_coefficient"]),
        training_games=int(expected_identity["training_games"]),
        training_first_season=int(expected_identity["training_first_season"]),
        training_last_season=int(expected_identity["training_last_season"]),
        training_data_sha256=str(expected_identity["training_data_sha256"]),
    )


def verify_fst_reconstruction_identity(
    output_dir: str | Path,
    input_manifest: dict[str, Any],
    refit: FrozenStackFit,
    expected_identity: dict[str, Any],
) -> dict[str, Any]:
    """Verify exact provenance and numerical refit consistency before scoring.

    Data/model identity fields are exact. Optimizer coefficients are diagnostic
    reconstruction values and must agree with the registered literals within the
    fixed absolute tolerance. They are never substituted for the registered
    coefficients used for scoring.
    """

    required = EXACT_IDENTITY_FIELDS + NUMERICAL_REFIT_FIELDS
    missing = [field for field in required if field not in expected_identity]
    if missing:
        raise ValueError(f"F-ST frozen identity spec missing fields: {missing}")
    if "source" not in expected_identity or not isinstance(expected_identity["source"], dict):
        raise ValueError("F-ST frozen identity spec requires an evidence source")

    actual = {
        "candidate_id": str(input_manifest["candidate_id"]),
        "training_data_sha256": str(refit.training_data_sha256),
        "training_games": int(refit.training_games),
        "training_first_season": int(refit.training_first_season),
        "training_last_season": int(refit.training_last_season),
        "intercept": float(refit.intercept),
        "market_logit_coefficient": float(refit.market_logit_coefficient),
        "pure_logit_coefficient": float(refit.pure_logit_coefficient),
    }
    expected = {
        "candidate_id": str(expected_identity["candidate_id"]),
        "training_data_sha256": str(expected_identity["training_data_sha256"]),
        "training_games": int(expected_identity["training_games"]),
        "training_first_season": int(expected_identity["training_first_season"]),
        "training_last_season": int(expected_identity["training_last_season"]),
        "intercept": float(expected_identity["intercept"]),
        "market_logit_coefficient": float(expected_identity["market_logit_coefficient"]),
        "pure_logit_coefficient": float(expected_identity["pure_logit_coefficient"]),
    }

    field_matches = {
        field: actual[field] == expected[field] for field in EXACT_IDENTITY_FIELDS
    }
    numerical_deltas: dict[str, float] = {}
    for field in NUMERICAL_REFIT_FIELDS:
        numerical_deltas[field] = float(actual[field] - expected[field])
        field_matches[field] = math.isclose(
            actual[field],
            expected[field],
            rel_tol=0.0,
            abs_tol=REFIT_ABS_TOLERANCE,
        )

    mismatched_fields = [field for field in required if not field_matches[field]]
    check = {
        "schema_version": 1,
        "check_stage": "post_refit_pre_scoring",
        "capture_context": input_manifest["capture_context"],
        "expected_source": expected_identity["source"],
        "authoritative_scoring_source": "registered_frozen_identity_literals",
        "exact_identity_fields": list(EXACT_IDENTITY_FIELDS),
        "numerical_refit_fields": list(NUMERICAL_REFIT_FIELDS),
        "refit_abs_tolerance": REFIT_ABS_TOLERANCE,
        "expected": expected,
        "actual_refit": actual,
        "numerical_deltas": numerical_deltas,
        "field_matches": field_matches,
        "mismatched_fields": mismatched_fields,
        "matches": not mismatched_fields,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "frozen_identity_check.json").write_text(
        json.dumps(check, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if mismatched_fields:
        raise RuntimeError(
            "F-ST frozen reconstruction mismatch before scoring: "
            + ", ".join(mismatched_fields)
        )
    return check

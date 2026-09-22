from __future__ import annotations

"""Forward-only scoring for Props 2.1 source-distribution evidence.

Continuous receipts preserve intervals/standard deviation but not the lossless simulation
distribution, so this module deliberately does NOT claim exact CRPS or PIT. It scores
interval coverage/sharpness and standardized residuals only. TD receipts preserve a
discrete count distribution, which supports exact 1+ TD Brier/log scores and conditional
multiclass log score when the realized count exists in preserved support.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping


class DistributionEvidenceError(RuntimeError):
    pass


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def score_continuous(forecast: Mapping[str, Any], actual: float) -> dict[str, Any]:
    evidence = forecast.get("source_v1_distribution_evidence")
    if not isinstance(evidence, Mapping):
        raise DistributionEvidenceError("receipt forecast is missing distribution evidence")
    if evidence.get("lossless_continuous_distribution_preserved") is not False:
        raise DistributionEvidenceError("unexpected continuous distribution preservation contract")

    mean = _num(forecast.get("model_mean"))
    sd = _num(evidence.get("standard_deviation"))
    interval = evidence.get("prediction_interval")
    if not isinstance(interval, Mapping):
        interval = {}
    low = _num(interval.get("low"))
    high = _num(interval.get("high"))
    nominal = _num(interval.get("coverage"))

    covered = None
    width = None
    if low is not None and high is not None:
        if high < low:
            raise DistributionEvidenceError("prediction interval high is below low")
        covered = low <= actual <= high
        width = high - low

    standardized_abs_error = None
    if mean is not None and sd is not None and sd > 0:
        standardized_abs_error = abs(actual - mean) / sd

    return {
        "metric_contract": "props21-continuous-distribution-evidence-v1",
        "actual": float(actual),
        "model_mean": mean,
        "standard_deviation": sd,
        "interval_low": low,
        "interval_high": high,
        "nominal_coverage": nominal,
        "interval_covered": covered,
        "interval_width": width,
        "standardized_absolute_error": standardized_abs_error,
        "exact_crps_available": False,
        "exact_pit_available": False,
        "unavailable_reason": "lossless_continuous_distribution_not_preserved",
    }


def _td_distribution(evidence: Mapping[str, Any]) -> dict[int, float]:
    raw = evidence.get("td_count_distribution")
    if not isinstance(raw, Mapping) or not raw:
        raise DistributionEvidenceError("TD distribution evidence is unavailable")
    result: dict[int, float] = {}
    for key, value in raw.items():
        try:
            count = int(key)
        except (TypeError, ValueError) as exc:
            raise DistributionEvidenceError(f"invalid TD support key: {key!r}") from exc
        probability = _num(value)
        if count < 0 or probability is None or probability < 0:
            raise DistributionEvidenceError("invalid TD distribution probability")
        result[count] = probability
    total = sum(result.values())
    if total <= 0 or abs(total - 1.0) > 1e-6:
        raise DistributionEvidenceError(f"TD distribution probabilities must sum to one; got {total}")
    return result


def score_td(forecast: Mapping[str, Any], actual_tds: int) -> dict[str, Any]:
    if actual_tds < 0:
        raise DistributionEvidenceError("actual TD count cannot be negative")
    evidence = forecast.get("source_v1_distribution_evidence")
    if not isinstance(evidence, Mapping):
        raise DistributionEvidenceError("receipt forecast is missing distribution evidence")
    distribution = _td_distribution(evidence)

    p_zero = distribution.get(0, 0.0)
    p_one_plus = 1.0 - p_zero
    y = 1.0 if actual_tds >= 1 else 0.0
    brier_1_plus = (p_one_plus - y) ** 2
    eps = 1e-15
    log_loss_1_plus = -(y * math.log(max(p_one_plus, eps)) + (1.0 - y) * math.log(max(1.0 - p_one_plus, eps)))

    multiclass_probability = distribution.get(actual_tds)
    multiclass_log_loss = (
        -math.log(max(multiclass_probability, eps))
        if multiclass_probability is not None
        else None
    )

    support = sorted(distribution)
    rps = None
    if support == list(range(0, max(support) + 1)) and actual_tds <= max(support):
        cumulative = 0.0
        score = 0.0
        for count in support[:-1]:
            cumulative += distribution[count]
            observed_cdf = 1.0 if actual_tds <= count else 0.0
            score += (cumulative - observed_cdf) ** 2
        rps = score

    return {
        "metric_contract": "props21-td-distribution-evidence-v1",
        "actual_tds": int(actual_tds),
        "p_one_plus_td": p_one_plus,
        "brier_1_plus_td": brier_1_plus,
        "log_loss_1_plus_td": log_loss_1_plus,
        "multiclass_probability_actual": multiclass_probability,
        "multiclass_log_loss": multiclass_log_loss,
        "ranked_probability_score": rps,
        "support_max": max(support),
        "full_realized_count_in_support": actual_tds in distribution,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--actual", type=float, required=True)
    parser.add_argument("--td", action="store_true")
    args = parser.parse_args()

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if not isinstance(receipt, Mapping):
        raise SystemExit("receipt must be a JSON object")
    forecast = receipt.get("forecast")
    if not isinstance(forecast, Mapping):
        raise SystemExit("receipt is missing forecast object")

    if args.td:
        if not float(args.actual).is_integer():
            raise SystemExit("TD actual must be an integer")
        result = score_td(forecast, int(args.actual))
    else:
        result = score_continuous(forecast, float(args.actual))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

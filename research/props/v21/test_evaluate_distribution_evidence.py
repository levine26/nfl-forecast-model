from __future__ import annotations

import pytest

from research.props.v21.evaluate_distribution_evidence import (
    DistributionEvidenceError,
    score_continuous,
    score_td,
)


def _continuous_forecast():
    return {
        "model_mean": 100.0,
        "source_v1_distribution_evidence": {
            "contract_version": "levline-props21-source-distribution-evidence-v0.1",
            "standard_deviation": 20.0,
            "prediction_interval": {"low": 60.0, "high": 140.0, "coverage": 0.90},
            "td_count_distribution": {},
            "lossless_continuous_distribution_preserved": False,
        },
    }


def _td_forecast():
    return {
        "source_v1_distribution_evidence": {
            "contract_version": "levline-props21-source-distribution-evidence-v0.1",
            "standard_deviation": None,
            "prediction_interval": {"low": None, "high": None, "coverage": None},
            "td_count_distribution": {"0": 0.25, "1": 0.45, "2": 0.22, "3": 0.08},
            "lossless_continuous_distribution_preserved": False,
        },
    }


def test_continuous_scores_exact_interval_evidence_without_claiming_crps_or_pit():
    result = score_continuous(_continuous_forecast(), 130.0)
    assert result["interval_covered"] is True
    assert result["interval_width"] == pytest.approx(80.0)
    assert result["standardized_absolute_error"] == pytest.approx(1.5)
    assert result["exact_crps_available"] is False
    assert result["exact_pit_available"] is False


def test_continuous_rejects_invalid_interval():
    row = _continuous_forecast()
    row["source_v1_distribution_evidence"]["prediction_interval"] = {
        "low": 140.0,
        "high": 60.0,
        "coverage": 0.90,
    }
    with pytest.raises(DistributionEvidenceError, match="high is below low"):
        score_continuous(row, 100.0)


def test_td_scores_preserved_discrete_distribution():
    result = score_td(_td_forecast(), 1)
    assert result["p_one_plus_td"] == pytest.approx(0.75)
    assert result["brier_1_plus_td"] == pytest.approx((0.75 - 1.0) ** 2)
    assert result["multiclass_probability_actual"] == pytest.approx(0.45)
    assert result["multiclass_log_loss"] is not None
    assert result["ranked_probability_score"] is not None
    assert result["full_realized_count_in_support"] is True


def test_td_marks_multiclass_score_unavailable_when_realized_tail_not_preserved():
    result = score_td(_td_forecast(), 4)
    assert result["multiclass_probability_actual"] is None
    assert result["multiclass_log_loss"] is None
    assert result["ranked_probability_score"] is None
    assert result["full_realized_count_in_support"] is False


def test_td_rejects_non_normalized_distribution():
    row = _td_forecast()
    row["source_v1_distribution_evidence"]["td_count_distribution"] = {
        "0": 0.5,
        "1": 0.6,
    }
    with pytest.raises(DistributionEvidenceError, match="sum to one"):
        score_td(row, 1)

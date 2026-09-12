from __future__ import annotations

import pandas as pd
import pytest

from research.evaluate_availability_practice_state_crosscheck_v3 import (
    practice_state_reverse_identity_metrics,
)


def test_blank_practice_rows_do_not_contaminate_reverse_identity_denominator() -> None:
    official = pd.DataFrame(
        {
            "external_practice_status": [
                "Full Participation in Practice",
                "Limited Participation in Practice",
                "Did Not Participate In Practice",
                None,
                None,
            ]
        }
    )
    unresolved = pd.DataFrame({"external_practice_status": [None, None]})
    metrics = practice_state_reverse_identity_metrics(official, unresolved)
    assert metrics["official_recognized_practice_rows"] == 3
    assert metrics["unresolved_recognized_practice_rows"] == 0
    assert metrics["resolved_recognized_practice_rows"] == 3
    assert metrics["official_practice_state_to_canonical_identity_resolution_rate"] == 1.0
    assert metrics["official_rows_without_recognized_practice_state"] == 2
    assert metrics["unresolved_rows_without_recognized_practice_state"] == 2


def test_unresolved_recognized_practice_row_remains_in_denominator() -> None:
    official = pd.DataFrame(
        {
            "external_practice_status": [
                "Full Participation in Practice",
                "Limited Participation in Practice",
                "Did Not Participate In Practice",
                None,
            ]
        }
    )
    unresolved = pd.DataFrame(
        {"external_practice_status": ["Limited Participation in Practice", None]}
    )
    metrics = practice_state_reverse_identity_metrics(official, unresolved)
    assert metrics["official_recognized_practice_rows"] == 3
    assert metrics["unresolved_recognized_practice_rows"] == 1
    assert metrics["resolved_recognized_practice_rows"] == 2
    assert metrics["official_practice_state_to_canonical_identity_resolution_rate"] == pytest.approx(2 / 3)


def test_no_recognized_practice_rows_fails_closed() -> None:
    official = pd.DataFrame({"external_practice_status": [None, ""]})
    unresolved = pd.DataFrame({"external_practice_status": [None]})
    with pytest.raises(ValueError, match="no recognized official practice-state rows"):
        practice_state_reverse_identity_metrics(official, unresolved)

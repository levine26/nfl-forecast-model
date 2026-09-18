from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "research" / "props" / "v2" / "market_microstructure_v2.py"


def _module():
    spec = importlib.util.spec_from_file_location("market_microstructure_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _record(captured, kickoff, line, p, std, a_line, b_line, a_p, b_p):
    books=[
        {
            "sportsbook_key":"a","line":a_line,"over_no_vig":a_p,
            "sportsbook_last_update_utc":(captured-timedelta(minutes=4)).isoformat(),
        },
        {
            "sportsbook_key":"b","line":b_line,"over_no_vig":b_p,
            "sportsbook_last_update_utc":(captured-timedelta(minutes=11)).isoformat(),
        },
    ]
    return {
        "snapshot_id":f"s-{captured.timestamp()}",
        "captured_at_utc":captured.isoformat(),
        "kickoff_utc":kickoff.isoformat(),
        "game_id":"g","player_id":"p","prop_type":"receiving_yards",
        "research_only":True,"production_authorized":False,
        "market_artifact":{
            "game_id":"g","player_id":"p","prop_type":"receiving_yards",
            "consensus_line":line,"consensus_no_vig_p_over":p,
            "sportsbook_count":2,"line_stddev":std,"line_range":abs(a_line-b_line),
            "individual_books":books,
        },
    }


def test_point_in_time_features_and_future_market_target_are_separated():
    m=_module()
    kickoff=datetime(2026,9,20,20,tzinfo=timezone.utc)
    t0=kickoff-timedelta(hours=12)
    t1=kickoff-timedelta(hours=6)
    rows=[
        _record(t0,kickoff,64.5,0.50,1.0,63.5,65.5,0.48,0.52),
        _record(t1,kickoff,65.5,0.54,0.5,65.5,65.5,0.53,0.55),
    ]
    out=m.build_microstructure_rows(rows)
    assert len(out)==2
    first, second=out
    assert first["line_move_since_previous"] is None
    assert first["evaluation_only_targets"]["line_move_to_final_observed"]==pytest.approx(1.0)
    assert second["line_move_since_previous"]==pytest.approx(1.0)
    assert second["probability_move_since_previous"]==pytest.approx(0.04)
    assert second["line_velocity_per_hour"]==pytest.approx(1/6)
    assert second["convergence_velocity_per_hour"]>0
    assert set(second["books_line_changed_since_previous"])=={"a"}
    assert second["same_threshold_price_book_count"]==2
    assert second["max_quote_age_minutes"]==pytest.approx(11.0)
    assert second["game_outcome_used"] is False


def test_different_lines_do_not_create_fake_price_dispersion():
    m=_module()
    kickoff=datetime(2026,9,20,20,tzinfo=timezone.utc)
    t=kickoff-timedelta(hours=6)
    out=m.build_microstructure_rows([
        _record(t,kickoff,64.5,0.51,0.5,64.5,65.5,0.49,0.56)
    ])[0]
    assert out["same_threshold_price_book_count"]==1
    assert out["same_threshold_price_stddev"]==0.0


def test_post_kickoff_history_fails_closed():
    m=_module()
    kickoff=datetime(2026,9,20,20,tzinfo=timezone.utc)
    with pytest.raises(m.MarketMicrostructureError,match="post-kickoff"):
        m.build_microstructure_rows([
            _record(kickoff+timedelta(seconds=1),kickoff,64.5,0.5,0.0,64.5,64.5,0.5,0.5)
        ])


def test_rejects_non_research_row():
    m=_module()
    kickoff=datetime(2026,9,20,20,tzinfo=timezone.utc)
    row=_record(kickoff-timedelta(hours=1),kickoff,64.5,0.5,0.0,64.5,64.5,0.5,0.5)
    row["production_authorized"]=True
    with pytest.raises(m.MarketMicrostructureError,match="research-only"):
        m.build_microstructure_rows([row])

from __future__ import annotations
from datetime import datetime,timedelta,timezone
import importlib.util,json,math
from pathlib import Path
import tempfile
HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("v3_keymass",HERE/"v3_keymass.py"); core=importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(core)
G=(0.2,0.35,0.15)
def test_unbounded_pmf_normalizes_and_is_nonnegative():
    vals=[core.cell(m,4.5,13.,6.,G) for m in range(-2000,2001)]; assert all(math.isfinite(x) and x>=0 for x in vals); assert abs(sum(vals)-1.)<1e-8; assert core.cell(100,4.5,13.,6.,G)>0; assert core.cell(-100,4.5,13.,6.,G)>0; assert core.leq(50,4.5,13.,6.,G)<1.
def test_sign_reversal_symmetry():
    for m in (-21,-7,-3,0,3,7,18): assert math.isclose(core.cell(m,5.5,12.,10.,G),core.cell(-m,-5.5,12.,10.,G),rel_tol=0,abs_tol=1e-13)
def test_raw_bookmaker_sign_conversion(): assert core.canonical_home_margin_from_bookmaker_home_point(-3.5)==3.5 and core.canonical_home_margin_from_bookmaker_home_point(2.5)==-2.5
def test_whole_point_has_structural_push_half_point_does_not():
    whole=core.cpl_probs(3.,13.,6.,G,3.); half=core.cpl_probs(3.,13.,6.,G,3.5); assert whole[1]>0 and half[1]==0; assert math.isclose(sum(whole),1.,abs_tol=1e-12); assert math.isclose(sum(half),1.,abs_tol=1e-12)
def _record(now):
    kickoff=now+timedelta(hours=6); target=kickoff-timedelta(hours=2); request=target-timedelta(minutes=3)
    return {"schema_version":"1.0","candidate_id":core.CANDIDATE_ID,"null_id":core.NULL_ID,"game_id":"2026_TEST_A_B","season":2026,"week":99,"kickoff_timestamp_utc":kickoff.isoformat(),"prediction_timestamp_utc":(target+timedelta(minutes=1)).isoformat(),"market_provider":"The Odds API","market_horizon":core.HORIZON,"market_target_timestamp_utc":target.isoformat(),"market_request_timestamp_utc":request.isoformat(),"market_quote_max_timestamp_utc":request.isoformat(),"market_event_id":"evt","market_source_count":3,"market_source_names":["a","b","c"],"raw_home_spread_point":-3.,"canonical_home_margin":3.,"home_spread_price":-110,"away_spread_price":-110,"candidate_pmf":core.pmf_descriptor(3.,13.,6.,G),"null_pmf":core.pmf_descriptor(3.,13.,6.,(0.,0.,0.)),"candidate_cover_push_loss":dict(zip(("cover","push","loss"),core.cpl_probs(3.,13.,6.,G,3.))),"null_cover_push_loss":dict(zip(("cover","push","loss"),core.cpl_probs(3.,13.,6.,(0.,0.,0.),3.))),"raw_input_hash":"a"*64,"model_code_hash":"b"*64,"config_hash":"c"*64}
def test_t120_timestamp_firewall():
    r=_record(datetime(2026,9,24,18,tzinfo=timezone.utc)); core.validate_prediction_record(r); target=datetime.fromisoformat(r["market_target_timestamp_utc"]); r["market_request_timestamp_utc"]=(target+timedelta(seconds=1)).isoformat()
    try: core.validate_prediction_record(r)
    except core.V3ContractError: pass
    else: raise AssertionError("after-horizon request accepted")
def test_completed_outcome_fields_are_rejected():
    r=_record(datetime(2026,9,24,18,tzinfo=timezone.utc)); r["home_score"]=27
    try: core.validate_prediction_record(r)
    except core.V3ContractError: pass
    else: raise AssertionError("outcome field accepted")
def test_serialization_hash_is_deterministic_and_append_is_immutable():
    r=_record(datetime(2026,9,24,18,tzinfo=timezone.utc)); a=core.serialize_prediction_record(r); b=core.serialize_prediction_record(dict(reversed(list(r.items())))); assert a==b; decoded=json.loads(a); assert len(decoded["prediction_hash"])==64
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"ledger.jsonl"; first=core.append_immutable_jsonl(p,r); before=p.read_bytes()
        try: core.append_immutable_jsonl(p,r)
        except core.V3ContractError: pass
        else: raise AssertionError("duplicate immutable prediction accepted")
        assert p.read_bytes()==before and first==decoded["prediction_hash"]
def test_training_script_hard_codes_pre_2026_era():
    text=(HERE/"fit_frozen_parameters.py").read_text(encoding="utf-8"); assert "TRAIN_END = 2025" in text and "range(TRAIN_START, TRAIN_END + 1)" in text

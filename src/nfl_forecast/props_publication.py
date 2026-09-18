from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PUBLIC_CONTRACT_VERSION = "levline-props-public-v0.1"
UPSTREAM_CONTRACT_VERSION = "levline-props-forecast-v0.1"
HISTORY_CONTRACT_VERSION = "levline-props-history-v0.1"
RESEARCH_LABEL = "LEVLINE PROPS — RESEARCH BETA"
QUALITY_STATES = {"HIGH", "MEDIUM", "LOW", "INSUFFICIENT"}
SIGNAL_STATES = {"MODEL EDGE", "WATCH", "NO SIGNAL"}
POSITION_MARKETS = {
    "QB": {"passing_yards", "rushing_yards", "passing_tds", "rushing_td", "anytime_td"},
    "RB": {"rushing_yards", "receiving_yards", "receptions", "rushing_td", "receiving_td", "anytime_td"},
    "WR": {"receiving_yards", "receptions", "receiving_td", "anytime_td"},
    "TE": {"receiving_yards", "receptions", "receiving_td", "anytime_td"},
}
LINE_MARKETS = {"passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds"}
TD_BINARY_MARKETS = {"rushing_td", "receiving_td", "anytime_td"}

class PropsPublicationError(RuntimeError): pass

def _text(v):
    if v is None: return None
    s=str(v).strip()
    return None if not s or s.lower() in {"nan","none","null","<na>"} else s

def _num(v):
    try: n=float(v)
    except (TypeError,ValueError): return None
    return n if math.isfinite(n) else None

def _bool(v, default=False):
    if isinstance(v,bool): return v
    if v is None: return default
    return str(v).strip().lower() in {"1","true","yes","y"}

def _dt(v):
    s=_text(v)
    if not s: return None
    try: d=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError: return None
    return None if d.tzinfo is None else d.astimezone(timezone.utc)

def _iso(v):
    d=_dt(v); return d.isoformat() if d else None

def _map(v): return v if isinstance(v,Mapping) else {}
def _list(v): return list(v) if isinstance(v,Sequence) and not isinstance(v,(str,bytes,bytearray)) else []
def _prob(v):
    n=_num(v); return n if n is not None and 0<=n<=1 else None

def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def _copy(v): return json.loads(_canon(v))
def _sha(v): return hashlib.sha256(_canon(v).encode()).hexdigest()

def american_odds_from_probability(p):
    if p is None or not 0 < p < 1: return None
    return int(round(-100*p/(1-p))) if p>=.5 else int(round(100*(1-p)/p))

def _kind(prop): return "OVER_UNDER" if prop in LINE_MARKETS else "BINARY_TD" if prop in TD_BINARY_MARKETS else "UNKNOWN"

def _forecast_id(row):
    m=_map(row.get("market")); model=_map(row.get("model"))
    key={"player_id":_text(row.get("player_id")),"game_id":_text(row.get("game_id")),"prop_type":_text(row.get("prop_type")),"forecast_timestamp_utc":_iso(row.get("forecast_timestamp_utc")),"market_source":_text(m.get("source")),"market_line":_num(m.get("line")),"model_version":_text(model.get("version") or row.get("model_version"))}
    return "prop_"+_sha(key)[:24]

def _drivers(v):
    out=[]
    for r in _list(v)[:8]:
        if isinstance(r,str):
            if _text(r): out.append({"label":_text(r),"direction":None,"detail":None})
        elif isinstance(r,Mapping) and _text(r.get("label")):
            direction=(_text(r.get("direction")) or "").upper() or None
            if direction not in {None,"UP","DOWN","NEUTRAL"}: direction=None
            out.append({"label":_text(r.get("label")),"direction":direction,"detail":_text(r.get("detail"))})
    return out

def _reasons(row, now):
    out=[]; pos=(_text(row.get("position")) or "").upper(); prop=_text(row.get("prop_type"))
    if not _bool(row.get("player_identity_resolved")) or not _text(row.get("player_id")) or not _text(row.get("player")): out.append("player_identity_unresolved")
    if not all(_text(row.get(k)) for k in ("game_id","team","opponent")): out.append("game_identity_incomplete")
    if pos not in POSITION_MARKETS: out.append("position_invalid")
    elif prop not in POSITION_MARKETS[pos]: out.append("unsupported_position_market")
    forecast,horizon,kickoff=(_dt(row.get(k)) for k in ("forecast_timestamp_utc","data_horizon_utc","kickoff_utc"))
    if forecast is None: out.append("forecast_timestamp_invalid")
    if horizon is None: out.append("data_horizon_timestamp_invalid")
    if kickoff is None: out.append("kickoff_timestamp_invalid")
    if forecast and kickoff and forecast>=kickoff: out.append("forecast_not_pregame")
    if horizon and kickoff and horizon>=kickoff: out.append("data_horizon_not_pregame")
    if horizon and forecast and horizon>forecast: out.append("data_horizon_after_forecast")
    if kickoff and now>=kickoff: out.append("game_started")
    market=_map(row.get("market")); model=_map(row.get("model")); quality=_map(row.get("data_quality")); market_at=_dt(market.get("captured_utc"))
    if not _text(market.get("source")): out.append("market_source_missing")
    if market_at is None: out.append("market_timestamp_invalid")
    elif forecast and market_at>forecast: out.append("market_after_forecast")
    elif kickoff and market_at>=kickoff: out.append("market_not_pregame")
    if _kind(prop)=="OVER_UNDER":
        if _num(market.get("line")) is None: out.append("market_line_invalid")
        if _num(market.get("over_price_american")) is None or _num(market.get("under_price_american")) is None: out.append("market_price_invalid")
        no,nu=_prob(market.get("no_vig_over_probability")),_prob(market.get("no_vig_under_probability"))
        if no is None or nu is None: out.append("market_no_vig_probability_invalid")
        elif not math.isclose(no+nu,1,abs_tol=1e-6): out.append("market_no_vig_accounting_failed")
        if _num(model.get("fair_line")) is None: out.append("fair_line_invalid")
        if _num(model.get("mean")) is None or _num(model.get("median")) is None: out.append("model_projection_missing")
        over,under,push=_prob(model.get("over_probability")),_prob(model.get("under_probability")),_prob(model.get("push_probability"))
        line=_num(market.get("line"))
        if push is None and line is not None and not line.is_integer(): push=0.0
        if over is None or under is None or push is None: out.append("model_probabilities_invalid")
        elif not math.isclose(over+under+push,1,abs_tol=1e-6): out.append("probability_accounting_failed")
    elif _kind(prop)=="BINARY_TD":
        if _num(market.get("td_price_american")) is None: out.append("market_price_invalid")
        if _prob(market.get("no_vig_probability")) is None: out.append("market_no_vig_probability_invalid")
        if _prob(model.get("td_probability")) is None: out.append("model_td_probability_invalid")
        etd=_num(model.get("expected_tds"))
        if etd is not None and etd<0: out.append("model_expected_tds_invalid")
    else: out.append("market_kind_unknown")
    if not _text(model.get("version") or row.get("model_version")): out.append("model_version_missing")
    if not _bool(model.get("simulation_accounting_ok")): out.append("simulation_accounting_failed")
    state=(_text(quality.get("state")) or "").upper()
    if state not in QUALITY_STATES: out.append("data_quality_state_invalid")
    if not _bool(quality.get("critical_ok")): out.append("critical_data_quality_failed")
    if state in {"LOW","INSUFFICIENT"}: out.append("critical_data_quality_below_minimum")
    return list(dict.fromkeys(out))

def normalize_public_forecast(row, *, now_utc=None):
    now=now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None: raise PropsPublicationError("now_utc must be timezone-aware")
    now=now.astimezone(timezone.utc); market=_map(row.get("market")); model=_map(row.get("model")); quality=_map(row.get("data_quality")); prop=_text(row.get("prop_type")); kind=_kind(prop)
    reasons=_reasons(row,now); state=(_text(row.get("signal_state")) or "WATCH").upper()
    if reasons: state="NO SIGNAL"
    elif state not in SIGNAL_STATES: state="WATCH"
    line=_num(market.get("line")); fair=_num(model.get("fair_line"))
    over,under,push=_prob(model.get("over_probability")),_prob(model.get("under_probability")),_prob(model.get("push_probability"))
    if push is None and line is not None and not line.is_integer(): push=0.0
    td=_prob(model.get("td_probability")); model_p=over if kind=="OVER_UNDER" else td; market_p=_prob(market.get("no_vig_over_probability")) if kind=="OVER_UNDER" else _prob(market.get("no_vig_probability"))
    interval=_map(model.get("prediction_interval")); lo,hi=_num(interval.get("low")),_num(interval.get("high"))
    if lo is not None and hi is not None and lo>hi:
        reasons.append("prediction_interval_invalid"); state="NO SIGNAL"
    return {
        "contract_version":PUBLIC_CONTRACT_VERSION,"research_label":RESEARCH_LABEL,"forecast_id":_text(row.get("forecast_id")) or _forecast_id(row),
        "player_id":_text(row.get("player_id")),"player":_text(row.get("player")),"position":(_text(row.get("position")) or "").upper() or None,"team":_text(row.get("team")),"opponent":_text(row.get("opponent")),"game_id":_text(row.get("game_id")),"prop_type":prop,"market_kind":kind,
        "forecast_timestamp_utc":_iso(row.get("forecast_timestamp_utc")),"data_horizon_utc":_iso(row.get("data_horizon_utc")),"kickoff_utc":_iso(row.get("kickoff_utc")),"signal_state":state,"unavailable_reasons":list(dict.fromkeys(reasons)),
        "market":{"source":_text(market.get("source")),"sportsbook":_text(market.get("sportsbook")),"captured_utc":_iso(market.get("captured_utc")),"line":line,"consensus_line":_num(market.get("consensus_line")),"underlying_count_line":_num(market.get("underlying_count_line")),"line_range":_num(market.get("line_range")),"line_stddev":_num(market.get("line_stddev")),"over_price_american":_num(market.get("over_price_american")),"under_price_american":_num(market.get("under_price_american")),"td_price_american":_num(market.get("td_price_american")),"raw_implied_over_probability":_prob(market.get("raw_implied_over_probability")),"raw_implied_under_probability":_prob(market.get("raw_implied_under_probability")),"raw_implied_probability":_prob(market.get("raw_implied_probability")),"no_vig_over_probability":_prob(market.get("no_vig_over_probability")),"no_vig_under_probability":_prob(market.get("no_vig_under_probability")),"no_vig_probability":_prob(market.get("no_vig_probability"))},
        "model":{"version":_text(model.get("version") or row.get("model_version")),"mean":_num(model.get("mean")),"median":_num(model.get("median")),"fair_line":fair,"line_difference":None if fair is None or line is None else fair-line,"standard_deviation":_num(model.get("standard_deviation")),"over_probability":over,"under_probability":under,"push_probability":push,"td_probability":td,"probability_1_plus_td":(_prob(model.get("probability_1_plus_td")) if _prob(model.get("probability_1_plus_td")) is not None else td),"probability_2_plus_td":_prob(model.get("probability_2_plus_td")),"td_count_distribution":_copy(_map(model.get("td_count_distribution"))),"expected_tds":_num(model.get("expected_tds")),"fair_odds_american":(_num(model.get("fair_odds_american")) or american_odds_from_probability(model_p)),"fair_over_odds_american":_num(model.get("fair_over_odds_american")) or american_odds_from_probability(over),"fair_under_odds_american":_num(model.get("fair_under_odds_american")) or american_odds_from_probability(under),"fair_td_odds_american":_num(model.get("fair_td_odds_american")) or american_odds_from_probability(td),"market_no_vig_probability":market_p,"probability_edge":None if model_p is None or market_p is None else model_p-market_p,"prediction_interval":{"low":lo,"high":hi,"coverage":_prob(interval.get("coverage"))},"simulation_count":int(_num(model.get("simulation_count")) or 0),"simulation_accounting_ok":_bool(model.get("simulation_accounting_ok"))},
        "data_quality":{"state":(_text(quality.get("state")) or "").upper() or None,"critical_ok":_bool(quality.get("critical_ok")),"confidence":_text(quality.get("confidence")),"notes":_text(quality.get("notes"))},"drivers":_drivers(row.get("drivers")),"provenance":_copy(_map(row.get("provenance"))),
    }

def build_public_props(artifact, *, now_utc=None):
    now=now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None: raise PropsPublicationError("now_utc must be timezone-aware")
    now=now.astimezone(timezone.utc)
    if isinstance(artifact,Mapping):
        if artifact.get("contract_version")!=UPSTREAM_CONTRACT_VERSION: raise PropsPublicationError(f"unsupported upstream Props contract: {artifact.get('contract_version')!r}; expected {UPSTREAM_CONTRACT_VERSION!r}")
        if _dt(artifact.get("generated_utc")) is None: raise PropsPublicationError("upstream Props artifact requires timezone-aware generated_utc")
        if not isinstance(artifact.get("forecasts"),list): raise PropsPublicationError("upstream artifact must contain a forecasts list")
        rows=artifact["forecasts"]; upstream=artifact["contract_version"]
    else: rows=list(artifact); upstream=None
    forecasts=[normalize_public_forecast(r,now_utc=now) for r in rows if isinstance(r,Mapping)]
    return {"contract_version":PUBLIC_CONTRACT_VERSION,"upstream_contract_version":upstream,"research_label":RESEARCH_LABEL,"generated_utc":now.isoformat(),"scope":"OFFENSIVE_PROPS_ONLY","profitability_claim":False,"market_superiority_claim":False,"calibration_claim":False,"summary":{"total":len(forecasts),"model_edge":sum(x["signal_state"]=="MODEL EDGE" for x in forecasts),"watch":sum(x["signal_state"]=="WATCH" for x in forecasts),"no_signal":sum(x["signal_state"]=="NO SIGNAL" for x in forecasts)},"forecasts":forecasts}

def make_forecast_receipt(row, *, recorded_utc=None):
    recorded=recorded_utc or datetime.now(timezone.utc)
    if recorded.tzinfo is None: raise PropsPublicationError("recorded_utc must be timezone-aware for prospective history")
    recorded=recorded.astimezone(timezone.utc); kickoff=_dt(row.get("kickoff_utc")); forecast=_dt(row.get("forecast_timestamp_utc")); market_at=_dt(_map(row.get("market")).get("captured_utc")); signal=(_text(row.get("signal_state")) or "").upper()
    if kickoff is None or forecast is None: raise PropsPublicationError("prospective receipt requires valid forecast and kickoff timestamps")
    if market_at is None and signal!="NO SIGNAL": raise PropsPublicationError("normal prospective receipt requires a valid market timestamp")
    if forecast>=kickoff or (market_at is not None and market_at>=kickoff) or recorded>=kickoff: raise PropsPublicationError("refusing to create a retrospective Props forecast receipt at/after kickoff")
    original=_copy(dict(row)); fid=_text(row.get("forecast_id")) or _forecast_id(row); original["forecast_id"]=fid
    return {"history_contract_version":HISTORY_CONTRACT_VERSION,"event_type":"FORECAST_ORIGINAL","forecast_id":fid,"recorded_utc":recorded.isoformat(),"original_sha256":_sha(original),"original_forecast":original}

def make_closing_event(forecast_id, *, captured_utc, source, line, over_price_american=None, under_price_american=None, td_price_american=None):
    captured=_dt(captured_utc)
    if not forecast_id or captured is None: raise PropsPublicationError("closing event requires forecast_id and timezone-aware captured_utc")
    e={"history_contract_version":HISTORY_CONTRACT_VERSION,"event_type":"MARKET_CLOSE","forecast_id":str(forecast_id),"captured_utc":captured.isoformat(),"source":_text(source),"line":_num(line),"over_price_american":_num(over_price_american),"under_price_american":_num(under_price_american),"td_price_american":_num(td_price_american)}; e["event_id"]="close_"+_sha(e)[:24]; return e

def grade_forecast_receipt(receipt, *, actual_result, graded_utc):
    if receipt.get("event_type")!="FORECAST_ORIGINAL" or not isinstance(receipt.get("original_forecast"),Mapping): raise PropsPublicationError("grading requires an immutable FORECAST_ORIGINAL receipt")
    graded,actual=_dt(graded_utc),_num(actual_result); original=receipt["original_forecast"]; kickoff=_dt(original.get("kickoff_utc"))
    if graded is None or actual is None: raise PropsPublicationError("grading requires finite actual_result and timezone-aware graded_utc")
    if kickoff is None or graded<=kickoff: raise PropsPublicationError("grading timestamp must be after the original forecast kickoff")
    prop=_text(original.get("prop_type")); market=_map(original.get("market")); model=_map(original.get("model"))
    if _kind(prop)=="OVER_UNDER":
        line=_num(market.get("line"))
        if line is None: raise PropsPublicationError("cannot grade line market without original market line")
        outcome="OVER" if actual>line else "UNDER" if actual<line else "PUSH"; over,under=_prob(model.get("over_probability")),_prob(model.get("under_probability")); side=None if over is None or under is None else "OVER" if over>under else "UNDER" if under>over else None; result="PUSH" if outcome=="PUSH" else None if side is None else "WIN" if side==outcome else "LOSS"
    elif _kind(prop)=="BINARY_TD":
        outcome="TD" if actual>=1 else "NO_TD"; p=_prob(model.get("td_probability")); side=None if p is None else "TD" if p>=.5 else "NO_TD"; result=None if side is None else "WIN" if side==outcome else "LOSS"
    else: raise PropsPublicationError("cannot grade unsupported market")
    e={"history_contract_version":HISTORY_CONTRACT_VERSION,"event_type":"GRADE","forecast_id":receipt.get("forecast_id"),"graded_utc":graded.isoformat(),"actual_result":actual,"market_outcome":outcome,"model_side":side,"grading_result":result,"original_sha256":receipt.get("original_sha256")}; e["event_id"]="grade_"+_sha(e)[:24]; return e

def read_jsonl(path:Path):
    if not path.exists(): return []
    out=[]
    for i,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError as exc: raise PropsPublicationError(f"invalid JSONL at {path}:{i}") from exc
        if not isinstance(row,dict): raise PropsPublicationError(f"history JSONL row must be an object: {path}:{i}")
        out.append(row)
    return out

def append_jsonl_immutable(path:Path, events:Iterable[Mapping[str,Any]], *, identity_key:str):
    existing=read_jsonl(path); by={str(r.get(identity_key)):r for r in existing if r.get(identity_key)}; additions=[]
    for event in events:
        c=_copy(dict(event)); ident=_text(c.get(identity_key))
        if not ident: raise PropsPublicationError(f"history event missing {identity_key}")
        if ident in by:
            if _canon(by[ident])!=_canon(c): raise PropsPublicationError(f"immutable history collision for {identity_key}={ident}")
            continue
        by[ident]=c; additions.append(c)
    if additions:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("a",encoding="utf-8") as h:
            for e in additions: h.write(_canon(e)+"\n")
    return len(additions)

def build_history_view(receipts, closing_events=(), grade_events=()):
    closes={}; grades={}
    for e in closing_events:
        fid=_text(e.get("forecast_id"))
        if fid and (fid not in closes or (_iso(e.get("captured_utc")) or "")>=(_iso(closes[fid].get("captured_utc")) or "")): closes[fid]=e
    for e in grade_events:
        fid=_text(e.get("forecast_id"));
        if fid: grades[fid]=e
    return [{"forecast_id":r.get("forecast_id"),"recorded_utc":r.get("recorded_utc"),"original_sha256":r.get("original_sha256"),"original_forecast":deepcopy(r.get("original_forecast")),"closing_market":deepcopy(closes.get(str(r.get("forecast_id")))),"grade":deepcopy(grades.get(str(r.get("forecast_id"))))} for r in receipts if r.get("event_type")=="FORECAST_ORIGINAL" and r.get("forecast_id")]

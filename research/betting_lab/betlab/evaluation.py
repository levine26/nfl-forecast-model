"""Outcome-blind, point-in-time backtesting and calibration reporting.

IMPORTANT: Only externally timestamp-qualified quotes are eligible. No inference of
historical odds from market spread numbers. Closing prices are never predictive inputs.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import log, isfinite, sqrt
from random import Random
from statistics import mean
from .pricing import BookQuote, quote_time, cash_profit, expected_net, implied_probability
from .settlement import GameResult, grade


@dataclass(frozen=True)
class Prediction:
    quote: BookQuote
    decision_utc: str
    prediction_utc: str
    feature_cutoff_utc: str
    p_win: float
    p_push: float
    result: GameResult  # grading-time-only; never presented to predictor
    season: int
    week: int
    stake: float = 1.
    closing_quote: BookQuote | None = None
    model_version: str = ''

    def validate(self):
        self.quote.validate(self.decision_utc, max_quote_age_seconds=7200)
        if not self.model_version:
            raise ValueError('missing fixed model identity')
        feature, prediction, decision, kickoff = map(quote_time,(self.feature_cutoff_utc,self.prediction_utc,self.decision_utc,self.quote.kickoff_utc))
        if feature > prediction or prediction > decision or feature >= kickoff:
            raise ValueError('point-in-time leakage / chronology violation')
        if self.season < 2000 or not 1<=self.week<=30 or not isfinite(self.stake) or self.stake<0:
            raise ValueError('invalid season/week/stake')
        if not all(isfinite(x) for x in (self.p_win,self.p_push)) or not 0<=self.p_win<=1 or not 0<=self.p_push<=1 or self.p_win+self.p_push>1+1e-8:
            raise ValueError('invalid probability vector')
        if self.closing_quote:
            c=self.closing_quote
            if (c.game_id,c.market,c.side,c.player_id,c.stat)!=(self.quote.game_id,self.quote.market,self.quote.side,self.quote.player_id,self.quote.stat):
                raise ValueError('closing market must match chosen selection')
            if not (decision < quote_time(c.observed_utc) < kickoff):
                raise ValueError('closing quote must strictly follow decision and precede kickoff')
            if self.quote.market == 'player_prop' and self.quote.line != c.line:
                # For CLV, differing thresholds cannot be converted into price-only movement.
                pass


def closing_line_value(record:Prediction)->float|None:
    """Selection-favorable line movement; moneylines return favorable raw implied-prob delta.

    Never mix points and probability into the same aggregate.
    No made-up price-based CLV for unequal stat lines.
    """
    q,c=record.quote,record.closing_quote
    if not c: return None
    if q.market=='spread': return q.line-c.line
    if q.market=='total': return (c.line-q.line) if q.side=='over' else (q.line-c.line)
    if q.market=='moneyline': return implied_probability(c.american)-implied_probability(q.american)
    if q.market in ('player_td','player_prop') and q.line==c.line:
        return implied_probability(c.american)-implied_probability(q.american)
    return None


def grade_records(records:list[Prediction])->dict:
    if not records: raise ValueError('no eligible predictions')
    for r in records:r.validate()
    ids=[(r.quote.id,r.decision_utc) for r in records]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate bet prediction records')
    nets=[]; obs=[]; probs=[]; stats={'win':0,'loss':0,'push':0}
    clv=[]; briers=[]; logs=[]; threeclass=[]
    for r in records:
        outcome=grade(r.quote,r.result)
        stats[outcome]+=1
        nets.append(cash_profit(outcome,r.quote.american,r.stake))
        cl=closing_line_value(r)
        if cl is not None:clv.append(cl)
        three_probs={'win':r.p_win,'push':r.p_push,'loss':max(0,1-r.p_win-r.p_push)}
        threeclass.append(-log(max(1e-15,three_probs[outcome])))
        if outcome!='push':
            y=1 if outcome=='win' else 0
            conditional=r.p_win/(1-r.p_push) if r.p_push<1 else 0.5
            briers.append((conditional-y)**2)
            logs.append(-(y*log(max(conditional,1e-15))+(1-y)*log(max(1-conditional,1e-15))))
            obs.append(y);probs.append(conditional)
    totalrisk=sum(r.stake for r in records)
    return {'count':len(records),'model':sorted(set(r.model_version for r in records)),**stats,
            'net_profit':sum(nets),'roi_on_risk':sum(nets)/totalrisk if totalrisk else None,
            'brier_nonpush':mean(briers) if briers else None,
            'log_loss_nonpush':mean(logs) if logs else None,
            'three_class_log_loss':mean(threeclass),
            'clv_count':len(clv),'mean_clv_only_if_homogeneous_market':mean(clv) if clv and len(set(r.quote.market for r in records))==1 else None,
            'reliability':reliability(probs,obs)}


def reliability(probs:list[float],actuals:list[int],bins:int=5)->list[dict]:
    if len(probs)!=len(actuals) or bins<2:raise ValueError('invalid calibration arrays')
    output=[]
    for k in range(bins):
        group=[(p,a) for p,a in zip(probs,actuals) if k/bins<=p<((k+1)/bins if k+1<bins else 1.00000001)]
        output.append({'low':k/bins,'high':(k+1)/bins,'n':len(group),
                       'predicted':mean(x[0] for x in group) if group else None,
                       'observed':mean(x[1] for x in group) if group else None})
    return output


def block_bootstrap_roi(records:list[Prediction],draws:int=2000,seed:int=20261010)->dict:
    if not records or draws<100:raise ValueError('not enough data or bootstrap draws')
    # Predefine full season-week clusters; plays within one slate stay correlated.
    groups={}
    for r in records:
        r.validate()
        groups.setdefault((r.season,r.week),[]).append(r)
    blocks=list(groups.values()); rng=Random(seed)
    ratios=[]
    for _ in range(draws):
        sample=[r for _ in blocks for r in blocks[rng.randrange(len(blocks))]]
        nets=[cash_profit(grade(r.quote,r.result),r.quote.american,r.stake) for r in sample]
        total=sum(r.stake for r in sample)
        ratios.append(sum(nets)/total if total else 0.0)
    ratios.sort()
    return {'blocks':len(blocks),'bootstrap_draws':draws,
            'ci_95_roi':[ratios[int(.025*draws)],ratios[min(draws-1,int(.975*draws))]],
            'p_roi_positive':sum(x>0 for x in ratios)/draws}


def compare_fixed_splits(rows:list[dict],train_end:int,validation_season:int,holdout_season:int)->dict:
    """Freeze chronological split IDs *before* fitting or examining labels.

    The helper returns row identities only, never performs retrospective tuning.
    """
    if not train_end<validation_season<holdout_season:
        raise ValueError('train / validation / holdout chronology required')
    train=[r['id'] for r in rows if r['season']<=train_end]
    val=[r['id'] for r in rows if r['season']==validation_season]
    test=[r['id'] for r in rows if r['season']==holdout_season]
    if not train or not val or not test or len(set(train+val+test))!=len(train+val+test):
        raise ValueError('empty or duplicate split')
    return {'train':train,'validation':val,'holdout':test,
            'test_labels_must_remain_sealed_until_selection':True}
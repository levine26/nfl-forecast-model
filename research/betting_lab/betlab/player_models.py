"""Trainable, strictly prior-game player TD/yardage shadow candidates.

Public labels are NEVER joined into target features.  The first strictly
out-of-time holdout is evaluated once after validation model selection.
No injury module. No production/model promotion and no ROI claims.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, isfinite, log
from statistics import mean
from .pricing import quote_time

FEATURE_NAMES=('prior_games','targets_4','carries_4','redzone_4','endzone_targets_4',
               'snap_share_4','receiving_yards_4','rushing_yards_4', 'tds_4',
               'team_expected_tds')


@dataclass(frozen=True)
class PlayerGame:
    player_id:str
    game_id:str
    season:int
    week:int
    kickoff_utc:str
    result_published_utc:str
    targets:float
    carries:float
    redzone_touches:float
    endzone_targets:float
    snap_share:float
    receiving_yards:float
    rushing_yards:float
    touchdowns:int
    # pregame sourced only; null means no point-in-time qualified market source.
    team_expected_tds:float|None=None
    team_expected_tds_observed_utc:str|None=None

    def validate(self):
        if not self.player_id or not self.game_id or self.season<2000 or not 1<=self.week<=30:
            raise ValueError('invalid player/game identity')
        if quote_time(self.result_published_utc)<=quote_time(self.kickoff_utc):
            raise ValueError('outcome publication must follow kickoff')
        for k in ('targets','carries','redzone_touches','endzone_targets','snap_share','receiving_yards','rushing_yards'):
            if not isfinite(getattr(self,k)):raise ValueError('nonfinite '+k)
        if self.touchdowns<0 or not isinstance(self.touchdowns,int):raise ValueError('invalid TD label')
        if self.team_expected_tds is not None:
            if self.team_expected_tds<0 or not isfinite(self.team_expected_tds) or not self.team_expected_tds_observed_utc:
                raise ValueError('unqualified expected TD quote')
            if quote_time(self.team_expected_tds_observed_utc)>=quote_time(self.kickoff_utc):
                raise ValueError('future team TD market data')


def build_prior_examples(rows:list[PlayerGame],window:int=4)->list[dict]:
    """Prior-record features; *all* label/yards/usage values shift by published date.

    A week-W game CANNOT read its own rows, even if input data is sorted strangely.
    Missing history is represented explicitly by 0 plus prior_games feature.
    This is a baseline/engineering choice, not calibrated rookie prior.
    """
    if window<1:raise ValueError('window must be positive')
    if len({(r.player_id,r.game_id) for r in rows})!=len(rows):raise ValueError('duplicate player-game')
    for r in rows:r.validate()
    sorted_rows=sorted(rows,key=lambda r:(quote_time(r.kickoff_utc),r.player_id,r.game_id))
    by_player={}
    out=[]
    for r in sorted_rows:
        prior=[p for p in by_player.get(r.player_id,[]) if quote_time(p.result_published_utc)<quote_time(r.kickoff_utc)]
        recent=prior[-window:]
        feature={'prior_games':len(prior)}
        for attr,key in [('targets','targets_4'),('carries','carries_4'),('redzone_touches','redzone_4'),
                         ('endzone_targets','endzone_targets_4'),('snap_share','snap_share_4'),
                         ('receiving_yards','receiving_yards_4'),('rushing_yards','rushing_yards_4'),('touchdowns','tds_4')]:
            feature[key]=mean(getattr(p,attr) for p in recent) if recent else 0.0
        feature['team_expected_tds']=r.team_expected_tds if r.team_expected_tds is not None else float('nan')
        out.append({'player_id':r.player_id,'game_id':r.game_id,'season':r.season,'week':r.week,
                    'asof_utc':r.kickoff_utc,'max_source_published_utc':max((p.result_published_utc for p in recent),default=None),
                    'features':feature,'td_label':int(r.touchdowns>=1),
                    'receiving_yards_label':r.receiving_yards,'rushing_yards_label':r.rushing_yards})
        by_player.setdefault(r.player_id,[]).append(r)
    return out


def team_td_opportunity_probability(expected_team_tds:float,player_scoring_share:float)->float:
    """Interpretable Poisson opportunity baseline; requires future calibration."""
    if not isfinite(expected_team_tds) or not 0<=expected_team_tds<=12 or not isfinite(player_scoring_share) or not 0<=player_scoring_share<=1:
        raise ValueError('invalid TD opportunity inputs')
    return 1-exp(-expected_team_tds*player_scoring_share)


def _matrix(rows:list[dict]):
    import numpy as np
    return np.array([[r['features'][key] for key in FEATURE_NAMES] for r in rows],float)


def _brier(y,p)->float:
    import numpy as np
    return float(np.mean((y-p)**2))


def _logloss(y,p)->float:
    import numpy as np
    p=np.clip(p,1e-12,1-1e-12)
    return float(np.mean(-np.array(y)*np.log(p)-(1-np.array(y))*np.log(1-p)))


def td_chronological_experiment(rows:list[dict],train_end:int=2023,val_season:int=2024,test_season:int=2025)->dict:
    """Fit two candidates, select on validation logloss, score sealed holdout ONCE.

    Returned numbers describe only the caller-supplied records, never model accuracy
    on NFL data unless that dataset itself is verified and independently documented.
    """
    import numpy as np
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    if not train_end<val_season<test_season:raise ValueError('invalid season chronology')
    train=[r for r in rows if r['season']<=train_end]
    valid=[r for r in rows if r['season']==val_season]
    test=[r for r in rows if r['season']==test_season]
    if min(len(train),len(valid),len(test))<20:raise ValueError('minimum 20 player-games per partition required')
    if len({(r['player_id'],r['game_id']) for r in rows})!=len(rows):raise ValueError('duplicate examples')
    Xtr,Xv,Xte=map(_matrix,(train,valid,test))
    ytr,yv,yte=[np.array([r['td_label'] for r in part],int) for part in (train,valid,test)]
    if len(set(ytr))<2:raise ValueError('train has only one TD class')
    models={
      'logistic':make_pipeline(SimpleImputer(strategy='constant',fill_value=0),StandardScaler(),LogisticRegression(C=1,max_iter=1000)),
      'hist_gradient_boosting':HistGradientBoostingClassifier(max_iter=60,max_leaf_nodes=8,l2_regularization=1.0,min_samples_leaf=10,random_state=20261010),
    }
    scores={}
    for k,m in models.items():
        m.fit(Xtr,ytr)
        pv=m.predict_proba(Xv)[:,1]
        scores[k]={'val_logloss':_logloss(yv,pv),'val_brier':_brier(yv,pv)}
    selected=min(scores,key=lambda k:(scores[k]['val_logloss'],k))
    selected_model=models[selected]  # no refit on holdout or validation outcomes
    ph=selected_model.predict_proba(Xte)[:,1]
    base=float(np.mean(ytr));constant=np.full(len(yte),base)
    return {'status':'EXPERIMENTAL_NOT_PROVEN','train_n':len(train),'validation_n':len(valid),'holdout_n':len(test),
            'selected_by_validation':selected,'validation':scores,
            'heldout':{'td_base_rate':float(np.mean(yte)),'model_brier':_brier(yte,ph),'model_logloss':_logloss(yte,ph),
                       'train_base_rate':base,'base_brier':_brier(yte,constant),'base_logloss':_logloss(yte,constant)},
            'not_an_nfl_claim_without_verified_source_data':True}


def yards_chronological_experiment(rows:list[dict],target:str='receiving_yards_label',train_end:int=2023,val_season:int=2024,test_season:int=2025)->dict:
    import numpy as np
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.dummy import DummyRegressor
    if target not in ('receiving_yards_label','rushing_yards_label'):raise ValueError('unsupported yardage target')
    if not train_end<val_season<test_season:raise ValueError('invalid season chronology')
    parts=[[r for r in rows if (r['season']<=train_end if i==0 else r['season']==year)] for i,year in enumerate((train_end,val_season,test_season))]
    if min(map(len,parts))<20:raise ValueError('minimum 20 observations in each partition')
    Xtr,Xv,Xte=map(_matrix,parts)
    ytr,yv,yte=[np.array([r[target] for r in part],float) for part in parts]
    models={'constant':DummyRegressor(strategy='mean'),
            'hgb':make_pipeline(SimpleImputer(strategy='constant',fill_value=0),HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=8,min_samples_leaf=10,random_state=20261010))}
    val={}
    for name,m in models.items():
        m.fit(Xtr,ytr)
        pred=m.predict(Xv)
        val[name]=float(np.mean(abs(yv-pred)))
    selected=min(val,key=lambda k:(val[k],k))
    preds=models[selected].predict(Xte)
    return {'status':'EXPERIMENTAL_NOT_PROVEN','target':target,'selected':selected,'validation_mae':val,
            'holdout_mae':float(np.mean(abs(yte-preds))),'holdout_constant_mae':float(np.mean(abs(yte-ytr.mean()))),
            'holdout_n':len(yte),'not_an_nfl_claim_without_verified_source_data':True}
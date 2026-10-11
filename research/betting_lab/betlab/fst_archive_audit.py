"""Re-score archived chronology-clean F-ST ML OOF records (2022–2025).

Do not confuse retrospective reproduced pregame predictions with immutable live
locks. Never use these late-horizon market probabilities as wager prices or
inference about alternate spreads, totals, touchdowns, or stakes.
"""
from __future__ import annotations

import csv
import json
from hashlib import sha256
from math import isfinite, log
from pathlib import Path

VALID_SEASONS = (2022, 2023, 2024, 2025)
REQUIRED = {'game_id','season','week','home_team','away_team','home_win','fst_prob','market_prob'}
EXPECTED_COUNTS = {2022:271,2023:272,2024:272,2025:272}


def _read(path: Path):
    raw=path.read_bytes()
    data=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    if not data or not REQUIRED.issubset(data[0]):
        raise ValueError('Missing required F-ST archive columns')
    return raw, data


def _score(rows):
    n=len(rows)
    def mean(fn):return round(sum(fn(r) for r in rows)/n, 8) if n else None
    def scored(key):
        return {
            'correct':sum(1 for x in rows if (x[key] >= .5)==bool(x['home_win'])),
            'accuracy':mean(lambda x: int((x[key] >= .5)==bool(x['home_win']))),
            'brier':mean(lambda x:(x[key]-x['home_win'])**2),
            'log_loss':mean(lambda x:-(x['home_win']*log(x[key])+(1-x['home_win'])*log(1-x[key]))),
        }
    return {'games':n,'FST':scored('fst_prob'),'MARKET':scored('market_prob')}


def audit_fst_archives(development: Path, diagnostic: Path, *, enforce_expected_counts: bool=True):
    devbytes,dev=_read(development)
    diagbytes,diag=_read(diagnostic)
    acc=[]; seen=set()
    for source,rows in [('2022_2024_development',dev),('2025_nonpristine_diagnostic',diag)]:
        for row in rows:
            gid=row['game_id']; year=int(row['season']); week=int(row['week'])
            if gid in seen:raise ValueError('duplicate game id: '+gid)
            seen.add(gid)
            if year not in VALID_SEASONS or (source.startswith('2025') != (year==2025)):
                raise ValueError('misplaced archive season')
            if not gid.startswith(str(year)+'_') or not 1<=week<=18:
                raise ValueError('invalid game/week identity')
            if row['home_win'] not in ('0','1'):raise ValueError('invalid binary outcome')
            parsed={'game_id':gid,'year':year,'home_win':int(row['home_win'])}
            for inp,out in [('fst_prob','fst_prob'),('market_prob','market_prob')]:
                p=float(row[inp])
                if not isfinite(p) or not 0<p<1:raise ValueError('invalid '+inp)
                parsed[out]=p
            acc.append(parsed)
    counts={y:sum(x['year']==y for x in acc) for y in VALID_SEASONS}
    if enforce_expected_counts and counts!=EXPECTED_COUNTS:
        raise ValueError('incomplete frozen coverage '+str(counts))
    return {'identity':'B08C_FST_ARCHIVE_MONEYLINE_REPLAY_V1',
       'method':'chronology_clean_archived_FST_reproduction_NOT_prospective_locks',
       'outcome_boundary':'2022_2024_development_and_2025_nonpristine_diagnostic',
       'qualifier':'historical_development_evidence_NOT_independent_holdout',
       'moneyline_only':True,'spread_total_prop_ineligible':True,
       'market_quote_horizon':'historical_late_closing_horizon_opaque',
       'real_world_betting_roi':None,
       'tie_label_caveat':'Binary home_win=0 can include tied games. This audit reproduces accepted original labels; it is not a moneyline bet-settlement study.',
       'source_files':[{'name':development.name,'sha256':sha256(devbytes).hexdigest()},
                       {'name':diagnostic.name,'sha256':sha256(diagbytes).hexdigest()}],
       'coverage':counts,
       'overall':_score(acc),
       'by_season':{str(y):_score([x for x in acc if x['year']==y]) for y in VALID_SEASONS},
       'methodology_notice':'Uses accepted pre-existing out-of-fold predictions; it does not retrain, tune thresholds, alter frozen official forecasts, or establish sportsbook-executable odds.'}


def save_report(report:dict,path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(report,f,sort_keys=True,indent=2)
        f.write('\n')
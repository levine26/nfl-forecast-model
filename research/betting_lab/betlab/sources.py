"""Book quote provenance and immutable manual/provider capture envelopes.

A provider's *fetch time* is not a bookmaker's quote-update time. Untimestamped
StartWho/ Alexandria sportsbook subquotes are RESEARCH_CONTEXT_ONLY, never tradable.
No external requests, injury sources, wagering or scheduled jobs.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from .pricing import BookQuote,quote_time

@dataclass(frozen=True)
class Capture:
    provider:str
    capability:str
    filters:dict
    received_utc:str
    source_updated_utc:str|None
    payload:dict
    contractual_access:str='UNVERIFIED'

    def validate(self):
        if not self.provider or not self.capability:
            raise ValueError('capture needs source identity')
        received=quote_time(self.received_utc)
        if self.source_updated_utc and quote_time(self.source_updated_utc)>received:
            raise ValueError('provider update timestamp later than capture')
        if not isinstance(self.payload,dict):raise ValueError('raw capture must be object')

    def receipt(self)->dict:
        self.validate()
        canonical=json.dumps(self.payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        raw_sha=sha256(canonical).hexdigest()
        identity=json.dumps({'provider':self.provider,'capability':self.capability,
                             'filters':self.filters,'received_utc':self.received_utc,
                             'raw_sha256':raw_sha},sort_keys=True,separators=(',',':')).encode('utf-8')
        return {'provider':self.provider,'capability':self.capability,'filters':self.filters,
                'received_utc':self.received_utc,'source_updated_utc':self.source_updated_utc,
                'raw_sha256':raw_sha,'snapshot_id':sha256(identity).hexdigest(),
                'byte_count':len(canonical), 'contractual_access':self.contractual_access,
                'predictive_eligibility':'UNQUALIFIED_UNTIL_PER_SOURCE_AUDIT'}


def archive_capture(capture:Capture,directory:Path)->dict:
    """Create-only receipt and raw JSON. Hash by canonical content; no overwrite.

    Files only in caller-provided local folder. Do NOT commit licensed source data.
    """
    rec=capture.receipt()
    directory.mkdir(parents=True,exist_ok=True)
    stem=rec['snapshot_id']
    payload=directory/(stem+'.json')
    receipt_path=directory/(stem+'.receipt.json')
    raw=json.dumps(capture.payload,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
    meta=json.dumps(rec,indent=2,sort_keys=True)+'\n'
    if payload.exists() or receipt_path.exists():
        raise FileExistsError('immutable snapshot already exists or incomplete previous write')
    created=[]
    try:
        with payload.open('x',encoding='utf-8') as f:
            created.append(payload)
            f.write(raw)
        with receipt_path.open('x',encoding='utf-8') as f:
            created.append(receipt_path)
            f.write(meta)
    except BaseException:
        # Only clean up paths created by THIS call, never competing-writer files.
        for p in reversed(created):p.unlink(missing_ok=True)
        raise
    return {'payload_path':str(payload),'receipt_path':str(receipt_path),**rec}


def startwho_prop_inventory(payload:dict,capture_time_utc:str)->list[dict]:
    """Normalize *unqualified* props; do not turn observed_at_ms into book quote time."""
    quote_time(capture_time_utc)
    data=payload
    if 'data' in payload and 'alexandria' in payload['data']:
        arr=payload['data']['alexandria']
        if len(arr)!=1 or arr[0].get('provider')!='startwho-com':
            raise ValueError('unmatched provider envelope')
        data=arr[0].get('data') or {}
    if not isinstance(data.get('players'),list):
        raise ValueError('missing StartWho players')
    out=[]
    for player in data['players']:
        for prop in player.get('props',[]):
            for book in prop.get('bookmakers',[]):
                out.append({'player_id':player['player_id'],'team':player['team'],
                  'opponent':player['opponent'],'game_kickoff_at':player.get('game_kickoff_at'),
                  'prop_type':prop['prop_type'],'book':book['sportsbook'],'line':book.get('line'),
                  'over_odds':book.get('over_odds'),'under_odds':book.get('under_odds'),
                  'captured_utc':capture_time_utc,'quote_observed_utc':book.get('quote_observed_utc'),
                  'eligibility':'PIT_ELIGIBLE_ONLY_WITH_QUOTE_TIMESTAMP' if book.get('quote_observed_utc') else 'RESEARCH_CONTEXT_ONLY',
                  'reason':None if book.get('quote_observed_utc') else 'NO_PER_BOOK_QUOTE_TIMESTAMP'})
    return out


def qualified_manual_quote(raw:dict,decision_utc:str,max_age_seconds:int=1800)->BookQuote:
    """Caller must provide explicit book/source/time and a verified kickoff."""
    allowed={k for k in BookQuote.__dataclass_fields__}
    extra=set(raw)-allowed
    if extra:raise ValueError('unrecognized quote fields: '+','.join(sorted(extra)))
    q=BookQuote(**raw)
    if q.source.lower().startswith(('synthetic','alexandria-provider-observed-time')):
        raise ValueError('not a direct operator quote')
    q.validate(decision_utc,max_age_seconds)
    return q
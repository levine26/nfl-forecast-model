"""Append-only implementation receipts, to prevent future chats losing state."""
import json
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone

REQUIRED=('id','date','status','scope','files','proof','next')

def verify_ledger(path:Path)->dict:
    rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    seen=set()
    for r in rows:
        if not all(k in r for k in REQUIRED):raise ValueError('incomplete implementation receipt')
        if r['id'] in seen:raise ValueError('duplicate implementation ID')
        seen.add(r['id'])
        if not r['files'] or not r['proof']:raise ValueError('unverifiable record')
    return {'records':len(rows),'ids':sorted(seen),'sha256':sha256(path.read_bytes()).hexdigest()}

def append_receipt(path:Path,entry:dict)->dict:
    if not all(k in entry for k in REQUIRED):raise ValueError('incomplete receipt')
    if path.exists():
        verify_ledger(path)
        ids={json.loads(x)['id'] for x in path.read_text().splitlines() if x.strip()}
        if entry['id'] in ids:raise ValueError('receipt is immutable; duplicate ID')
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(entry,sort_keys=True,ensure_ascii=False)+'\n')
    return verify_ledger(path)
# Phase 2 — Data Gaps, Point-in-Time Source Policy, and Paid-Data Decision

**Status:** research design  
**Production dependency authorization:** none

## 1. Current $0 foundation

The program can implement the initial three challengers without a new paid dependency using:

- nflverse schedules/results;
- nflverse play-by-play;
- lagged EPA/success/process fields;
- sequential Elo / internal ratings;
- deterministic schedule/home/rest data;
- historical schedule market fields as a closing/late benchmark;
- existing repository PIT governance.

Therefore a paid source is **not necessary to begin Phase 3**.

---

## 2. Market data gap

### Historical

nflverse schedule spread/total/moneyline fields are usable as a historical closing/late benchmark but do not prove:

- bookmaker identity;
- exact opening time;
- T-120 state;
- exact capture latency.

Challenger C historical work must be labeled accordingly.

### Prospective

The existing free-tier multi-book collector was most recently observed in Phase 1 with an HTTP 401 state and no usable current snapshot ledger.

**Required action before Phase 5 / same-horizon research:**

- repair authorization/configuration;
- preserve request time and per-book update time;
- fail closed on stale/sparse coverage;
- keep free-tier quota reserve.

No historical paid odds API is authorized.

---

## 3. QB / starter-state gap

Final schedule starter IDs cannot automatically be treated as what was known at a simulated pregame horizon.

Existing useful pieces:

- 2025+ timestamped depth-chart data;
- 2026 prospective expected-lineup / injury snapshots;
- prior-completed-game quarterback performance;
- stable identifiers.

Missing:

- one harmonized multi-season 2022–2025 starter-as-of history at a fixed decision horizon.

**Policy:** no core historical QB overlay until that gap is resolved. Prospective QB shadow features remain possible.

---

## 4. Injury / availability gap

The 2025 composite qualifies practice state known before T-120 for 2025 only.

It does not create a valid 2022–2024 bridge.

**Policy:**

- use 2025 for prespecified sensitivity only;
- never encode absent historical rows as healthy;
- do not use hindsight inactive status or realized snaps;
- do not make player availability a mandatory initial Challenger A/B input.

---

## 5. Weather / venue gap

Prospective NWS/Open-Meteo research paths exist, but exact game-venue receipts remain incomplete in the current research infrastructure.

Historical realized temperature/wind is not an acceptable substitute for what was forecast pregame.

**Policy:** weather is blocked from initial challenger selection. Restore exact venue mapping and forecast-as-of capture first.

---

## 6. Advanced football-data availability

Free/open lagged sources include, subject to their own publication timing:

- nflverse NGS weekly;
- FTN charting via nflverse;
- PFR advanced;
- rosters;
- depth charts;
- public participation data.

Potential issues:

- threshold-based missingness;
- publication after a game rather than before it;
- participation datasets released too late for some historical same-season uses;
- identity changes.

**Policy:** Challenger A/B start from stable PBP-derived features. Advanced sources are optional ablations, not prerequisites.

---

## 7. Commercial sources considered

Examples already cataloged in repository governance include:

- Sports Info Solutions;
- PFF commercial APIs/data;
- SumerSports subscription products;
- Sportradar;
- SportsDataIO.

Potential unique value includes:

- richer line-play / pressure / blocking;
- route and coverage charting;
- better historical injury/availability revision history;
- stable participation / lineup feeds.

However, Phase 2 has not established that any of those sources would provide a **material score-accuracy improvement that cannot be tested first with free data**.

---

# Paid-data escalation decision

**No paid-data escalation is warranted in Phase 2.**

Reason:

1. the strongest Phase 1 failures can be attacked with free/public data;
2. dynamic team strength, drive decomposition and market residualization do not require a new subscription;
3. historical PIT player/weather gaps are real, but the program does not yet know whether solving them improves score accuracy enough to justify cost;
4. buying data before a free challenger baseline exists would confound data value with architecture value.

## Reopen condition

Escalate a paid source only if Phase 3/4 shows:

- a specific residual failure remains;
- a specific paid field uniquely addresses it;
- no reasonable free proxy/source exists;
- an offline or limited trial can test incremental value;
- expected improvement is large enough to matter relative to uncertainty and operational cost.

Any future memo must name the source, fields, price, test plan and no-cost alternatives before purchase.

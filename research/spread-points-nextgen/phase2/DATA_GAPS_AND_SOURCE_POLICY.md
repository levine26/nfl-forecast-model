# Phase 2 — Data Gaps, Point-in-Time Source Policy, and Paid-Data Decision

**Status:** research design  
**Production dependency authorization:** none


## Canonical Phase 3 source-feasibility matrix

This table is the binding feasibility summary for the proposed feature families. "Research-ready" means constructible with the stated chronology; it does not mean production-authorized or empirically useful.

| Feature family | Source | Stable key | Pregame / publication rule | Lag | Missingness | Coverage / readiness | Initial status |
|---|---|---|---|---|---|---|---|
| opponent-adjusted EPA / success | nflverse PBP | game_id + team/opponent | only completed games before forecast; opponent adjustment fit inside training fold | lagged prior-game summaries; A0 weighting controlled by bounded spec | explicit; no future fill | multi-season, $0 | **A0 READY** |
| dynamic offense/defense state | derived from prior schedule/PBP | team + game order | state updated only after prior final game | sequential | initialize from league prior | multi-season | **A0 READY** |
| drives / possession counts | nflverse PBP drive structure | game_id + drive + posteam | prior completed games only; drive extraction contract frozen before outputs | lagged prior-game state; exact transform frozen in B0 implementation contract | ambiguous drives fail closed / logged | multi-season, implementation contract required | **B0 READY WITH EXTRACTION TESTS** |
| TD/FG/empty drive rates | nflverse PBP | game_id + drive + posteam | prior completed drives only | lagged / training-fold regularized | unknown outcome rows excluded with counts | multi-season | **B0 READY** |
| red-zone rates | nflverse PBP | game_id + drive/play | prior completed games only | would be lagged | explicit | multi-season | **B0 READY; SHRINKAGE-SMOOTHED** |
| explosive-play rates | nflverse PBP | game_id + team | prior completed games only; definition fixed before run | lagged prior-game state | explicit | multi-season | **B0 READY / CONTROLLED INPUT** |
| sacks | nflverse PBP | game_id + team | prior completed games only | lagged | explicit | multi-season | **DEFERRED AS STANDALONE B0 FEATURE** |
| turnovers / takeaways | nflverse PBP | game_id + team | prior completed games only | lagged / regularized | explicit | multi-season | **CONTROLLED B INPUT** |
| special teams / defensive scores | nflverse PBP | game_id + scoring event | prior completed games only | training-only empirical tail | explicit | multi-season but sparse | **TAIL ONLY / NO TEAM-SPECIFIC CLASSIFIER** |
| static stadium / roof | nflverse schedule + qualified venue map | game_id / venue_id | deterministic venue metadata known pregame | none | unknown venue stays unknown | partial venue-quality issue | **DEFERRED FROM A0/B0** |
| rest | nflverse schedule | game_id + team | deterministic from schedule known before game | none | fail closed if date missing | strong | **A0/B0/C0 READY** |
| QB starter / replacement | timestamped expected-lineup/depth sources when qualified | game_id + GSIS player id | starter identity must be preserved at/before simulated horizon | prior performance only | missing = unknown, never stable starter | unified 2022–2025 fixed-horizon history absent | **BLOCKED/CONDITIONAL** |
| injuries | qualified practice/injury snapshots | game_id + GSIS player id | report/snapshot timestamp <= horizon | none beyond source timing | missing != healthy | qualified 2025 slice; 2026 prospective | **BLOCKED AS CORE MULTI-SEASON FEATURE** |
| OL/personnel continuity | depth/roster/availability + stable IDs | game_id + player id + role | as-of lineup/role must be proven | prior state only | missing role/state explicit | incomplete uniform history | **BLOCKED/CONDITIONAL** |
| advanced player/charting | nflverse NGS / FTN / PFR advanced | player/team IDs | source publication must precede next forecast horizon | prior completed game/week | source-specific | varying, often 2022+ | **NOT INITIAL; LATER PREREGISTERED ABLATION ONLY** |
| weather forecast | NWS / qualified Open-Meteo archived runs + venue resolver | game_id + venue + issue time | forecast issue/update available <= horizon; never realized weather | none | missing forecast = unavailable | venue receipts incomplete | **BLOCKED** |
| historical market | nflverse schedule lines | game_id | exact historical horizon opaque; use only as closing/late family | none | no imputation | strong paired historical coverage | **C0 READY, CLOSING/LATE LABEL ONLY** |
| prospective T-120 market | timestamped LevLine market collector | game_id + book + captured_at | latest valid receipt <= kickoff-120 with staleness rules | none | failed collector != no move | last audited collector HTTP 401 / empty usable ledger | **BLOCKED FOR T-120 RESEARCH UNTIL REPAIRED** |

### Research/production distinction

A source being "READY" in this table authorizes only the bounded Phase 3 research use described by the preregistration. It does not authorize production, a new public forecast surface, or an expanded feature family.

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


---

## 8. Canonical Phase 3 feature/source feasibility matrix

This table is the authoritative source/PIT gate for the initial implementation. A Phase 3 feature may not be added merely because a dataframe column exists.

| Feature family | Source | Stable identity key | Pregame availability rule | Publication-time / lag rule | Missingness | Historical coverage used | Status |
|---|---|---|---|---|---|---|---|
| game identity / schedule / home-away | nflverse games | `game_id`, team abbreviations mapped by repository crosswalk | schedule row known before game; final scores excluded from features | static schedule metadata only | fail if game/team identity unresolved | 2016–2024 dev; 2025 holdout later | **AUTHORIZED A0/B0/C0** |
| rest differential | nflverse schedule dates | `game_id`, team | deterministically calculable from prior scheduled/completed games | prior schedule only | explicit unknown only if schedule history missing | 2016–2024 | **AUTHORIZED A0/B0/C0** |
| prior PBP EPA/success | nflverse PBP | `game_id`, `posteam`/`defteam` | only completed games strictly before forecast game | fixed 8-team-game EW state; no current-game plays | no future fill; team-state minimum support enforced | 2016–2024 | **AUTHORIZED A0/B0** |
| opponent-adjusted offense/defense state | derived inside training fold from prior PBP | team + season/week | state for game built from prior games only | opponent adjustment fitted/recomputed inside prior-time fold; never full-sample normalization | fail/league-prior shrinkage per frozen A0 spec | 2016–2024 | **AUTHORIZED A0; OOF output to B0/C0** |
| drives / possessions | nflverse PBP drive identifiers/outcome reconstruction | `game_id`, possession team, drive index | only drives from completed prior games | fixed 8-team-game lagged state | malformed drives excluded with count reported | 2016–2024 where reconstruction passes | **AUTHORIZED B0** |
| plays per drive | derived prior PBP | team/game | prior games only | fixed 8-team-game lagged state | explicit support threshold | 2016–2024 | **AUTHORIZED B0** |
| TD / FG per drive | derived prior PBP scoring outcomes | team/game/drive | prior games only | fixed 8-team-game lagged state | rare/ambiguous scoring handled by frozen tail rule | 2016–2024 | **AUTHORIZED B0** |
| turnover/takeaway per drive | prior PBP | team/game/drive | prior games only | fixed 8-team-game lagged state | explicit unknown/excluded malformed drive | 2016–2024 | **AUTHORIZED B0** |
| explosive-play rate | prior PBP | team/game/play | prior games only; explosive definition frozen in Phase 3 contract before outputs | fixed 8-team-game lagged state | denominator/support recorded | 2016–2024 | **AUTHORIZED B0 after definition is coded once, not tuned** |
| red-zone rates | prior PBP | team/game/drive | prior games only | would use fixed lag if activated | not encoded as zero when unavailable | multi-season possible | **DEFERRED; not B0** |
| sacks / pressure | nflverse PBP / advanced sources | team/game/play/player IDs where needed | prior games only | source publication must precede next forecast | explicit | PBP sacks broad; pressure advanced varies | **DEFERRED; not B0** |
| special teams | prior PBP | team/game/play | prior games only | prior-completed game | explicit | broad | **DEFERRED; rare tail only in B0** |
| market spread / total | nflverse games historical fields | `game_id` | historical field treated only as closing/late family | exact capture horizon opaque; never called T-120 | paired rows only; never imputed | 2016–2025 where present | **AUTHORIZED C0 as historical closing-like benchmark** |
| prospective T-120 market | repository market collector / The Odds API when healthy | game + book + snapshot timestamp | latest qualified snapshot at/before kickoff-120 | retrieval and provider timestamps required | failed auth/stale/sparse = unavailable | prospective only | **BLOCKED currently; required for same-horizon future work** |
| QB expected starter | timestamped depth/expected-lineup sources | GSIS/player ID + game/team | identity must be explicitly known by simulated horizon | snapshot timestamp <= decision time | missing = unknown, never continuity | unified 2022–2025 fixed-horizon history absent | **BLOCKED/CONDITIONAL** |
| QB prior quality | prior completed-game PBP/NGS after starter identity qualifies | stable player ID | only for qualified expected starter | observed prior data published before forecast | shrinkage + unknown flag | data broad, identity/PIT start-state gap remains | **CONDITIONAL** |
| injury/practice state | 2025 composite; prospective NFL snapshots | stable player ID + team/week | report/practice state known by horizon | source timestamp <= horizon | missing = unknown | qualified 2025 only historically | **SENSITIVITY ONLY / CONDITIONAL** |
| OL continuity/personnel | depth/roster/participation sources | player ID + position/team | expected role must be known pregame | participation cannot use same-game realized snaps | missing = unknown | incomplete unified PIT history | **BLOCKED/CONDITIONAL** |
| NGS/PFR/FTN advanced | nflverse-distributed advanced feeds | player/team/game IDs | prior completed game only | must satisfy observed publication lag before next forecast | structural missingness explicit | varies by family | **DEFERRED** |
| static roof/venue | schedule + verified venue mapping | game/venue ID | venue assignment known pregame | static metadata only | unresolved venue = unknown | broad but venue mapping must pass | **OPTIONAL FUTURE; not initial A0/B0/C0** |
| weather forecast | NWS / archived Open-Meteo contract | game + venue + forecast issue time | forecast available by simulated horizon | issue/init availability <= horizon | missing = unavailable | historical reconstruction not yet qualified; prospective collector incomplete | **BLOCKED** |
| travel/time zone | deterministic schedule + exact venue | team/game/venue | calculable pregame | static calculation | unresolved venue = unknown | potentially broad | **DEFERRED** |
| news/text | official/team/media sources | URL/article ID + publication timestamp + entity mapping | published by horizon | timestamp must be preserved | missing is not negative evidence | no uniform historical archive | **BLOCKED from numerical initial model** |

### Source-policy consequences

1. **Initial A0/B0/C0 is fully feasible at $0** without QB, injury, weather, paid charting or repaired prospective market collection.
2. The Odds API HTTP 401 affects prospective multi-book/T-120 research, not the historical closing-like C0 experiment.
3. Unresolved venue receipts block qualified weather and precise travel extensions, not A0/B0/C0.
4. No Phase 3 implementation may reinterpret a blocked/conditional row as authorized without a logged source-contract amendment written before results from that feature are inspected.

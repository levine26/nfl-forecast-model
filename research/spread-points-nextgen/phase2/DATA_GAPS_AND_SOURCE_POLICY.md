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

## 1A. Feature-family PIT feasibility matrix

| Feature family | Source | Stable identity key | Pregame availability / publication rule | Missingness | Historical coverage | Initial Phase 3 status |
|---|---|---|---|---|---|---|
| dynamic offense/defense state | derived from nflverse PBP + schedule | `game_id`, team abbreviation / franchise mapping | only completed prior games; state updated after game completion | fail row/candidate build if core game/team identity is unresolved | multi-season | **core A/B** |
| opponent-adjusted EPA / success | nflverse PBP | `game_id`, `posteam`, `defteam` | prior completed games only; adjustment fit only inside training chronology | no future/opponent backfill | multi-season | **core A/B** |
| drives / possessions | nflverse PBP | `game_id`, drive id, possession team | prior completed games only | explicit malformed/missing drive handling | multi-season | **core B** |
| red-zone rates | nflverse PBP | `game_id`, possession team, yardline/play | prior completed games only; fixed red-zone definition | explicit denominator=0 and missing play state | multi-season | **bounded B input** |
| explosive-play rates | nflverse PBP | `game_id`, offense/defense team, play id | prior completed games only; threshold fixed before results | explicit no-qualified-play state | multi-season | **bounded B input** |
| sacks / turnovers | nflverse PBP | `game_id`, team, play id | prior completed games only | explicit event/denominator handling | multi-season | **bounded B input** |
| FG / special-teams scoring | nflverse PBP | `game_id`, team, play id | prior completed games only | rare-event pooling; no hindsight roster attribution | multi-season | **bounded B / tail** |
| home/rest | nflverse schedule | `game_id`, team, game date | deterministic from schedule known before kickoff | fail if date/team identity missing | multi-season | **core A/B/C** |
| static venue/roof | nflverse schedule + qualified venue map | `game_id`, venue/stadium identity | venue for that game must be resolved independently of outcome | unknown, never guessed | broad schedule; exact mapping variable | **optional static sensitivity** |
| QB starter / replacement | timestamped depth/expected-lineup evidence + stable player IDs | GSIS/player id + `game_id` + snapshot time | expected starter must be timestamped <= simulated horizon | unknown != same starter | no unified fixed-horizon 2022–2025 history | **blocked/conditional** |
| injury / availability | qualified practice/injury snapshots | GSIS/player id + team/week + report timestamp | report version must be known <= horizon | missing != healthy | qualified 2025 slice; prospective 2026+ | **blocked core; sensitivity only** |
| OL continuity / personnel | depth charts + availability + roster identity | player ids + lineup snapshot time | expected role/lineup timestamp <= horizon | unresolved role explicit | incomplete multi-season PIT | **blocked/conditional** |
| advanced player/charting | nflverse NGS / FTN / PFR advanced | player/team/week identifiers | prior completed game plus source-publication lag before forecast | structural missingness flag required | source-dependent | **not initial; later ablation only** |
| weather | NWS / archived Open-Meteo + exact venue | `game_id` + venue coordinates + forecast issue/update timestamp | forecast issue/update available <= simulated horizon | missing forecast != benign weather | historical PIT incomplete; prospective collector exists | **blocked** |
| historical market | nflverse schedule fields | `game_id` | exact historical horizon/book opaque | paired rows only; never impute line | multi-season | **C closing/late benchmark only** |
| prospective market | timestamped multi-book collector | `game_id` + book/source + fetched/update timestamp | latest valid snapshot <= declared horizon | failed collector != no move | current collector issue; no usable ledger at Phase 1 audit | **blocked for T-120 claims** |

The key distinction is **source qualification versus feature authorization**. A source can be technically accessible yet remain inadmissible for a fixed-horizon historical experiment.

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

## 8. Phase 3 feature-source feasibility matrix

This matrix is the implementation contract for the proposed feature families. "Publication rule" refers to when the information is eligible for a simulated forecast, not merely when the source ultimately contains it.

| Feature family | Source | Stable key | Pregame / publication rule | Lag | Missingness | Historical coverage / status |
|---|---|---|---|---|---|---|
| opponent-adjusted EPA / success | nflverse PBP | game ID + team | only completed prior games; sequential opponent state | >=1 completed game | explicit; no same-game fill | strong multi-season; **initial A/B allowed** |
| dynamic offense/defense state | derived from prior schedule/PBP | team + game order | update only after prior game completes | sequential | prior/shrinkage state, not future imputation | strong; **initial A allowed** |
| drives / possessions | nflverse PBP drive fields / derived drive boundaries | game ID + drive + offense team | prior completed games only | >=1 game | malformed/unresolved drives excluded and counted | strong enough for B subject to construction QA |
| red-zone opportunity/conversion | prior PBP | game + team/play | prior completed games only | >=1 game | shrink sparse rates; preserve missing | strong; **controlled B input** |
| explosive-play rate | prior PBP | game + team/play | definition frozen before results; prior completed games only | >=1 game | explicit | strong; **controlled B input** |
| sacks / turnovers | prior PBP | game + team/play | prior completed games only | >=1 game | explicit; regularize rare rates | strong; **controlled B input** |
| field-goal / special-teams scoring | prior PBP | game + team/play | prior completed games only | >=1 game | rare defensive/ST scores handled as tail component | strong for basic scoring; richer player ST state not required |
| home/rest | schedule | game ID | deterministic schedule known pregame | none | fail if game identity unresolved | strong; **initial A/B/C allowed** |
| static stadium/roof | schedule + qualified venue map | game ID/venue | use only truly static value tied to correct venue | none | unknown != outdoor | conditional sensitivity; venue mapping must pass |
| market spread/total | nflverse schedule for historical family | game ID | closing/late benchmark only; exact horizon opaque | none | exact paired rows only | strong benchmark; **C allowed with label** |
| prospective T-120 market | timestamped collector | game ID + book + captured_at | latest valid snapshot at/before T-120; staleness rules | none | failure/stale != no movement | collector currently blocked by HTTP 401; **not historical C** |
| QB starter / replacement | timestamped expected-lineup/depth evidence + lagged QB performance | GSIS/player ID + game ID | starter identity timestamp <= decision horizon | lag QB quality | unknown starter remains unknown | no uniform 2022–2025 fixed-horizon history; **conditional** |
| injuries / availability | qualified reports/snapshots | player ID + team + game | report/snapshot available <= horizon | source-specific | missing != healthy | qualified 2025 slice + prospective 2026; **conditional only** |
| OL/personnel continuity | depth/availability/roster history | stable player IDs | as-of lineup/role must be proven | source-specific | unresolved role fails closed | insufficient uniform 2022–2025 history; **conditional** |
| NGS / FTN / PFR advanced | nflverse/public advanced feeds | player/team + week | source publication must precede next forecast horizon | >=1 published game/week | structural missingness explicit | optional controlled ablation, not prerequisite |
| weather | NWS/Open-Meteo forecast-as-of + exact venue | game ID + forecast issue time | forecast issue/update <= decision horizon | none | missing forecast != normal | venue receipts incomplete; **blocked initially** |
| news/coaching state | timestamped official/reputable publication | game/team + published_at | published <= simulated horizon | none | absence of article != no change | no uniform numeric historical pipeline; **not initial** |

### Operational constraints retained

- The Odds API HTTP 401 state blocks strong prospective multi-book same-horizon evidence until repaired; it does **not** block closing-like historical C.
- Unresolved venue receipts block qualified prospective weather capture; they do **not** authorize realized historical weather.
- Source existence never substitutes for as-of proof.

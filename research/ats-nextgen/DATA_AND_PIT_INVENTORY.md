# Phase 1 Data & Point-in-Time Inventory

## 1. Market source matrix

| Source | Line | Side price | Book | Timestamp | Historical coverage | PIT-safe classification |
|---|---|---|---|---|---|---|
| nflverse schedule fields used by LevLine | yes | **no qualified spread-side juice** | opaque | opaque | multi-season including 2022–2025 | usable only as `historical_closing_late_benchmark_exact_horizon_opaque` |
| nflverse schedule moneylines | moneyline pair, plus spread/total row | yes for ML odds where populated | opaque | opaque | multi-season | no-vig market probability benchmark; not a specific T-minus quote |
| `src/nfl_forecast/market_t120.py` from append-only LevLine run history | yes when captured | no dedicated spread-side price field in selector | not preserved as a constituent book | LevLine snapshot/run time | prospective/archive-dependent | PIT-safe for the exact latest-valid <= T-120 rule when source row exists |
| The Odds API collector in `challenger_market_sources.py` | yes | **yes** | **yes** | retrieval + bookmaker `last_update` | current/prospective under current free-source policy | conceptually strong; operationally unqualified until authorization/source capture succeeds |
| The Odds API constituent books | yes | yes | yes | per-book update | prospective | preserve raw quotes; same-horizon consensus only |
| David Sasser public board | current/open display | not a qualified data feed | not documented | page update time only | public current board | comparator only, not LevLine training data |

### Current operational note

The prior authoritative data audit records that The Odds API credential path was configured but returned HTTP 401 and the market snapshot ledger was empty at that audit. Phase 1 does not silently promote the collector to “available.” Phase 2 must re-qualify it before prospective use.

### PropLine

No active `PropLine`/`propline` integration was located in the inspected live `main` ATS/market code or repository code search. Prior Props research is retired/separate and is not assumed to provide spread-side pricing for this program.

## 2. Football source matrix

| Source | Use in V1 | PIT rule |
|---|---|---|
| nflverse PBP / nflreadpy | lagged team efficiency state | only prior completed games; existing shift-before-roll contract |
| pregame Elo derived in repository | compact team-strength state | value written before current result update |
| schedule/rest | matchup/rest context | known pregame fields only |
| market spread/total/moneyline | primary benchmark/features | use exact historical benchmark semantics; no horizon relabeling |
| 2025 practice-state composite | **not primary V1** | qualified only for its narrow 2025 T-120 practice-state contract |
| timestamped 2025+ depth charts / 2026 archives | prospective extension | snapshot time <= decision time |
| weather | **not primary V1** | only archived/preserved pregame forecast, never realized weather masquerading as forecast |
| current news/media | **not numeric V1** | historical use requires preserved publication timestamp |

## 3. Frozen compact V1 feature hierarchy

Every feature is computed at the row's market decision snapshot and uses training-fold imputation/scaling only.

### Market features

Required line:

1. sportsbook home spread `L`;
2. market home-margin center `C=-L`;
3. favorite size `|L|`;
4. market total;
5. vig-free home moneyline probability when both home/away moneylines exist;
6. missing indicators for optional total/moneyline fields;
7. fixed `C × centered_total` interaction;
8. fixed `|L| × centered_total` interaction.

No historical line movement, side juice, book dispersion or multi-book consensus is included unless a separate source is qualified before a new candidate version is frozen.

### Football features

Use exactly one compact EWMA representation per concept, not 3/5/8-window duplication:

1. pregame Elo home-minus-away differential;
2. EWMA offensive EPA/play differential;
3. EWMA defensive EPA/play-allowed differential;
4. EWMA pass EPA differential;
5. EWMA defensive pass-EPA-allowed differential;
6. EWMA rush EPA differential;
7. EWMA defensive rush-EPA-allowed differential;
8. EWMA offensive success-rate differential;
9. EWMA defensive success-allowed differential;
10. EWMA neutral-situation EPA differential;
11. rest differential.

The EWMA must use the existing chronology-safe alpha `0.15` semantics and be shifted one completed game before the target row. Phase 2 may map these semantic fields to existing column names but may not substitute a new feature family.

## 4. Missingness contract

- `L` is mandatory for ATS evaluation; rows without a qualified spread are ineligible.
- optional numeric market/football features use the **training-fold median** and a missingness indicator when missingness occurs;
- no missing injury row becomes “healthy”;
- no missing price becomes -110;
- no missing market movement becomes zero movement;
- no current endpoint is projected backward to create history.

## 5. Personnel decision

Player/QB state remains important but is **reserved for a later extension**. V1 must first answer whether the distributional/quantile framing improves on the market with existing compact PIT-safe state. The narrow 2025 practice reconstruction is not enough to justify a new multi-season personnel model inside this ATS sprint.

## 6. Live 2026 source qualification firewall

Live 2026 inputs may be queried solely to determine whether a provider exposes the required fields/timestamps. Completed 2026 game outcomes, graded ATS results or candidate performance must not enter source choice, feature choice, thresholds, model families or blend weights.
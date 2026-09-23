# Data and Point-in-Time Inventory

Audit date: 2026-09-23

## Source matrix

| Source | Line | Spread-side price | Book | Timestamp | Historical coverage | PIT safe? | Phase-2 role |
|---|---|---|---|---|---|---|---|
| nflverse-style schedules used by LevLine | Yes (`spread_line`) | No | No | No quote timestamp | broad historical schedule coverage | Only as generic historical/late benchmark; not exact horizon | Primary historical line/total/ML development input |
| LevLine `outputs/run_history.csv` + `market_t120.py` | Yes when captured | No spread juice in selected schema | No | Yes, prediction timestamp + computed T-120 cutoff | prospective retained LevLine history | Yes when selector proves snapshot <= T-120 | Prospective shadow/horizon source; not backfilled history |
| The Odds API current endpoint | Yes | Yes | Yes | bookmaker/response update time | current | Yes if raw response archived before lock | Prospective priced multi-book extension |
| The Odds API historical endpoint | Yes | Yes | Yes | historical snapshot + bookmaker update time | NFL snapshots available from 2020-06-06; 10-min then 5-min cadence per provider docs | Yes if query snapshot is <= frozen horizon and raw response archived | Optional paid historical qualification; not assumed available |
| David Sasser public pages | Open/current line visible | Not a reliable two-sided spread-price feed | Not auditable as source contract | Public page state, no canonical archive contract | recent/public display | No for reproducible historical PIT ingestion | Comparator/design observation only |
| PropLine game-spread collector in current live tree | Not identified | Not identified | Not identified | Not identified | n/a | n/a | None; do not assume an integration that is absent |

## Current LevLine market fields

`src/nfl_forecast/features.py` carries schedule fields including:

- `spread_line`;
- `total_line`;
- `home_moneyline`;
- `away_moneyline`.

`src/nfl_forecast/market.py` converts American moneyline odds to implied probabilities and normalizes paired home/away moneyline probabilities to a no-vig home-win probability.

This is useful for M1/M2 market-shape baselines. It does **not** recover the price attached to either spread side.

## T-120 research selector

`src/nfl_forecast/market_t120.py` is explicitly research-only. It:

- filters append-only history to market snapshots;
- computes kickoff and T-120 target time;
- selects the latest usable market observation at or before that cutoff;
- records the chosen timestamp, minutes to kickoff, staleness and no-lookahead boolean;
- omits a game rather than filling it from a later snapshot.

This is a strong prospective PIT pattern. It must not be used to claim that historical schedule spread fields represent T-120.

## Football feature provenance

The current feature pipeline constructs per-team game aggregates from PBP and shifts rolling/EWMA state by one game before matchup construction. V1 may use only the following compact pregame state, subject to Phase-2 row-level PIT validation:

- Elo difference (`home_elo - away_elo`);
- `rest_diff`;
- `diff_off_epa_ewma`;
- `diff_pass_epa_ewma`;
- `diff_rush_epa_ewma`;
- `diff_success_rate_ewma`;
- `diff_def_epa_allowed_ewma`;
- `diff_def_pass_epa_allowed_ewma`;
- `diff_def_rush_epa_allowed_ewma`;
- `diff_def_success_allowed_ewma`;
- `diff_win_ewma`.

V1 excludes broad lag-window variants and all new historical player-state reconstruction.

## Historical market feature contract

For a row to enter the main historical Q1-Q3 development set:

- regular-season game;
- season 2015–2025;
- final home/away score present only for training/evaluation according to fold chronology;
- numeric quoted `spread_line`;
- line must lie on an integer or half-point grid; quarter-line/nonstandard quotes are ineligible rather than coerced;
- `total_line` may be missing and is training-median imputed with a fixed missing indicator;
- moneyline-derived no-vig probability is used only when both paired moneylines exist; otherwise training-median imputed with a fixed missing indicator.

No row gains a field from a later market horizon than the row's declared market object.

## Missingness contract

For Q1/Q3 numeric feature inputs:

1. training-fold median imputation only;
2. a fixed missing indicator accompanies each input variable, even if a given fold has zero missing values;
3. standardization parameters are fitted only on training data;
4. target/outer data never determine an imputation or scaling statistic.

For Q2 market total, training-fold median is used if missing and a total-missing indicator is retained in provenance; the frozen conditional-scale formula itself does not add an extra missingness coefficient.

## 2015 scoring-regime floor

The NFL moved extra points to the 15-yard line beginning in the 2015 season. Because Q2 explicitly estimates key-number mass, V1 does not pool pre-2015 seasons into the same key-mass regime. The floor is therefore 2015.

This is a preregistered regime choice, not a result-driven truncation.

## 2022–2025 evidence status

These seasons are usable for chronology-clean development/OOF mechanism analysis but are non-pristine because LevLine has repeatedly inspected them in prior research. Any positive Q1-Q3 historical result remains development evidence and cannot authorize production.

## Completed 2026 firewall

Completed 2026 game outcomes are not an eligible data source for Phase 1–3 Q1-Q3 architecture or historical development. In particular they may not enter:

- rolling feature construction for a retrospective candidate claim;
- distribution/key-mass estimation;
- model/calibration/blend fitting;
- threshold selection;
- model rescue.

Outcome-blind 2026 market/input rows may be viewed only to test whether a source/pipeline field exists and has the promised timestamp/provenance.

## Price/juice consequence

Because the main historical development source lacks spread-side juice:

- probability scoring remains fully feasible;
- ATS grading remains fully feasible from spread + final score;
- exact-price historical EV/ROI is not available on those rows;
- standard -110 EV/ROI may appear only as an explicitly labeled sensitivity analysis;
- `positive-EV at quoted price` subsets require a verified priced source and are omitted otherwise.

No `-110` value may be silently inserted into a missing historical price field.

## Prospective collection recommendation

If Q1-Q3 survive Phase 3, the prospective shadow collector should archive the raw, bookmaker-specific spread quote at the frozen horizon:

- book ID;
- home line and home price;
- away line and away price;
- total and moneyline markets where available;
- provider snapshot time;
- bookmaker last-update time;
- retrieval time;
- raw-response hash/file;
- game ID mapping;
- T-120 eligibility/staleness proof.

That future collection can support actual-price EV, CLV, book dispersion and price-at-key hypotheses without retrospective reconstruction.
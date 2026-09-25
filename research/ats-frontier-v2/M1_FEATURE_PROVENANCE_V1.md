# M1 Feature Provenance V1

Program: `FV2-PROS-M1-MARKETSTATE-01`

Status: `FROZEN_IMPLEMENTATION_CONTRACT`

Completed-2026 outcomes used to define this contract: `0`

This document operationalizes implementation details left intentionally unspecified by the preregistration. It does not change the M1 hypothesis, target, model family, null, or metric.

## Horizon boundary

Predictor-accessible captures are limited to `T-2160m`, `T-720m`, `T-360m`, and `T-120m`. The frozen feature vector itself uses the T-120 state plus T-360→T-120 path terms. T-2160/T-720 remain captured context and provenance but do not add new V1 predictor columns.

`T-60m`, `T-30m`, and `LATEST_PREKICK` are diagnostic-only and are emitted to a separate artifact. Existing `T-45m` infrastructure is outside M1.

## Eligibility rule

A book is M1-complete at a horizon only when all of the following are available point-in-time: home spread, two-way no-vig spread-side probability, two-way no-vig moneyline probability, total, quote age, sportsbook identity, event identity, and kickoff identity. A qualifying horizon requires at least **2 complete books**. Two is frozen because it is the mathematical minimum for the cross-book dispersion/breadth mechanism and matches the existing research minimum; this value was fixed without outcome inspection.

A T-120 predictor row additionally requires at least 2 common complete books between T-360 and T-120. Partial books remain append-only raw evidence but do not close M1 eligibility.

Quotes with age **>= 15 minutes** are classified as stale for the frozen stale-share feature. This threshold is an outcome-blind implementation definition and is not tunable within M1 V1.

Fixed-horizon observations must occur no later than the nominal target and within the existing 7.5-minute early tolerance. Later observations cannot repair a missed horizon.

Provider kickoff may differ by at most 30 minutes from the schedule kickoff during event resolution. A cross-horizon change in the schedule kickoff or event ID invalidates the joined predictor row rather than re-anchoring earlier captures.

## Frozen feature provenance

| # | Frozen family | V1 field | Source / definition | Missingness behavior |
|---|---|---|---|---|
| 1 | Consensus spread median | `consensus_spread_t120` | Median home spread across complete T-120 books | Predictor row ineligible if T-120 has <2 complete books |
| 2 | Consensus no-vig favorite/underdog spread-side probability | `spread_favorite_no_vig_t120` | Median-logit T-120 spread cover probability, oriented to the T-120 favorite | Predictor row ineligible if unavailable |
| 3 | Consensus no-vig moneyline probability | `moneyline_favorite_no_vig_t120` | Median-logit T-120 moneyline probability, oriented to the same T-120 favorite | Predictor row ineligible if unavailable |
| 4 | Consensus total | `consensus_total_t120` | Median total across complete T-120 books | Predictor row ineligible if unavailable |
| 5 | Cross-book spread dispersion | `spread_dispersion_t120` | Population SD of T-120 home spread across complete books | Predictor row ineligible if <2 complete books |
| 6 | Active-book count / breadth | `active_book_count_t120` | Count of complete T-120 books; V1 operationalizes breadth as qualifying active-book count | Predictor row ineligible if <2 |
| 7 | Quote age / stale share | `median_quote_age_minutes_t120`, `stale_book_share_t120` | Median quote age and fraction with quote age >=15m | Predictor row ineligible if quote age unavailable in a required complete book |
| 8 | T-360→T-120 number movement | `favorite_spread_strength_move_t360_to_t120` | Change in favorite-oriented spread strength using the T-120 favorite orientation | Predictor row ineligible if T-360/T-120 path unavailable |
| 9 | Price movement conditional on unchanged number | `spread_price_move_unchanged_number_t360_to_t120` | Median favorite-oriented spread-price probability change among common books whose spread number is unchanged; deterministically 0 when no common book has unchanged number | No additional imputation or outcome-driven rescue |
| 10 | Movement breadth | `movement_breadth_t360_to_t120` | Mean direction score across common books; number movement is primary, spread-price movement breaks unchanged-number ties | Predictor row ineligible if <2 common complete books |
| 11 | Key-number crossing | `key_number_crossing_3_or_7_t360_to_t120` | Indicator that consensus favorite spread strength crosses 3 or 7 between T-360 and T-120 | Deterministic 0/1 |
| 12 | Spread/moneyline consistency residual | `spread_moneyline_logit_residual_t120` | Logit(spread favorite no-vig probability) minus logit(moneyline favorite no-vig probability) | Predictor row ineligible if either probability unavailable |

## Diagnostic provenance

`T-60m`, `T-30m`, and `LATEST_PREKICK` consensus spread, spread-side probability, and moneyline probability are written only to the diagnostic artifact. `LATEST_PREKICK` selects the latest qualifying request from the 10-to-1-minute pre-kick window. These fields are mechanically absent from the predictor feature registry.

## Outcome firewall

Rows carrying completed-game outcome fields are rejected by the M1 derivative. Predictor construction requires `research_only=true`, `production_authorized=false`, a pre-kick request timestamp, and the strict horizon contract. The feature builder contains no target-score, ATS-result, or final-margin dependency.

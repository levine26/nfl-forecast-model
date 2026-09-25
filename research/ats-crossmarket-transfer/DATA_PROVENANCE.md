# Data Provenance

## Historical game / spread surface

The experiment reuses the canonical historical data construction from `research/ats-historical-challenger/historical_challenger.py`, which loads repository core data only through 2025, builds the same game identities/features, and joins the accepted V2 sportsbook spread/total fields. `spread_line` is the repository-normalized expected home margin. If a conventional home spread is denoted by L, the corresponding center is C=-L; the repository field already stores C.

## F-ST and market-moneyline probability surface

The source is the immutable package artifact read by `src/nfl_forecast/fst_nested_pure.py::load_frozen_training_frame()`. Its verified training frame contains exactly:

`game_id, row_position, season, home_win, market_prob, pure_prob`.

The archive covers 2020–2025, is game-keyed, checksum-validated, and refuses post-2025 outcomes. The `market_prob` values are reused exactly as they were used in the historical F-ST experiment. This program does **not** reconstruct a new moneyline series, does not substitute current consensus prices, and does not relabel the historical probability as T-120/closing when that exact horizon is not established by the archive.

Semantic label in this experiment:

`FST_FROZEN_HISTORICAL_MARKET_PROBABILITY_ARCHIVE_EXACT_ORIGINAL_HORIZON_OPAQUE`.

Where raw paired home/away moneyline prices are unavailable in this immutable archive, no new de-vig transformation is invented. The experiment inherits the market-probability semantics already validated for the F-ST historical evidence.

## Historical F-ST surface

For each target season, the same frozen two-input architecture is refit on earlier seasons only using `logit(market_prob)` and `logit(pure_prob)`. Final 2026 production coefficients are never back-applied. The resulting `fst_home_prob` is therefore a chronology-clean season-forward reconstruction on the archived historical rows.

## KMASS nuisance surface

The experiment reuses, verbatim, the accepted target-season prior-only `CONSTANT_SCALE_KEY` nuisance fits from `research/ats-historical-challenger/v2_nuisance_freeze.json`. Those fits descend from canonical ATS Frontier V2 Phase-4 artifact `10820397832` and are not retuned here.

## Outer common-row rule

Primary 2022–2025 comparisons use the exact joined rows on which historical game outcome, spread/total, archived market probability, chronology-clean F-ST probability, and frozen KMASS nuisance fit are all available. Candidate/null deltas are always paired on identical rows.

Completed-2026 outcomes are forbidden and must equal zero in every execution receipt.

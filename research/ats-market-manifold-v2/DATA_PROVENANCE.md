# ATS Market Manifold V2 — Data Provenance

## Historical game/spread/total scaffold

Reuse the schedule-only historical scaffold introduced and hard-gated in ATS Cross-Market Transfer V1. It reads the canonical nflverse games schedule through 2025, restricts to completed regular-season games, constructs integer home margin from final scores, and uses repository `spread_line` / `total_line` semantics.

Before any V2 scoring, the sorted historical game-ID SHA-256 must equal the accepted PR #582/V1 identity:

`26aed1cdeb34d0381e1af3fbc4e00a14360330861ad04ecc5c244635b8e0b156`.

No PBP, team EPA, QB, injury, personnel, weather, or other football-state feature enters a V2 primary candidate.

## Historical moneyline probability surface

Use the immutable F-ST training archive only as the repository's accepted source of historical `market_prob` keyed by `game_id` and `season`.

Semantic class is inherited unchanged:

`FST_FROZEN_HISTORICAL_MARKET_PROBABILITY_ARCHIVE_EXACT_ORIGINAL_HORIZON_OPAQUE`.

V2 does not reconstruct a different historical moneyline series, substitute modern consensus prices, infer unavailable paired-book juice, or relabel the archive as a known closing/T-minus horizon.

Although the immutable archive also contains `pure_prob`, and V1 reconstruction can produce `fst_home_prob`, those fields are forbidden from V2 primary candidate construction. Preflight mutates the F-ST field and requires candidate probabilities to remain bitwise/numerically invariant.

## KMASS nuisance surface

For outer seasons 2022–2025, reuse the exact accepted prior-only `CONSTANT_SCALE_KEY` nuisance fits from:

`research/ats-historical-challenger/v2_nuisance_freeze.json`.

For the 2021 inner-validation rows required by 2022 theta selection, reuse the strict chronology construction accepted in V1: fit only the nuisance parameters on pre-2021 historical games while inheriting the already-frozen structural hyperparameters `nu=30`, `lambda_scale=10`, `lambda_key=1`, `conditional=false`, `use_key=true`.

Every inner validation row is therefore scored using a nuisance fit trained strictly before that row's season.

## Common-row identity

Expected V2 archive counts, inherited from the accepted V1 hard gate:

- 2021: 272
- 2022: 271
- 2023: 272
- 2024: 272
- 2025: 272

Primary outer OOF N must therefore be 1,087 unless the experiment fails closed for identity drift.

## Evidence boundary

The 2022–2025 rows have been used in prior LevLine research and are explicitly non-pristine development evidence. They may reject or provisionally support V2, but they cannot provide an untouched confirmation claim.

Completed 2026 outcomes are forbidden. Production files and live forecasting behavior are read-only/out of scope.
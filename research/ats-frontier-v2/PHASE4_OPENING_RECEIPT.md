# PHASE 4 OPENING RECEIPT

Program: `LEVLINE_ATS_FRONTIER_V2`

Phase: `4 — CONTROLLED HISTORICAL DEVELOPMENT, ABLATION & EMPIRICAL VALIDATION`

Status at receipt: `OPEN / PRE_RESULT_GATE_NOT_YET_PASSED`

Date opened: `2026-09-24`

Branch: `research/ats-frontier-v2-phase4`

Base `main` SHA: `2391ccded6ab7252f89937b98e24afeafd4d7ce6`

Production model: `F-ST-01-FROZEN-2026`

Production forecasting state: `UNCHANGED`

Completed-2026 outcomes used: `0`

Candidate performance inspected before this receipt: `NO`

## Frozen historical portfolio

Only these candidates are authorized in Phase 4:

- `FV2-HIST-M3-DSSM-01`
- `FV2-HIST-M4-DMARGIN-01`

Historical M1 remains `BLOCKED_PENDING_PAID_SOURCE`.

Historical M2 remains excluded.

No third historical candidate and no M3+M4 combined candidate are authorized.

## Frozen comparison identities

M3 null: `M3-NULL-MARKET-NORMAL-01`

M3 ablations, exactly:

1. `MARKET_ONLY`
2. `STATIC_FOOTBALL_STATE`
3. `DYNAMIC_NO_QB`
4. `DYNAMIC_FULL`

M4 null: `M4-NULL-STUDENTT-CONSTANT-01`

M4 ablations, exactly:

1. `CONSTANT_SCALE_NO_KEY`
2. `CONDITIONAL_SCALE_NO_KEY`
3. `CONSTANT_SCALE_KEY`
4. `FULL_CONDITIONAL_SCALE_KEY`

## Evidence boundary

- state/training warm-up begins: `2010`
- outer development seasons: `2022, 2023, 2024, 2025`
- primary population: regular season
- 2022–2025 designation: `DEVELOPMENT / NON-PRISTINE`
- completed-2026 outcomes: sealed
- historical market label: `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`

## Frozen deterministic execution settings

The Phase-1/2/3 repository contracts required a fixed bootstrap seed but did not contain a concrete numeric seed token. Before any Phase-4 target scoring, this receipt freezes the missing deterministic value:

- `BOOTSTRAP_SEED = 20260924`
- paired bootstrap resamples: `10000`
- bootstrap unit: NFL week blocks within explicit season strata
- interval: `2.5 / 97.5 percentile`

This is a pre-result governance completion, not a result-driven choice. The seed may not be changed after candidate performance exists.

## Scientific embargo and change control

Before any candidate scoring, Phase 4 must pass the preregistered synthetic sign, chronology, leakage, M3 state-update, and M4 PMF/tail/push tests; prove target-game data cannot enter predictors; prove completed-2026 outcomes remain excluded; freeze implementation/config hashes; and commit the pre-result scientific surface.

Engineering bug corrections are allowed only when they preserve the frozen scientific hypothesis and must be recorded. After candidate performance is inspected, new features, grids, latent states, distributions, key numbers, horizons, subsets, calibration methods, selective betting thresholds, and rescue candidates are prohibited.

ATS is diagnostic only. No historical selective betting strategy is authorized. Any `REFERENCE_MINUS110` arithmetic is hypothetical, not actual historical sportsbook ROI.

## Production firewall

Phase 4 may not modify production numerical forecasting behavior, the frozen F-ST model, Sunday Signal forecasts, win probabilities, fair spread, score projections, ATS logic, history, grading, or deployment.

## Phase-4 authority

The frozen repository contracts in `research/ats-frontier-v2/` remain authoritative. If an implementation convenience conflicts with those contracts, the contract controls.

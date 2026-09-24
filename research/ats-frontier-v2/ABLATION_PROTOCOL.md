# ABLATION PROTOCOL

Ablations are hypothesis tests, not a feature-search menu. Only the following are authorized in Phase 4 / later prospective evaluation.

## M3 — `FV2-HIST-M3-DSSM-01`

1. `MARKET_ONLY` — exact market null.
2. `STATIC_FOOTBALL_STATE` — prior-only pooled football state with no process-noise evolution.
3. `DYNAMIC_NO_QB` — dynamic offense/defense states, no QB latent state.
4. `DYNAMIC_FULL` — offense/defense/QB dynamic state; frozen candidate.

Interpretation:

- `DYNAMIC_FULL` vs `MARKET_ONLY` tests overall incremental football information.
- `DYNAMIC_FULL` vs `STATIC_FOOTBALL_STATE` tests whether dynamic state representation contributes beyond static summaries.
- `DYNAMIC_FULL` vs `DYNAMIC_NO_QB` isolates the preregistered QB state component.

No pass/rush/unit/matchup feature ablations may be added after target results are seen.

## M4 — `FV2-HIST-M4-DMARGIN-01`

1. `CONSTANT_SCALE_NO_KEY` — strong Student-t null.
2. `CONDITIONAL_SCALE_NO_KEY` — tests heteroskedastic scale only.
3. `CONSTANT_SCALE_KEY` — tests 0/|3|/|7| mass offsets only.
4. `FULL_CONDITIONAL_SCALE_KEY` — frozen candidate.

No additional key margins, tail families or conditional subsets may be added after target results are seen.

## M1 prospective — `FV2-PROS-M1-MARKETSTATE-01`

1. `STATIC_MARKET_LEVEL` — T-120 spread/price/ML/total only.
2. `+DISPERSION_BREADTH_STALENESS`.
3. `+PATH` — T-360→T-120 number/price movement and key crossing; frozen full prospective identity.

Lead/lag is intentionally excluded from V1.

## M2 prospective — `FV2-PROS-M2-QBDELTA-01`

1. `MARKET_ONLY`.
2. `MARKET_PLUS_QB_ABILITY_LEVEL`.
3. `MARKET_PLUS_EXPECTED_QB_VALUE_DELTA` — frozen full identity.

## Common rules

- All ablations use exact common rows with their parent candidate where possible.
- Ablations inherit the same chronology, preprocessing and market null.
- They may explain a result but may not create a replacement candidate in Phase 4.
- No ablation is selected by ATS hit rate or ROI.
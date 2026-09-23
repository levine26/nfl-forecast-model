# Candidate 5 Feature and Component Contract

All features are frozen before Candidate-5-specific performance is inspected. No raw rolling-variable expansion is authorized.

## Incumbent
`fst_prob` from the chronology-clean historical F-ST reproduction; clipped to `[1e-6, 1-1e-6]` only for logits. `fst_confidence = abs(fst_prob - 0.5)`.

## A0 fields
- `a0_home_win_probability`
- `a0_expected_margin`
- `a0_score_uncertainty`
- `a0_offense_strength_diff`
- `a0_defense_strength_diff`
- derived `a0_logit_delta = logit(a0_home_win_probability) - logit(fst_prob)`

## B0 fields
- `b0_home_win_probability`
- `b0_expected_margin`
- `b0_expected_total`
- `b0_margin_variance` -> preregistered `b0_margin_sd = sqrt(variance)`
- `b0_total_variance` -> preregistered `b0_total_sd = sqrt(variance)`
- derived `b0_logit_delta = logit(b0_home_win_probability) - logit(fst_prob)`

## Disagreement fields
- `a0_b0_logit_gap = logit(a0_prob) - logit(b0_prob)`
- `component_prob_dispersion = population_sd([fst_prob,a0_prob,b0_prob])`

## Frozen ablation feature sets
`FST+A0`: A0 fields above excluding raw probability after its logit delta is constructed.  
`FST+B0`: B0 fields above excluding raw probability after its logit delta is constructed.  
`FST+A0+B0`: union of those two sets.  
`PRIMARY_COMPACT_FOOTBALL`: union plus `fst_confidence`, `a0_b0_logit_gap`, and `component_prob_dispersion`.

## Market-aware diagnostic only
Add exactly:
- `market_logit_delta = logit(market_prob) - logit(fst_prob)`;
- `c0_market_margin`;
- `c0_predicted_margin_residual`;
- `c0_market_total`;
- `c0_predicted_total_residual`.

The market diagnostic may not affect the primary football-only disposition.

## Missingness and eligibility
No outcome-dependent row filtering. All required predeclared fields for an arm must be finite. Invalid/missing required fields fail closed for that arm. Exact game identity (`game_id`, season, week, home, away) must agree across sources. Duplicate IDs fail execution.

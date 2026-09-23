# Phase 4 — Robustness Report

## Fixed 2025 diagnostic slices

All slices below were frozen before the holdout. They are descriptive robustness checks, not new selection gates.

### Favorite size

The football-only models do not reveal a stable favorite-size regime that reverses the pooled result. A0 margin MAE is 10.04 for [0,3), 9.53 for [3,7), 12.89 for [7,10), 12.42 for [10,14), and 8.85 for 14+; B0 is 9.23, 9.93, 12.23, 12.04 and 8.69 respectively. The 14+ bucket contains only 10 games and is not treated as a promotion signal. C0 remains closer to the market across these bins, reflecting its market-aware construction rather than a demonstrated standalone football edge.

### Market-total regime

A0 total MAE ranges from 9.97 in 48+ games to 11.55 in the 42–45 bucket. B0 is worse in every broad total regime and remains especially weak in 42–45 (12.52) and below 42 (11.98). C0 M3 stays close to the market baseline, with total MAE 9.68 (<42), 11.06 (42–45), 10.54 (45–48) and 10.09 (48+).

### Season segment

A0 margin MAE is 9.07 in Weeks 1–4, 11.30 in Weeks 5–9, 9.82 in Weeks 10–14 and 11.80 in Weeks 15+. B0 follows a similar late-season degradation, with margin MAE 11.27 in Weeks 15+. C0 M3 remains materially closer to market-like error levels across segments. No segment is used to retune decay, weighting or feature logic.

### Model-market disagreement

The preregistered disagreement slices reinforce the Phase 1 warning that large disagreement is not evidence of edge. For A0, margin MAE rises from 9.17 when disagreement is <2 points to **16.89** in the 8+ bucket (16 games). B0 rises from 9.64 to **17.47** in its 8+ bucket (11 games). These small high-disagreement samples are descriptive, but their direction is inconsistent with using disagreement as a rescue rule.

C0 M3 remains within the <2-point disagreement bin for all 272 rows, which is expected because its residual adjustment is strongly regularized and close to M0. That is not evidence of a separate football signal.

### Realized blowouts — descriptive only

For games with |margin| >=14 (96 games), A0/B0/C0 M3 margin MAE is 19.29 / 18.99 / 17.14. At >=21 (49 games) it is 23.54 / 22.74 / 20.04. At >=28 (20 games) it is 27.59 / 26.67 / 23.95. This confirms that large realized margins remain difficult and that the football-only models do not solve the earlier score-compression/blowout problem.

Because realized blowout membership is postgame information, these rows are never used as a pregame selection gate.

## Development-to-holdout robustness

A0's market-relative weakness persists from 2022–2024 into 2025. B0's total overprediction persists and becomes larger in the holdout (`actual - prediction = -5.49` versus approximately -4.20 in development). C0 remains near the market null in both periods. The most robust finding is therefore negative: none of the three frozen reference candidates establishes a standalone advantage that survives both development and the one-time 2025 holdout.

## Complexity robustness

The simple market, historical-scoring and EPA baselines remain competitive or superior to the more complex football-only candidates on the main continuous targets. B0's additional drive-process simulation does not earn its complexity through point error or proper-score improvement. C0's residual machinery collapses close to M0. These outcomes support the preregistered complexity principle: complexity did not earn standalone survival in Phase 4.

## What remains scientifically valid

A negative standalone result does not make the implementations invalid. A0 and B0 were executed under the frozen chronology/source contract and remain valid underlying representations for downstream research that is separately preregistered. C0 remains a valid market-aware diagnostic/null reference. Their 2025 result is now spent and cannot be reused as an untouched selection sample for a redesigned model.
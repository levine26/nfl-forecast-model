# Phase 1 — Error Decomposition and Failure-Mode Report

**Status:** diagnostic research only  
**Historical universe:** 2022–2025 regular season, 1,087 games unless a narrower slice is explicitly stated  
**Causality warning:** subgroup associations identify where the current model misses; they do not prove the missing feature that caused the miss.

## 1. Highest-confidence failure mode: blowout compression

The margin model is much more accurate in one-score games than in games that become decisive.

| Realized result | Games | Margin MAE | Market spread MAE |
|---|---:|---:|---:|
| One-score, abs margin <= 8 | 600 | **5.313** | 4.923 |
| Non-one-score | 487 | **15.690** | 15.126 |
| Abs margin >= 14 | 362 | **18.227** | 17.552 |
| Abs margin >= 21 | 176 | **22.547** | 21.724 |
| Abs margin >= 28 | 70 | **27.075** | 26.236 |

For realized blowouts, the forecasted winner-oriented margin is extremely conservative:

| Realized threshold | Mean realized abs margin | Mean model margin oriented to actual winner | Mean market margin oriented to actual winner |
|---|---:|---:|---:|
| >=14 | 21.59 | **3.37** | 4.04 |
| >=21 | 26.99 | **4.44** | 5.26 |
| >=28 | 32.50 | **5.43** | 6.26 |

This does **not** mean a pregame model should predict 20–30 point margins whenever a blowout later occurs; much of that realized spread is game noise. It does show that the current conditional mean has difficulty separating games that become highly asymmetric.

### Phase 2 hypotheses

- better opponent-adjusted team strength;
- quarterback/start-state changes;
- offensive-line/pass-rush matchup state;
- pace/possession expectations;
- red-zone/goal-line efficiency;
- explosive-play generation/suppression;
- market-conditioned residual modeling.

## 2. Favorite-size compression

Market-favorite-oriented means show the score regression becomes too conservative when the market sees a large favorite.

| Absolute market favorite size | Games | Market expected favorite margin | Model expected favorite margin | Realized favorite margin | Realized - model |
|---|---:|---:|---:|---:|---:|
| 0–3 | 275 | 1.92 | **0.56** | 1.27 | +0.71 |
| 3–7 | 536 | 4.26 | **3.83** | 5.33 | +1.49 |
| 7–10 | 161 | 7.83 | **7.14** | 7.75 | +0.61 |
| 10–14 | 78 | 11.36 | **9.56** | 13.18 | **+3.62** |
| 14+ | 37 | 14.78 | **11.44** | 15.05 | **+3.62** |

The biggest systematic gap is in double-digit favorite environments.

This is a strong reason to test **market residualization** rather than simply injecting the spread into the same model and calling it improvement. The scientific question is whether football features can predict residual error around the market.

## 3. Total regression toward the middle

The independent total model has very low cross-game prediction variability: SD **1.83** points versus **4.25** for the market total.

Conditional bias by market total:

| Market total | Games | Model total MAE | Market total MAE | Mean actual - model total |
|---|---:|---:|---:|---:|
| <42 | 330 | 11.659 | 10.158 | **-4.84** |
| 42–45 | 308 | 10.018 | 9.685 | -1.74 |
| 45–48 | 243 | 10.496 | 10.292 | +1.82 |
| 48+ | 206 | 11.236 | 10.871 | **+4.32** |

Interpretation:

- low-total games are forecast too high;
- high-total games are forecast too low;
- the model compresses game environments toward a narrow middle.

### Phase 2 hypotheses

- explicit pace / expected-play model;
- offensive and defensive scoring components rather than one direct total;
- QB/start-state effects;
- red-zone and explosive-play rates;
- special-teams/scoring-position effects;
- weather/roof where PIT-valid;
- market total residual modeling.

## 4. Large model-market disagreement is not a validated edge

Current margin disagreement forensics:

| Absolute model-market gap | Games | Model margin MAE | Market MAE | Model closer rate |
|---|---:|---:|---:|---:|
| <2 | 525 | 9.444 | 9.294 | 42.9% |
| 2–4 | 348 | 9.757 | 9.343 | 43.1% |
| 4–6 | 141 | 11.520 | 10.543 | 39.7% |
| 6–8 | 43 | 11.124 | 9.570 | 37.2% |
| 8+ | 30 | 12.418 | 9.717 | 36.7% |

For the preregistered >=6 point gap slice:

- games = 73;
- model minus market MAE = **+2.026 points**;
- season+week block-bootstrap 95% interval = **+0.130 to +3.678**;
- bootstrap probability the model is better = **1.7%**.

Therefore Phase 1 rejects the heuristic “bigger LevLine-market disagreement means stronger model edge.”

The high-gap ATS hit rates in the tiny 6–8 and 8+ groups are not sufficient to override the paired continuous-error evidence.

## 5. Season and schedule-segment stability

### By season

Margin MAE:

- 2022: 9.08;
- 2023: 10.55;
- 2024: 9.98;
- 2025: 10.24.

Total MAE:

- 2022: 11.38;
- 2023: 10.91;
- 2024: 10.01;
- 2025: 11.12.

No single season explains the overall failure. The total regression improved in 2024 but deteriorated again in 2025.

### By season segment

| Segment | Games | Margin MAE | Total MAE |
|---|---:|---:|---:|
| Weeks 1–4 | 256 | 9.986 | 10.801 |
| Weeks 5–9 | 289 | 10.201 | 10.245 |
| Weeks 10–14 | 287 | **9.226** | 10.554 |
| Weeks 15+ | 255 | **10.495** | **11.935** |

Late-season totals are the weakest schedule segment in this audit. Early-season margin is not uniquely bad, although offseason roster/staff change may still be hidden inside specific teams.

## 6. Rest asymmetry

| Rest condition | Games | Margin MAE | Total MAE |
|---|---:|---:|---:|
| Home rest advantage >=3 days | 114 | **8.188** | 10.224 |
| Home rest disadvantage >=3 days | 120 | 10.193 | 10.704 |
| Rest difference within 2 days | 853 | 10.167 | 10.959 |

The existing rest feature appears directionally useful; large home rest advantage is associated with lower margin error. This slice does not establish whether the current linear rest differential is optimally specified.

## 7. Team-level scoring residuals

Across 2022–2025, team-specific offense/defense point errors show persistent-looking residual patterns. These are hypothesis generators because team identity spans coaching/QB/personnel regime changes.

Examples:

### Offensive points underpredicted most on average

- DET: actual scoring exceeded projection by about **4.26 points/game**; offense-points MAE 9.56.
- DAL: +2.10.
- BUF: +1.98.
- CIN: +1.52.

### Offensive points overpredicted most on average

- TEN: actual scoring about **3.52 points/game below** projection.
- NYJ: -2.51.
- KC: -2.40.
- PIT: -2.33.
- LV: -2.24.
- CLE: -2.11.

### Defensive points allowed residual examples

Model underpredicted points allowed most for:

- DAL: +2.30 actual points allowed versus prediction;
- CIN: +2.01;
- IND: +1.90;
- WAS: +1.72;
- ARI: +1.65.

Model overpredicted points allowed most for:

- DEN: -2.52;
- PIT: -2.38;
- HOU: -2.29;
- NE: -2.04.

A future model should not encode these as team-name corrections. The useful question is which QB, personnel, scheme, pace, red-zone, or matchup variables explain them prospectively.

## 8. 2025 qualified availability slice

Only 2025 currently has a qualified historical practice-state reconstruction suitable for this diagnostic.

Definition:

- final practice state proven known by T-120;
- DNP or limited;
- excludes "not injury related - resting player";
- no hindsight inactive status or actual snaps.

### QB practice limitation

Games with at least one qualified non-rest QB DNP/limited row:

- flagged games in score baseline: 78;
- margin MAE: **11.15**;
- other 2025 games: **9.88**;
- descriptive difference: **+1.27 points**;
- ordinary game-bootstrap 95% interval: approximately **-0.94 to +3.53**.

### Offensive-line practice limitation

Games with at least one qualified non-rest OL DNP/limited row:

- flagged games: 217;
- margin MAE: **10.49**;
- other 2025 games: **9.24**;
- descriptive difference: **+1.25 points**;
- ordinary game-bootstrap 95% interval: approximately **-1.30 to +3.67**.

These are **suggestive but not decisive**. The confidence intervals cross zero, the sample is one season, and "limited/DNP on the final practice report" is not equivalent to actual absence or replacement quality.

The correct Phase 2 response is a PIT-safe availability hypothesis—not an injury point adjustment.

## 9. QB-specific existing research

The repository already tested leakage-controlled lagged QB quality/continuity features for winner probability research.

Relevant reuse:

- QB-aware PURE alone did not improve winner accuracy over the production-compatible PURE baseline in the v0.8 artifact;
- the combined opponent-adjusted + QB-aware family showed some small improvements in selected blended probability candidates;
- no promotion was authorized;
- that research optimized winner probability, not score/margin/total accuracy.

Phase 1 therefore does **not** conclude that QB state is unimportant to score forecasting. It concludes that prior QB evidence is mixed and must be retested against score residuals with a stricter historical starter-as-of contract.

## 10. Realized process diagnostics

Postgame PBP variables were correlated with absolute errors strictly as diagnostics, never as features.

In the first reproducible Phase 1 artifact:

- realized offensive-play count correlation with abs margin error: -0.218;
- realized possessions proxy correlation with abs total error: +0.112;
- realized turnovers correlation with abs margin error: +0.067;
- explosive-play rate, sacks, QB hits, mean EPA, and success rate had only small simple correlations with absolute error.

These weak unconditional correlations do **not** mean pace, turnovers, red-zone state, or explosiveness lack forecast value. Realized outcomes are noisy, and the relevant future question is whether **pregame expectations** of those processes add OOS information.

## 11. Probability-margin coherence

The chronology-clean historical F-ST analogue and the independent football margin disagree on winner direction in **18.4%** of games.

That split is not automatically an error because the two systems optimize different objects. It does create a product/model-governance problem if they are described as a single forecast.

Phase 2 should compare:

- independent football score distribution;
- market-conditioned probability;
- probability-implied fair margin;
- market-residual score challenger

under one explicit joint evaluation.

## 12. Dimensions not yet safely testable across 2022–2025

Phase 1 intentionally does **not** manufacture subgroup labels for:

- QB transition at a fixed historical T-minus horizon;
- confirmed inactives;
- offensive-line starter continuity before 2025;
- travel/time-zone state not already captured by schedule/rest;
- pregame weather forecasts;
- pregame news state;
- coaching-change state at a frozen decision time;
- exact special-teams roster quality.

Those require source/PIT work before causal claims.

## 13. Ranked Phase 2 hypotheses from Phase 1 evidence

This is a research priority ordering, not a model ranking or promotion decision.

1. **Market residualization for margin and total** — market is the strongest baseline and large disagreements currently degrade.
2. **Decompress total environment** — direct total predictions regress aggressively toward the middle.
3. **Decompress large-favorite / asymmetric matchups** — current football margin is too conservative in large-favorite regimes.
4. **Opponent-adjusted football strength** — reuse existing prior work under score targets.
5. **Pace/possession and scoring-process decomposition** — plays, drives, red zone, explosive scoring, special teams.
6. **PIT-safe QB/start-state layer** — quality, experience, continuity, replacement delta.
7. **PIT-safe OL/personnel/availability layer** — especially where pregame uncertainty is material.
8. **Roof/weather and late-season context** — only after capture/reconstruction is qualified.
9. **Stacking simplification / proper nesting** — current equal-ish inverse-MAE blend does not beat the best base regressor.
10. **Joint distribution/coherence** — one score distribution should explain winner, margin, total, cover, and O/U consistently.

## 14. Phase 1 error conclusion

The score model's most defensible failure description is:

> **LevLine's independent score regression is a stable but compressed team-strength model. It captures enough signal to achieve roughly 10-point margin MAE, but it under-differentiates extreme game environments, does not beat the historical market on margin or total, and currently lacks several PIT-safe game-specific state variables that could explain residuals.**

That conclusion is strong enough to design Phase 2 research without changing production.

## Appendix A — structural slices completed on exact-head Phase 1 audit

These diagnostics were generated by `run_structural_slices.py`. They are descriptive hypothesis screens, not model-selection tests.

### Pregame pace proxy

Definition: sum of each team's mean offensive plays over its prior five completed regular-season games.

- simple correlation with absolute margin error: **0.003**;
- simple correlation with absolute total error: **-0.030**;
- slowest quartile: margin MAE 10.134, total MAE 11.393;
- fastest quartile: margin MAE 10.382, total MAE 10.529.

There is no strong monotonic error gradient in this simple pace proxy. This does **not** reject possession/drive modeling; it rejects the idea that a crude prior-five play-count split alone explains the residual problem.

### Recent-form screens

For EWMA home-minus-away differences in offense EPA, pass EPA, rush EPA, success rate and win rate, simple correlations with absolute margin/total error were small (absolute values generally below 0.10). Quartile errors were non-monotonic.

Phase 2 should therefore not justify a challenger by merely adding more of the same unadjusted recent-form transforms. Opponent adjustment, state-space structure or process decomposition must supply the scientific rationale.

### Core feature missingness

Across all 1,087 audited rows:

- Core feature count: 44;
- mean missing feature count before model imputation: **0.0**;
- maximum missing feature count: **0**.

Therefore baseline error on this universe is not explained by missing Core fields or median-imputation frequency.

### Observed roof/weather association — descriptive only

Schedule-recorded weather metadata are not proven historical forecast snapshots and are **not PIT-safe model inputs**.

Observed roof state:

- enclosed: margin MAE 9.953, total MAE 10.638;
- open air/open roof: margin MAE 9.966, total MAE 10.957.

Observed 20+ mph wind has total MAE 16.015, but only **11 games** and uses observed metadata rather than a decision-time forecast. It is hypothesis-generating only.

The weather conclusion is therefore a source/chronology conclusion, not a claim that weather is or is not predictive.

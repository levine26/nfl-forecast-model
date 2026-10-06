# LevLine 2026 Week 4 Performance Audit

**Audit type:** research / diagnostic only  
**Production changes authorized:** no  
**Production model:** F-ST-01-FROZEN-2026  
**Main snapshot audited:** `723ba40f908b3b11325a5f47ad2b788b1474b5b3`  
**Official accountability sample:** immutable `LOCKED` forecasts only. `RECOVERED_MISSED_LOCK` rows are excluded from the headline record.  
**Monday Night Football grading note:** ATL 45, NO 24 was externally verified after the repository's prediction-history row had not yet been graded. The locked pregame row itself was not altered for this audit.

## Executive finding

The two-week slump is real, but the evidence does **not** indicate a production corruption, model swap, fallback event, or broad collapse of the underlying margin engine.

Weeks 3-4 contain an unusually unfavorable cluster of winner outcomes relative to LevLine's own locked probabilities. On the 31 immutable official locks across those two weeks, F-ST went **15-16 (48.4%)** despite **20.06 expected wins** from its own locked pick probabilities. A Poisson-binomial calculation gives approximately **4.18%** probability of observing 15 or fewer wins under those game-level probabilities. That is notable adverse variance, but not by itself sufficient evidence of a regime break.

The main architectural fact is that F-ST is intentionally market-heavy. The frozen final stack has market-logit coefficient **+1.1939087** and nested-PURE coefficient **-0.1934275**. Historically, F-ST's winner edge came almost entirely from selective near-50/50 decision-boundary flips rather than from routinely opposing the sportsbook favorite. Therefore, when market favorites are upset in clusters, F-ST is expected to suffer with the market.

## Official forward record

| Period | F-ST record | Accuracy | Expected wins | Wins minus expectation |
|---|---:|---:|---:|---:|
| Weeks 1-2 | 24-8 | 75.0% | 21.289 | +2.711 |
| Weeks 3-4 | 15-16 | 48.4% | 20.061 | -5.061 |
| Weeks 1-4 | 39-24 | 61.9% | 41.351 | -2.351 |

The first two weeks ran materially above expectation, and the next two ran materially below expectation. The full-season deficit versus expected wins is much smaller than the two-week slump makes it appear.

## F-ST versus market

Across all 63 official locks:

- F-ST: **39-24 (61.9%)**
- Market side: **39-24 (61.9%)**
- F-ST Brier: **0.23159**
- Market Brier: **0.23013**
- F-ST log loss: **0.65632**
- Market log loss: **0.65270**

Across Weeks 3-4:

- F-ST: **15-16**
- Market: **16-15**
- Both correct: **15**
- Both wrong: **15**
- F-ST-only correct: **0**
- Market-only correct: **1**
- F-ST/market side agreement: **96.8%**

The one net winner lost to the market during the slump was a boundary switch, not a broad disagreement pattern.

This 2026 side-agreement rate is consistent with the historical F-ST design. The frozen historical audit had only 25 F-ST/market pick disagreements in 1,087 games (2.30%); the chronology-clean version had 34/1,087 (3.13%). The 2026 rate is 2/63 (3.17%).

## Important correction to the preliminary diagnostic

A preliminary check suggested that F-ST/market probability separation had collapsed. That was caused by inconsistent historical population of the diagnostic `fst_vs_market_delta` field in older prediction-history rows.

Using the actual locked `final_home_prob - market_home_prob` directly:

- Weeks 1-2 mean absolute F-ST/market separation: **1.50 percentage points**
- Weeks 3-4: **1.92 percentage points**

There is therefore **no evidence of a new market-convergence implementation bug**.

The football-only signals did move closer to the market:

- nested-PURE vs market absolute gap: **11.72 pp -> 6.48 pp**
- legacy-PURE vs market absolute gap: **11.52 pp -> 6.68 pp**

But base-model disagreement remained essentially unchanged (**3.96% -> 3.99%**) and mean ATS edge magnitude remained stable (**2.32 -> 2.46 points**). This looks like output-level convergence, not a broad model-instability signature.

## Confidence calibration

### Weeks 3-4

| Bucket | Record | Accuracy | Mean locked pick probability |
|---|---:|---:|---:|
| High | 7-2 | 77.8% | 77.7% |
| Lean | 3-2 | 60.0% | 57.7% |
| Solid | 4-5 | 44.4% | 65.4% |
| Coin Flip | 1-7 | 12.5% | 53.7% |

The high-confidence bucket did **not** collapse. The damage was concentrated in the low-to-mid confidence buckets, especially Coin Flip. This is important: the recent headline record looks worse than the performance of the strongest signals.

Across all 63 official locks, Coin Flip is 5-8 and High is 12-6. The sample is still too small to redefine confidence thresholds from 2026 outcomes.

## Football-only counterfactuals

These are diagnostics only. They are **not** promotion evidence and must not be used for post-hoc production switching.

### Weeks 3-4

| Signal | Record |
|---|---:|
| F-ST | 15-16 |
| Market | 16-15 |
| F-ST nested PURE | 20-11 |
| Legacy PURE | 19-12 |
| Logistic | 19-12 |
| Extra Trees | 19-12 |
| XGBoost | 21-10 |
| CatBoost | 20-11 |
| Elo | 20-11 |

However, the same football-only signals were substantially worse in Weeks 1-2. Over all 63 official locks:

- F-ST: **39-24**
- Market: **39-24**
- XGBoost: **39-24**
- Elo: **40-23**
- F-ST nested PURE: **38-25**
- Legacy PURE: **37-26**

So the last two weeks do **not** justify replacing F-ST with a football-only model. They do support the already-preregistered LevLine 4 hypothesis that football components may be useful as a **selective residual/switch signal** when corroborated by independent contemporaneous evidence.

## ATS / margin engine

The winner slump did not coincide with a comparable margin collapse.

Across Weeks 3-4:

- Graded ATS picks: **17-10-3**
- ATS win rate excluding pushes: **63.0%**
- Model margin MAE: **7.60 points**
- Market spread MAE: **7.66 points**

Week 4 specifically:

- ATS: **8-5-2**
- Model margin MAE: **6.44**
- Market spread MAE: **6.90**

This is consistent with the view that binary winner classification was hit harder than the independent expected-margin signal.

## Largest team-level residuals, Weeks 3-4

Two games per team only; these are diagnostic flags, not stable team priors.

| Team | Mean margin residual vs LevLine |
|---|---:|
| ATL | +23.6 |
| NO | -16.6 |
| JAX | +14.4 |
| PHI | -12.0 |
| GB | -11.7 |
| CHI | +10.9 |
| NE | -9.2 |
| SEA | -8.0 |

Atlanta is the clearest short-run miss: LevLine materially underestimated ATL in both Weeks 3 and 4. New Orleans was correspondingly overestimated in the same recent window. Two observations are not enough to create a team-specific correction.

## Pipeline / integrity audit

No evidence was found that the slump was caused by a production implementation change:

- Weeks 2-4 used `F-ST-01-FROZEN-2026`
- training digest remained `6a26713b...`
- freeze implementation SHA remained `59830d23...`
- zero F-ST fallbacks in the official sample
- Week 3 had normal immutable locks
- Week 4 had one `RECOVERED_MISSED_LOCK` game; it is excluded from the official headline audit and was not the cause of the slump
- movement attribution showed no material pregame probability movement for almost all Week 3-4 games; ATL-NO moved only about 0.52 pp in final probability, driven by market movement

The repository does not currently persist a true closing snapshot for every game, so a rigorous CLV/closing-line audit cannot be reconstructed honestly from the current artifacts. Future research should persist closing consensus explicitly rather than infer it retrospectively.

## Architectural interpretation

The current production F-ST formula is:

`logit(p_final) = intercept + 1.1939 * logit(p_market) - 0.1934 * logit(p_nested_pure)`

Historical research already established:

- frozen final-coefficient F-ST: 740/1087, **68.08%**
- market: 735/1087, **67.62%**
- chronology-clean F-ST architecture: 741/1087, **68.17%**
- paired uncertainty did **not** establish a statistically certain winner-accuracy advantage
- historical F-ST gains occurred at the near-coinflip boundary
- outside the boundary, F-ST and market selected the same winner

The current 2026 behavior is therefore consistent with the registered architecture. The model is behaving like the model that was approved; the question is whether that architecture will continue to add enough residual value prospectively.

## Decision

**Do not change production F-ST based on Weeks 3-4.**

The scientifically valid response is:

1. preserve F-ST as the immutable benchmark;
2. keep the existing LevLine 4 prospective selective-upset / component-residual research running;
3. evaluate challenger switches only under the pre-existing prospective contracts;
4. treat Coin Flip winner calls as low-actionability in presentation, while still preserving the official pick and accountability record;
5. add a prospective raw-feature/output drift monitor and explicit closing-market snapshot capture, without tuning thresholds from these outcomes;
6. continue team-level residual monitoring, but do not create team-specific corrections from a two-game pattern.

The existing LevLine 4 research program is already aimed at the right weakness: a market-first incumbent with a selective, independently corroborated football-information correction rather than a wholesale move away from the market.

## Sources inside the repository

- `outputs/prediction_history.csv`
- `outputs/history_scoreboard.json`
- `outputs/movement_attribution.csv`
- `outputs/market_t120_research.csv`
- `src/nfl_forecast/fst_production.py`
- `src/nfl_forecast/pipeline.py`
- `research/levline3_fst_market_accuracy_audit_v1.json`
- `research/levline3_boundary_accuracy_audit_v1.json`
- `research/levline4_conditional_market_reliance_audit_v1.json`
- `research/levline4_component_resolved_upset_audit_v1.json`
- `research/levline4_accuracy_primary_contract_v1.json`
- `research/levline4_selective_upset_monitor_contract_v1.json`

External grading verification used only for the still-ungraded ATL-NO result:
- Reuters, Oct. 5/6, 2026: Atlanta 45, New Orleans 24
- NewOrleansSaints.com Week 4 game recap: Atlanta 45, New Orleans 24

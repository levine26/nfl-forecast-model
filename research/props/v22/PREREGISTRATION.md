# LevLine Props 2.2 — Market-Residual & Calibration Challenger Preregistration

Status: FROZEN DESIGN BEFORE FUTURE-HOLDOUT FORECAST CAPTURE
Research-only: yes
Production authorization: no
Baseline: frozen Props 2.1 (levline-props-2.1-sunday-v0.1)
Motivation source: Week 2 prospective evaluation diagnosis only. Week 2 outcomes may not be used to fit, select, or validate a Props 2.2 winner.

## 1. Scientific objective

Determine whether LevLine contains incremental player-prop information beyond the sportsbook market after correcting two prospectively observed failure modes: overconfident probabilities and raw Fair Lines that underperformed the contemporaneous market on the matched Week 2 cohort.

The forward-looking question is whether the residual disagreement between LevLine and the sportsbook contains predictive information when the market is treated as a strong prior rather than something to replace.

## 2. Contamination boundary

Prohibited: fitting coefficients to Week 2 outcomes; choosing a challenger after looking at Week 2 counterfactual performance; changing candidate weights after any future-holdout outcome is observed; rewriting frozen Props 2.1 receipts; changing official LevLine/F-ST winner-model code; using post-kickoff market data; or selecting only favorable prop families after outcome inspection.

## 3. Frozen challenger grid

Let M be Props 2.1 Fair Line, L the contemporaneous sportsbook consensus line, p the Props 2.1 model probability for the evaluated side, and q the sportsbook no-vig probability when available.

### P21_BASE
Line = M. Probability = p. This is the unchanged prospective control.

### P22_RESIDUAL_25
Line = L + 0.25 × (M − L). Probability = p.

### P22_RESIDUAL_50
Line = L + 0.50 × (M − L). Probability = p.

### P22_CAL_50
Line = M. Probability = 0.5 + 0.50 × (p − 0.5).

### P22_RESIDUAL50_CAL50
Line = L + 0.50 × (M − L). Probability = 0.5 + 0.50 × (p − 0.5).

Where q exists, also preserve p − q and M − L as diagnostic residuals. These residuals are not separately promoted models.

## 4. Why these weights are admissible

The coefficients are simple prespecified fractions (0.25 and 0.50), not fitted to Week 2 errors. No coefficient is selected because it would have performed best retrospectively on Week 2. All candidates stay active through the required future holdout.

## 5. Prospective capture requirements

Every challenger receipt must preserve challenger ID, frozen coefficients, source Props 2.1 forecast ID, player/game/prop identity, model Fair Line/probability, sportsbook line/no-vig probability when available, provider/book count, market capture time, forecast time, data horizon, kickoff, role/availability/depth-chart state, research-only flags, and immutable receipt hash.

Chronology must prove market/data horizon <= forecast time < kickoff. Missing required market information makes the market-anchored challenger unavailable for that observation; it must not be backfilled.

## 6. Primary future-holdout metrics

Projection accuracy: MAE, paired absolute-error difference versus the original sportsbook line, and game-clustered bootstrap confidence interval.

Probability accuracy: Brier score, log loss, paired difference versus sportsbook no-vig probability, and game-clustered confidence interval.

Calibration: fixed probability bins, expected calibration error, and calibration intercept/slope when sample size permits.

Incremental residual signal: for continuous markets, regress outcome residual (actual − L) on model residual (M − L), with game-clustered uncertainty. Also report residual sign agreement and descriptive Pearson/Spearman association.

## 7. Secondary decompositions

Predeclared prop-family strata: QB passing yards, QB rushing yards, RB rushing yards, RB receiving yards, receptions, WR/TE receiving yards, passing TDs, and rushing/receiving/anytime TDs where probability semantics are compatible.

Also report book-count, stable-versus-uncertain role state, player availability state, and market-capture-horizon strata. These remain diagnostic unless minimum sample rules are met.

## 8. Minimum evidence thresholds

Per-week reports are descriptive only. No promotion/model-selection claim before at least 3 future weeks, 30 finalized games, 1,000 market-matched observations, 250 observations for any prop-family superiority claim, game-clustered uncertainty, and no unresolved chronology/receipt-integrity violations.

If thresholds are not met, continue prospective accumulation without changing the grid.

## 9. Selection rule

After minimum future-holdout evidence is reached, compare every challenger against both the original sportsbook market and P21_BASE. Require supported projection or probability improvement, non-degraded calibration, and clean chronology/governance. Document losing candidates as well as winners.

If no candidate shows credible incremental value, keep Props in research status and do not promote.

## 10. ROI boundary

ROI is secondary and valid only for prospectively frozen signal decisions with captured executable prices. No retrospective threshold selection, no backfilled prices, and no using later market movement as if known at forecast time.

## 11. Opportunity vs efficiency attribution

Preserve enough future-holdout decomposition to attribute central-estimate error to opportunity/volume, efficiency per opportunity, availability/role misses, and market disagreement. This is diagnostic and may not mutate the grid mid-holdout.

## 12. Promotion firewall

Props 2.2 remains isolated research. It may not modify official LevLine/F-ST probabilities, winner-model features/weights, official pick locks, grading, existing frozen Props 2.1 receipts, or production labels implying verified market superiority.
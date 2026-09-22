# LevLine Props 2.2 — Market-Residual Future-Holdout Preregistration

Status: **FROZEN DESIGN BEFORE FUTURE-HOLDOUT FORECAST CAPTURE**  
Research-only: yes  
Production authorization: no  
Baseline: `levline-props-2.1-sunday-v0.1`

Week 2 is diagnosis-only. Its outcomes may motivate the scientific question, but they may not fit coefficients, select a candidate, determine a prop-family exclusion, or validate a Props 2.2 winner.

## 1. Scientific objective

Determine whether LevLine contains incremental player-prop information beyond the sportsbook market after the frozen Props 2.1 Week 2 cohort showed two prospective failure modes: raw Fair Lines underperformed contemporaneous market lines and model probabilities were overconfident / inferior on Brier and log loss.

The market is therefore treated as a strong point-in-time prior. The forward question is whether the residual disagreement between LevLine and the market contains predictive information.

## 2. Contamination boundary

Before any future-holdout outcome is observed, the candidate grid, weights, eligibility rules, metrics, multiplicity rule and minimum evidence are frozen.

Prohibited:
- fitting any coefficient to Week 2 outcomes;
- testing counterfactual Week 2 candidate performance to choose weights;
- changing the grid after any future-holdout outcome is known;
- rewriting frozen Props 2.1 receipts;
- post-kickoff market use;
- retrospective signal relabeling or threshold search;
- selecting favorable prop families after outcome inspection;
- changing official LevLine/F-ST winner-model code.

## 3. Definitions

For an eligible point-in-time market observation:

- `M` = Props 2.1 Fair Line.
- `L` = contemporaneous sportsbook consensus line captured before forecast/kickoff.
- `p` = Props 2.1 probability for the evaluated side.
- `q` = sportsbook no-vig probability for the same side, when available.

A residual line blend is `L + w(M-L)`.  
A residual probability blend is `q + w(p-q)`.

If the required market quantity is missing at the allowed horizon, the corresponding market-anchored challenger is unavailable for that observation. It may not be backfilled.

## 4. Frozen candidate grid

### Control

**P21_BASE**  
Line = `M`. Probability = `p`.

### Mechanism ablations — descriptive only, not promotion eligible

**P22_LINE_RESIDUAL_25**  
Line = `L + 0.25(M-L)`. Probability = `p`.

**P22_LINE_RESIDUAL_50**  
Line = `L + 0.50(M-L)`. Probability = `p`.

**P22_PROB_RESIDUAL_25**  
Line = `M`. Probability = `q + 0.25(p-q)`.

**P22_PROB_RESIDUAL_50**  
Line = `M`. Probability = `q + 0.50(p-q)`.

**P22_CAL_50**  
Line = `M`. Probability = `0.5 + 0.50(p-0.5)`.

These ablations diagnose whether any improvement comes from line anchoring, probability anchoring, or generic de-overconfidence. They cannot be promoted as a selected winner from this grid.

### Primary promotion-eligible challengers

**P22_COMBINED_25**  
Line = `L + 0.25(M-L)`. Probability = `q + 0.25(p-q)`.

**P22_COMBINED_50**  
Line = `L + 0.50(M-L)`. Probability = `q + 0.50(p-q)`.

The fractions 0.25 and 0.50 are simple prespecified shrinkage strengths, not fitted to Week 2 outcomes. Both remain active through the entire required future holdout.

## 5. Prospective capture requirements

Each challenger receipt must preserve:

- challenger ID and frozen coefficient contract;
- source Props 2.1 forecast ID and immutable source hash;
- game/player/prop identity;
- source model Fair Line and probability;
- sportsbook line and no-vig probability used by the challenger;
- provider/book count and dispersion when available;
- market capture timestamp, forecast timestamp, data horizon and kickoff;
- role/availability/depth-chart state;
- research-only / production-ineligible flags;
- immutable challenger receipt hash.

Chronology must prove market/data horizon <= forecast time < kickoff.

## 6. Primary future-holdout metrics

For line markets:

- MAE;
- paired absolute-error difference vs the original point-in-time sportsbook line;
- game-clustered confidence interval.

For probability markets:

- Brier score;
- log loss;
- paired differences vs sportsbook no-vig probability;
- game-clustered confidence intervals.

Calibration:

- fixed probability bins;
- ECE;
- calibration intercept/slope when sample size permits.

Incremental residual signal:

- regress `actual - L` on `M - L` with game-clustered uncertainty;
- residual sign agreement;
- descriptive Pearson and Spearman association.

The original point-in-time sportsbook market remains the required comparator. Beating P21_BASE alone is insufficient.

## 7. Multiplicity and selection control

Only `P22_COMBINED_25` and `P22_COMBINED_50` are promotion-eligible.

At the prespecified terminal evaluation, primary market-relative comparisons across these two candidates use **Holm-Bonferroni control at family alpha 0.05**. Losing candidates remain reported.

A promotion claim additionally requires:
- no degradation on both Brier and log loss for the probability component;
- clean chronology and receipt integrity;
- no material calibration deterioration;
- minimum sample thresholds below.

Mechanism ablations are explanatory only and cannot become the promoted winner based on this holdout.

If neither primary challenger shows credible incremental value beyond the market, Props remains research-only.

## 8. Minimum evidence

No promotion/model-selection claim before all of:

- at least 3 future weeks;
- at least 30 finalized games;
- at least 1,000 market-matched observations;
- at least 250 observations for any prop-family superiority claim;
- game-clustered uncertainty;
- no unresolved chronology or receipt-integrity violation.

Per-week reports are descriptive only.

## 9. Predeclared decompositions

Report, without post-hoc selection:

- QB passing yards;
- QB rushing yards;
- RB rushing yards;
- RB receiving yards;
- receptions;
- WR/TE receiving yards;
- passing TDs;
- rushing/receiving/anytime TDs where probability semantics are compatible;
- book-count/liquidity;
- stable vs uncertain role state;
- availability state;
- market-capture horizon.

A subgroup result does not authorize a subgroup-specific production rule unless it meets the minimum sample requirement and is separately prospectively validated.

## 10. ROI boundary

ROI is secondary and valid only for prospectively frozen signal decisions with captured executable prices. No retrospective threshold selection, no backfilled prices, and no treating later market movement as available at forecast time.

## 11. Promotion firewall

Props 2.2 remains isolated research. It may not modify official LevLine/F-ST probabilities, winner-model features/weights, official pick locks, grading, existing frozen Props 2.1 receipts, or production labels implying verified market superiority.

# LevLine 4.0 — Final Research Recommendation

Status: **architecture conclusion / research-only / no production promotion authorization**  
Date: **2026-09-12**

This document is a synthesis, not a rewrite of the preregistration. The frozen production model `F-ST-01-FROZEN-2026` remains unchanged. No completed 2026 outcome was used to invent, tune, rescue, or select a LevLine 4 candidate in reaching this architecture conclusion.

## 1. Final conclusion

LevLine 4 should **not** be a larger football-first model.

The highest-evidence architecture is a point-in-time market-first forecasting system whose principal research question is **when the NFL market is most informative**, followed by narrowly gated tests of whether LevLine adds residual information that the same-horizon market has not already incorporated.

The recommended probability path is:

`strict-PIT multi-book market consensus at horizon h`

then, **only when prospectively additive**,

`+ sparse same-horizon residual information`

then, **only when independently justified**,

`+ conservative calibration`.

The raw market is allowed to remain the final probability if no proprietary transform beats it on proper scoring rules. LevLine should prefer an honest strong benchmark to a branded degradation.

The architecture question is therefore sufficiently resolved. What is **not** resolved is the empirical promotion question: no T-120/T-60/T-45/T-30 winner may be declared before the prospective gate and family-level inference are satisfied.

## 2. Production remains frozen

`F-ST-01-FROZEN-2026` remains the immutable production/accountability forecast at T-120. Its coefficients, training digest, historical locks, Sunday Signal behavior, grading, and rollback boundary are not modified by LevLine 4 research.

LevLine 4 operates as a shadow program. It may grade completed games but may not rewrite official historical locks or silently replace production.

## 3. The canonical horizon experiment

The primary timing family is:

- raw market T-120;
- raw market T-60;
- raw market T-45;
- raw market T-30.

All four must use the **same market-construction definition** for the primary timing comparison. This isolates the value of waiting from the value of changing the model.

### Strict information-set rule

A nominal T-X forecast is an information cutoff, not a symmetric timing window.

A qualified observation may be captured at or before the T-X cutoff within the preregistered early tolerance. An observation captured after the cutoff is later information and is ineligible for the nominal horizon even if it is only seconds late.

Accordingly:

- valid timing error is `[-7.5, 0]` minutes;
- positive timing error is excluded from canonical grading;
- missing timing provenance fails closed;
- a missed horizon remains missing;
- T-30 cannot backfill T-45;
- closing prices cannot reconstruct T-60/T-45/T-30;
- later inactive states cannot reconstruct earlier player state;
- post-kickoff information is prohibited.

Actual request timestamp and timing error remain part of provenance. The horizon label should therefore be interpreted as an **as-of cutoff** with exact timing retained, not as a claim that every request occurred at the identical second.

### Primary sample

The canonical timing comparison uses the complete-case intersection of games having strict-PIT valid forecasts at all four horizons. Larger pairwise samples are sensitivity analyses only.

Capture completeness is reported separately so an apparently strong complete-case result cannot hide selective data loss. No imputation is permitted.

## 4. Horizon selection rule

The minimum 200-game / 14-NFL-week gate is **eligibility for formal inference**, not permission to choose the lowest observed Brier score.

The four raw market horizons are one forecast-comparison family. The frozen inference contract requires:

- Brier score as the primary loss;
- 95% Model Confidence Set logic across T-120/T-60/T-45/T-30;
- 10,000 week-block bootstrap draws preserving within-week dependence;
- log loss and calibration as corroboration;
- leave-one-week-out stability diagnostics;
- explicit capture-completeness/source-integrity review.

A later horizon may replace T-120 only if T-120 is excluded from the 95% confidence set, a later horizon survives, the paired Brier improvement versus T-120 has a week-block 95% upper bound below zero, and the secondary diagnostics do not materially contradict the conclusion.

If multiple later horizons remain statistically indistinguishable, select the **earliest surviving later horizon** that meets all product/integrity requirements. This maximizes retry, validation, and publication margin without pretending the data distinguish T-60 from T-45 or T-30 when they do not.

T-45 remains an operationally attractive hypothesis because it follows the game-day inactive information event while retaining more operational buffer than T-30. It is **not** a selected statistical winner.

## 5. Market construction

The current baseline is robust multi-book consensus with book-level provenance and median aggregation in logit space.

The de-vig family is frozen separately as:

- `L4-MKT-DEVIG-PROP-V1` — proportional normalization;
- `L4-MKT-DEVIG-SHIN2-V1` — two-outcome Shin/additive equivalent;
- `L4-MKT-DEVIG-POWER-V1` — power transform.

A key final finding is that for a **two-outcome** NFL moneyline, Shin is algebraically equivalent to additive margin removal. It is therefore not an independent insider-information model in this setting and its fitted parameter must not be interpreted as a measurement of hidden player news or “smart money.”

De-vig and consensus choices are a separate candidate family from horizon selection. No method is assumed superior from cross-sport evidence alone.

A temporal line-movement correction is scientifically worth shadowing because published NFL evidence reports significant negative autocorrelation in pregame moneyline changes. But that evidence does not identify a Brier-optimal fade coefficient. Any movement/shrinkage model therefore requires its own frozen candidate ID and either genuinely prior fitting data or a fresh prospective evaluation start.

## 6. Player state

Player availability is **not a prerequisite for LevLine 4.0 promotion**.

The 2025 historical source-coverage blocker has been technically resolved, and the repository now prospectively archives richer official NFL inactive/news evidence around the T-90 event. However, the multi-season player probability feature remains unauthorized because one unified 2022–2025 chronology/identity/missingness/status-normalization contract has not yet passed.

This is the correct fail-closed state.

If the player lane later qualifies, the appropriate estimand is not “how many points is this player worth?” It is:

> Does point-in-time player/role state improve win-probability proper scores **conditional on the contemporaneous same-horizon market and its response to the information release?**

The recommended player model is therefore a small regularized market-offset residual. It may use as-of availability, modeled role share, replacement burden, lineup value lost/gained, uncertainty, market movement, and time since the official status observation. It may not use current-game realized snaps, later inactive information, post-kickoff participation, or postgame value.

If historical harmonization is not complete before a player candidate is frozen, the player feature waits for a later prospective candidate cycle rather than being retrofitted into LevLine 4 using already-seen 2026 outcomes.

## 7. Dynamic team strength

Dynamic latent strength remains a **diagnostic/challenger lane**, not part of the core LevLine 4 probability backbone.

The statistical literature supports dynamic Bradley–Terry/state-space modeling, and recent work supports adaptive innovation variance capable of reacting to abrupt roster/regime changes. That establishes methodological plausibility, not incremental NFL value beyond the betting market.

LevLine's own historical research has repeatedly found that plausible football-rich states either fail to establish incremental gain or remain materially worse than raw market probability. Therefore any future dynamic-strength candidate must enter as a same-horizon residual and beat the contemporaneous market on paired Brier before receiving weight.

If revisited, the preferred form is adaptive state evolution rather than another fixed-decay rating system.

## 8. Score distributions

The score-distribution lane is scientifically useful but should remain **separate from winner-probability production**.

LevLine's preregistered coherent joint margin/total model produced higher winner accuracy than the market but worse Brier/log loss and significantly worse margin MAE. This is a concrete demonstration of why winner accuracy cannot override proper-score and distributional evidence.

Score models remain appropriate for:

- expected margin;
- total;
- score intervals;
- exact-score/tail simulation;
- derivative market analysis.

Their implied win probability receives no ensemble weight unless it independently beats the same-horizon raw market. Better score realism does not imply better event probability.

## 9. Calibration

Identity calibration is the default.

Beta calibration is the first serious parametric challenger because the beta family can retain the identity mapping, unlike ordinary logistic/Platt calibration. It must be fitted only on chronologically prior out-of-sample forecasts.

Flexible isotonic calibration is deferred until there is materially more independent data and explicit overfitting control. Calibration is not mandatory post-processing; an already well-calibrated market should be left alone.

## 10. Ensemble policy

Do not create an ensemble merely because multiple research components exist.

Recent forecast-combination research reinforces the combination puzzle: theoretical gains from estimated optimal weights can be small relative to estimation error, and discarding weak forecasts then averaging/shrinking the remainder can dominate elaborate weight estimation.

LevLine 4 therefore defaults to:

1. raw same-horizon market;
2. at most a sparse/shrunken residual if it has demonstrated incremental value;
3. no unrestricted optimized weights on a small NFL sample.

Every component must earn inclusion prospectively. A rejected player, dynamic-strength, or score model does not become useful merely because an optimizer can assign it a nonzero coefficient in-sample.

## 11. Validation and governance

Brier is the primary probability metric. Log loss and calibration corroborate. Winner accuracy remains descriptive.

Hard governance rules:

- strict same-game pairing;
- week-aware dependence handling;
- invalid probabilities fail closed rather than being clipped into validity;
- NFL ties are excluded from the binary home-win target rather than silently graded as away wins;
- duplicate forecast identities fail closed;
- raw T-120/T-60/T-45/T-30 timing is evaluated before model-adjustment claims;
- every adjustment is benchmarked against the raw market at the **same horizon**;
- horizon, de-vig, player, dynamic-strength, score, calibration, and ensemble searches are separate candidate families;
- family-level multiplicity is respected;
- material specification changes require a new candidate ID and prospective start;
- completed 2026 outcomes may grade frozen candidates but may not be repeatedly reused to invent rescue features or thresholds;
- promotion is explicit and never automatic.

## 12. What LevLine 4 should ship if the evidence supports it

The preferred eventual product architecture is two clocks:

### Accountability clock

- T-120;
- immutable `F-ST-01-FROZEN-2026` historical forecast of record.

### Final-probability clock

- horizon selected prospectively from T-60/T-45/T-30 only if the timing family establishes a genuine improvement over T-120;
- robust multi-book market consensus as the default probability backbone;
- F-ST-at-horizon, player residual, calibration, or any other adjustment included only when it beats the identical-horizon raw market under the frozen promotion rules.

If no later horizon establishes superiority, LevLine should **not promote a later clock merely because it sounds more informed**. If a later raw market wins and every proprietary adjustment fails, LevLine should publish the later raw market probability as the final probability and retain proprietary models for diagnostics, distributions, explanation, and editorial intelligence.

## 13. Research stopping rule

The LevLine 4 conceptual architecture is now considered **settled**.

Further architecture expansion has lower expected value than collecting uncontaminated prospective evidence. New model families should not be added to the active LevLine 4 search merely because the current slate is small or because an early result is disappointing.

From this point, the program should primarily:

- collect strict-PIT T-120/T-60/T-45/T-30 snapshots;
- preserve official player/news provenance;
- shadow the frozen de-vig family;
- audit capture completeness and source quality;
- grade only frozen candidates;
- wait for the formal evidence gate;
- apply the frozen family-level inference contract;
- promote only with explicit authorization.

A genuinely new architecture discovered later should normally be treated as a **new prospective candidate cycle (or LevLine 4.1)** rather than silently extending the search space of LevLine 4.0.

## 14. Final recommendation in one sentence

**Keep frozen F-ST at T-120 in production; make LevLine 4 a strictly point-in-time, prospectively selected multi-book market-timing system, and permit player state, dynamic strength, score distributions, calibration, or ensembles into the win-probability path only when they prove incremental proper-score value against the same-horizon market.**

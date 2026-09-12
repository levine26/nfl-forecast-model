# LevLine 4.0 Evaluation Governance Addendum V2

Status: **research-only / prospective clarification / no production authorization**

This addendum does not alter `F-ST-01-FROZEN-2026`, any official T-120 lock, Sunday Signal publication, or any production probability. It tightens evaluation semantics before any LevLine 4 horizon can be selected. These rules were authored without consulting LevLine 4 shadow performance to choose thresholds, horizons, interactions, or winners.

## 1. Primary timing family

The canonical information-timing experiment is the identically constructed raw multi-book market family:

- T-120
- T-60
- T-45
- T-30

The primary comparison uses only games having a valid point-in-time raw market forecast at **all four** horizons. Missing T-120/T-60/T-45/T-30 data remain missing. A later observation, closing line, corrected source, or postgame reconstruction may never fill an earlier horizon.

Pairwise analyses on larger partial samples are permitted only as explicitly labeled sensitivity analyses. They cannot replace the four-horizon complete-case primary analysis.

This separates the timing question (does waiting change forecast quality?) from the model question (does a LevLine adjustment improve the market available at that same time?).

## 2. Probability and outcome validity

A candidate probability used for binary scoring must be numeric, finite, and strictly between 0 and 1. Out-of-domain values are data-contract failures and are excluded/reported; they are never clipped into validity. Numerical clipping is allowed only inside logarithms or diagnostic logit transforms after validity has been established.

NFL ties are not away wins. Because the production target is currently a binary home-win probability, tied games are excluded from binary Brier/log-loss/winner-accuracy grading and reported separately. A future three-way target would require a new candidate/evaluation contract.

Duplicate forecast identities, missing timestamp provenance, ambiguous source identity, post-kickoff inputs, or missing week metadata for cluster inference fail closed.

## 3. Horizon inference and multiplicity

The minimum `>=200 eligible games` and `>=14 NFL weeks` rule is an **eligibility gate for formal inference**, not authority to select whichever horizon has the lowest sample Brier.

At the gate, the four horizons must be treated as one forecast-comparison family. Formal selection requires a joint or multiplicity-aware procedure that respects the dependence among losses from the same game and the shared NFL-week environment. Suitable methodological references include:

- Grant, Mrazik & Satchell (2026), *Journal of Forecasting*, DOI `10.1002/for.70150`, for joint multi-horizon forecast comparison and cross-horizon covariance;
- Hansen, Lunde & Nason (2011), *Econometrica*, DOI `10.3982/ECTA5771`, for Model Confidence Sets when the data do not identify a unique best forecast.

Because LevLine's horizons are multiple lead times for the **same game outcome**, the production research implementation should use a week-blocked family procedure tailored to these paired losses rather than mechanically importing an asymptotic test whose assumptions are not satisfied.

If multiple horizons remain statistically indistinguishable from the best, the preregistered engineering tie-break is: **choose the earliest horizon in the surviving confidence set that satisfies the product's information requirements**, because it preserves more retry/validation/publication margin without claiming unsupported predictive superiority.

## 4. Few-week caution

NFL weeks are the natural high-level dependence blocks, but 14 weeks is still a small number of clusters. Week-block bootstrap and leave-one-week-out diagnostics remain required, but their nominal interval should not be treated as infallible evidence solely because 14 weeks have elapsed. Promotion requires coherent point estimates, corroborating log loss/calibration, family-level inference, and explicit human authorization.

Relevant econometric work includes MacKinnon & Webb (2018), *The Econometrics Journal*, DOI `10.1111/ectj.12107`, documenting the difficulty of cluster inference with very few clusters.

## 5. Same-horizon model gates

For each horizon `h`, modeling effects are evaluated separately from timing:

`M_h` = raw same-horizon multi-book market consensus.

A model-adjusted candidate may claim incremental forecasting value only by beating `M_h` on paired proper-score evidence. Beating the frozen T-120 incumbent alone is insufficient because later information itself may explain the gain.

The evaluation order is:

1. raw `M_T120` vs `M_T60` vs `M_T45` vs `M_T30` timing family;
2. frozen structural transform `FST_h` vs `M_h`;
3. player-state residual vs `M_h`;
4. any dynamic-strength residual vs `M_h`;
5. any score-derived win probability vs `M_h`;
6. calibration/ensemble candidate vs its uncalibrated same-horizon parent.

Brier remains primary. Log loss and calibration must corroborate. Winner accuracy is descriptive and cannot override a proper-score failure.

## 6. Market construction

Book-level raw prices and timestamps are preserved. Proportional, Shin, power and robust consensus variants are separate market-construction candidates; none is assumed superior in two-way NFL moneylines from cross-sport evidence alone.

A de-vig parameter must not be interpreted as a direct measurement of hidden player news or informed betting. Whelan (2025), *Scottish Journal of Political Economy*, DOI `10.1111/sjpe.70017`, shows why the relationship between inside information and favorite-longshot distortions is not monotone enough to support that interpretation.

Any temporal line-movement correction must receive a new candidate ID and a prospective start or be fixed entirely from genuinely prior data. The negative autocorrelation in NFL pregame price changes reported by Simon (2025), *International Journal of Sport Finance*, DOI `10.1177/15586235251394815`, justifies the ablation; it does not authorize a post-hoc fade coefficient.

## 7. Player-state lane

Official inactive evidence is an information event, not an automatic adjustment. Player features enter only as a residual conditional on the same-horizon market and, where preregistered, the market path since T-120.

The player-state record must be as-of the forecast timestamp and preserve first-observed time, source publication/capture time, source identity/hash, team/player identity, status, expected role and uncertainty. No later inactive list, realized snaps, post-kickoff participation, or postgame player value can backfill the state.

Fischer & Schmal (2025), *Economic Inquiry*, DOI `10.1111/ecin.13258`, provide evidence that betting prices may digest player-absence information with initial inertia and lag. That motivates measuring market digestion; it does not establish an NFL player residual in advance.

## 8. Dynamic strength and score distributions

Dynamic latent strength remains a non-core challenger. Adaptive state-space evolution is the scientifically preferred form if revisited because team regimes can change abruptly, but it receives no probability weight without same-horizon incremental Brier evidence.

Score distributions remain an independent lane for margin, total, exact-score and tail inference. Better score-distribution fit does not imply better win probability. A score-derived probability must beat the same-horizon market before it can enter an ensemble.

## 9. Calibration and ensemble

Identity calibration remains the default. Beta calibration is the first parametric challenger when it can be trained on chronologically prior out-of-sample forecasts. Isotonic/flexible calibration requires materially more independent data and explicit overfitting controls.

Ensemble weights are not optimized merely because components exist. New 2026 work on the forecast-combination puzzle reinforces that estimated optimal weights can offer small gains relative to simple averaging and can lose through estimation error. LevLine therefore favors raw market or sparse/shrunken residual combinations unless a more flexible ensemble earns its complexity prospectively.

## 10. Candidate-family firewall

Horizon, market-construction, player-residual, dynamic-strength, score-distribution, calibration and ensemble searches are distinct candidate families. Completed 2026 outcomes may grade already-frozen candidates; they may not be repeatedly reused to invent interactions, retune thresholds, select a de-vig method, change player weights, or rescue a losing model.

A material specification change requires a new candidate ID and prospective evaluation start. Family-level multiplicity must be considered before any claim that the selected member is superior.

## 11. Production firewall

`F-ST-01-FROZEN-2026` remains the immutable T-120 production/accountability forecast throughout this program. Research collection, grading and challenger failures cannot rewrite historical locks or silently change Sunday Signal output. Promotion is explicit, reversible and separately authorized only after the research gates are satisfied.

# Adaptive Weekly Learning — Candidate 4 evidence review

Status: **pre-outcome design evidence / research only**  
Candidate: `ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1`  
Reviewed: 2026-09-22  
Production authority: **none**

## 1. Research question

Candidate 4 asks a narrower question than Candidates 1–3:

> After conditioning on the contemporaneous market level, can a selective combination of strict point-in-time market movement and independently timestamped football-information shocks identify a subset of winner decisions where frozen F-ST should be overridden?

This is not another weekly refit. It is not a generic market follower. It is not a player-value model. It is a sparse decision gate over the frozen incumbent.

## 2. Why Candidate 4 differs from Candidate 3

Candidate 3 tested a historical market-path innovation and was INCONCLUSIVE. Its +1 net winner gain was reproduced by a level-only control, so market path did not establish incremental information beyond the later market level.

Candidate 4 therefore requires:
1. same-horizon market level as an explicit control;
2. same-book T-120 -> T-60 path state;
3. an independently timestamped football-information shock that was not already available at T-120;
4. a sparse gate rather than a broad probability blend;
5. a new prospective clock.

No Candidate 3 threshold, robustness winner, or target-period result is eligible to tune Candidate 4.

## 3. User-supplied research reviewed

### Samford Sports Analytics — compact five-statistic NFL model

Source: Austin Streitmatter (2023), “How I Built a Competitive NFL Prediction Model with Only Five Statistics.”

Useful idea:
- low-dimensional models can be competitive when the inputs encode durable football structure;
- passing, rushing, takeaways and giveaways were converted into simulated game outcomes rather than stacked into an opaque high-dimensional learner;
- simulation can be useful after expected component values are estimated.

Limitations for LevLine governance:
- the public write-up describes changing the model after Week 8 of the same season;
- the reported 2022 success is one-season and not a chronology-frozen prospective validation of the revised specification;
- raw yards and realized turnovers are noisy and should not be copied literally into Candidate 4.

LevLine mapping:
- **do not add these variables to Candidate 4 V1**;
- preserve as a future compact-state challenger hypothesis using opponent-adjusted pass/rush efficiency and turnover-expectation/shrinkage rather than raw same-season box-score totals.

### nfl-data-py / nflverse

The PyPI package is useful as a catalog of accessible NFL data families (PBP, weekly/seasonal stats, rosters, scoring lines, NGS, depth charts, injuries, snap counts and FTN charting), but `nfl_data_py` is deprecated and its repository was archived in 2025 in favor of `nflreadpy`.

LevLine mapping:
- no deprecated `nfl_data_py` dependency;
- use direct nflverse artifacts or `nflreadpy` where a package wrapper is useful;
- every in-season feature still requires a point-in-time availability rule; a loader existing does not prove a field was known before kickoff.

### Congelio — advanced NFL analytics methods

Useful ideas:
- explicit feature engineering to encode game context;
- regularization and controlled feature selection;
- model families such as logistic regression and gradient boosting;
- personnel/formation context and over-expected metrics can improve the representation of play difficulty;
- holdout evaluation is necessary to diagnose overfit.

LevLine mapping:
- the feature-engineering concepts are relevant to future challengers, especially player/formation continuity and “over expected” state;
- ordinary random train/test splits and K-fold CV are **not sufficient for LevLine time-series forecasting** because future rows can inform earlier rows; LevLine must continue season-forward / week-forward validation;
- XGBoost or another flexible learner is not justified merely because it is powerful. It must beat simpler chronology-clean controls and survive ablation.

### Quinnipiac — total/spread capstone

Useful ideas:
- pregame player projections, weather and market lines can be combined with game data;
- forward selection and lasso are useful complexity controls;
- gradient boosting can be a worthwhile challenger when paired with disciplined feature selection;
- referee and coaching information are plausible future feature families.

Limitations for LevLine governance:
- the project reports K-fold cross-validation rather than a clearly chronological sports-forecast split;
- threshold scans can overstate performance if the same target period chooses the betting cutoff;
- it targets totals/spreads, not directly straight-up winner accuracy.

LevLine mapping:
- future spread/points work should preserve weather, referee/coaching, projection residual and selected boosting hypotheses;
- Candidate 4 V1 remains narrow and does not import those features after seeing current-season outcomes.

## 4. Current data-source findings

### Market source

The current `research-data/market-capture-v2` status is blocked:
- The Odds API request returned HTTP 401 Unauthorized;
- the append-only `market_snapshots.csv` ledger is empty;
- therefore no Candidate 4 market-path claim is currently authorized.

A promising replacement is PropLine:
- current NFL moneyline endpoint;
- The-Odds-API-compatible event/bookmaker/market/outcome shape;
- multi-book response;
- free tier with no card and 1,000 requests/day;
- per-book update timestamps exposed.

Public documentation is **not source qualification**. Candidate 4 requires a live, outcome-blind qualification receipt before PropLine rows can close a horizon.

Secondary free fallbacks identified for contingency only:
- Odds-API.io: free pre-match access but only two selected bookmakers;
- TheRundown: free delayed pregame odds from three books;
- SharpAPI: free two-book tier.

These are weaker for same-book path breadth than the documented PropLine surface and should not be silently substituted into the primary candidate.

### Football information

Already-qualified/reusable:
- official NFL injury snapshot archive;
- official NFL Sunday inactive article cohort parser V2 (held-out PASS);
- prospective expected-lineup/QB state schemas;
- nflverse 2025+ depth chart source semantics, including `dt`, `player_name`, `gsis_id`, `pos_abb`, and `pos_rank`.

Not yet qualified for Candidate 4 Week 3+:
- a Week 3+ prospective QB1 identity snapshot and join from depth-chart QB1 to the official inactive article;
- a probability-point or player-value effect for any inactive player.

Candidate 4 therefore uses only a deterministic **directional QB shock** if that identity join is qualified prospectively. Non-QB player absences remain diagnostic-only in V1.

## 5. Candidate 4 architecture selected pre-outcome

Decision horizons:
- incumbent prior: frozen F-ST T-120 state;
- update/gate: T-60;
- T-45 and T-30: diagnostics only for V1, never allowed to alter the T-60 Candidate 4 lock.

Primary gate is intentionally sparse.

Let:
- `P_FST120` = frozen incumbent home-win probability available by T-120;
- `M120`, `M60` = strict PIT multi-book no-vig home probabilities;
- `D60_120` = median same-book logit change from T-120 to T-60;
- `B60_120` = same-book directional breadth;
- `S_QB` = {-1,0,+1} qualified directional QB-information shock in home-team direction that first becomes knowable after T-120 and by T-60.

Required market-path integrity:
- at least 5 common sportsbooks;
- both horizons captured no later than their nominal cutoffs;
- path direction is usable only when `abs(B60_120) >= 0.50`;
- missing data fail closed.

Primary Candidate 4 changes the incumbent winner only when all are true:
1. T-60 raw market winner disagrees with the T-120 F-ST winner;
2. same-book path direction points toward the T-60 market winner;
3. `abs(B60_120) >= 0.50`;
4. a newly qualified directional QB shock exists by T-60;
5. the QB-shock direction points toward the T-60 market winner.

Otherwise Candidate 4 retains frozen F-ST.

The primary candidate contains **no fitted coefficient, no player point value, no team-specific rule, no current-season threshold fit and no manual news override**.

## 6. Mandatory controls / ablations

On the exact eligible rows:
1. frozen T-120 F-ST;
2. raw T-60 market level;
3. level-only switch control;
4. path-only gate (remove QB condition);
5. QB-news-only gate (remove path condition);
6. primary path + QB gate;
7. same-horizon F-ST transform if its strict PIT inputs are independently eligible.

Candidate 4 earns an incremental claim only if its selected switch set improves on the level-only and single-component controls. A favorable market-level result alone is not Candidate 4 evidence.

## 7. Probability diagnostics

Candidate 4 is fundamentally a decision gate. For secondary proper-score reporting, the frozen hybrid probability is:
- retain case: `P_C4 = P_FST120`;
- switch case: `P_C4 = M60`.

This rule is deterministic and untuned. It is not claimed to be an optimal probability blend.

Primary inference remains paired winner accuracy / net correct switches. Brier, log loss and calibration are guardrails.

## 8. Power and interpretation

For a selective switch gate, inference is limited by the number of disagreements, not the full game count.

Approximate two-sided 5% / 80% power for a switch-win test against 50%:
- true 55% switch win rate: ~783 switches;
- 60%: ~194 switches;
- 62.5%: ~124 switches;
- 65%: ~85 switches;
- 66.7%: ~68 switches.

At a 5% switch rate, 194 switches implies roughly 3,880 games. Therefore one remaining 2026 regular season is not enough to prove a small sustainable +0.3 to +0.5 percentage-point winner uplift.

2026 prospective evidence can still:
- detect obvious harm;
- test whether the gate actually fires;
- measure switch concentration and mechanism coherence;
- falsify source/identity assumptions;
- provide an initial locked effect estimate.

No small-sample positive result will be labeled “validated” solely because its raw accuracy is higher.

## 9. Future challenger backlog from this review

These hypotheses are recorded now but are **not Candidate 4 rescue options**:
- compact opponent-adjusted pass/rush efficiency + expected-turnover state;
- personnel/formation continuity from participation/depth data;
- over-expected player/team efficiency states;
- referee and coaching residuals;
- weather interaction models;
- pregame player-projection residuals;
- regularized gradient boosting after chronology-safe simple-model baselines;
- compact simulation layer for score/margin distributions.

Each requires a new candidate ID and prospective clock if Candidate 4 has already begun grading.

## 10. Current disposition

Candidate 4 theory: **scientifically coherent enough to preregister**.  
Market PIT execution: **blocked pending live source qualification**.  
Week 3+ QB identity execution: **not yet qualified**.  
Production F-ST: unchanged.

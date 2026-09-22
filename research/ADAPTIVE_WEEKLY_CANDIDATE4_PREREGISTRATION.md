# Adaptive Weekly Learning — Candidate 4 preregistration

Status: **FROZEN BEFORE FIRST ELIGIBLE CANDIDATE 4 GAME**  
Candidate ID: **ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1**  
Program: LEVLINE ADAPTIVE WEEKLY LEARNING RESEARCH PROGRAM  
Frozen date: **2026-09-22**  
Production authorization: **NONE**  
Completed 2026 outcomes used for Candidate 4 design/selection: **0**

## 1. Hypothesis

A later pregame market level can contain new information, but Candidate 3 did not establish that market path independently improves winner selection. Candidate 4 therefore tests a stricter proposition:

> Among games where the T-60 market winner disagrees with the frozen production F-ST winner, does broad same-book T-120 -> T-60 market movement that is directionally corroborated by a newly observed, independently sourced QB information shock identify a subset of winner switches that improves on F-ST and on a T-60 market-level-only control?

Candidate 4 is a sparse decision gate. It does not refit F-ST, does not estimate player value, and does not assign hand-written probability-point adjustments.

## 2. New prospective clock

Candidate 4 starts a new prospective clock.

No completed 2026 game may be used to:
- select features;
- choose thresholds;
- select a source;
- change the gate;
- choose a model family;
- rescue a failed or sparse result.

Completed 2026 games may be inspected only for source/parser integrity, schema behavior, timestamps, missingness, or operational defects, and any such use must remain outcome-blind for Candidate 4 selection.

The first possible **primary** Candidate 4 cohort is Week 3 Sunday, 2026-09-27.

For the 13:00 ET cohort:
- kickoff: 2026-09-27T17:00:00Z;
- nominal T-120: 2026-09-27T15:00:00Z;
- nominal T-60: 2026-09-27T16:00:00Z.

Thursday 2026-09-24 is **not** primary-Candidate-4 eligible because the currently qualified official inactive-article parser semantics are Sunday-specific. Thursday market data may be captured for source/operations diagnostics only and may not be graded as Candidate 4.

## 3. Frozen incumbent

The incumbent is the exact official production row from `outputs/prediction_history.csv` satisfying:
- `lock_status == LOCKED`;
- `snapshot_type` is the official lock snapshot;
- `final_probability_strategy == F-ST-01-FROZEN-2026`;
- `fst_artifact_id == F-ST-01-FROZEN-2026`;
- `0 < minutes_to_kickoff_at_lock <= 120`;
- lock timestamp precedes Candidate 4's T-60 decision timestamp.

If multiple production rows exist for one game, use the first immutable `LOCKED` row. Later production refreshes may not rewrite the Candidate 4 incumbent.

Define:
- `P_FST` = incumbent `final_home_prob`;
- `W_FST` = home if `P_FST >= 0.5`, otherwise away.

No Candidate 4 process may mutate this row.

## 4. Strict point-in-time market state

Primary source family: a zero-cost, qualified, multi-book live NFL moneyline source captured by the repository's append-only market collector.

Primary provider candidate at freeze: **PropLine**. The Odds API may remain an operational fallback only if separately configured and qualified under the same candidate source gates. A provider that has not passed Candidate 4's live source qualification cannot close a Candidate 4 horizon.

Required horizons:
- T-120;
- T-60.

T-45 and T-30 are diagnostic only for Candidate 4 V1.

### 4.1 One-sided timing

A horizon row is legal only when:
- request timestamp <= nominal horizon target;
- request timestamp >= target - 7.5 minutes;
- request timestamp < kickoff.

Positive timing error is prohibited.

Later snapshots may never backfill an earlier horizon.

### 4.2 Market construction

For each sportsbook at each selected request:
1. require one valid home and one valid away American moneyline;
2. convert each side to raw implied probability;
3. proportional no-vig normalization;
4. retain sportsbook identity and source update timestamp.

Horizon consensus:
- median sportsbook logit transformed back with expit.

### 4.3 Same-book path

For every sportsbook present at both selected T-120 and T-60 requests:

`delta_book = logit(p_home_T60_book) - logit(p_home_T120_book)`.

Require at least **5 common sportsbooks**.

Define:
- `D = median(delta_book)`;
- `B = (N_home_move - N_away_move) / N_common`.

Unchanged books contribute zero to the numerator and remain in the denominator.

A path is directionally broad only when:

`abs(B) >= 0.50`.

This threshold is frozen before any Candidate 4 outcome is graded and may not be tuned on 2026 results.

### 4.4 Market winner

Define:
- `M60` = T-60 consensus home probability;
- `W_M60` = home if `M60 >= 0.5`, otherwise away.

Market level is always preserved as its own control.

## 5. QB information-shock state

Candidate 4 V1 uses only one football-news shock type for winner authority:

**newly known unavailability of the T-120 QB1**.

No non-QB absence may alter Candidate 4 V1's winner.

### 5.1 T-120 QB1 identity

Use nflverse 2025+ depth-chart state:
- `dt <= nominal T-120`;
- exact team;
- `pos_abb == QB`;
- rank-1 depth state;
- stable `gsis_id`;
- `player_name`.

The latest legal team snapshot at or before T-120 is selected.

The QB1 state fails closed if:
- no legal snapshot exists;
- multiple rank-1 QB IDs exist;
- GSIS ID is missing;
- player name is missing;
- snapshot timestamp is later than T-120.

### 5.2 T-60 official inactive evidence

Source:
- official NFL inactive article;
- existing qualified cohort-aware parser V2 semantics;
- raw article capture timestamp is the conservative known-by time.

Candidate 4 requires:
- the due-game team cohort is present under the qualified parser semantics;
- the evidence is captured after the incumbent production lock and no later than nominal T-60;
- an inactive QB rendered name/team either exactly identifies the frozen T-120 QB1 or does not.

Emergency-third-QB annotation alone does not imply starter loss.

Exact name comparison may normalize Unicode, case, punctuation, spaces and common suffixes. It may not use fuzzy one-to-many guessing.

### 5.3 Directional shock

`S_QB` is expressed in **home-team probability direction**:
- home T-120 QB1 newly inactive => `S_QB = -1`;
- away T-120 QB1 newly inactive => `S_QB = +1`;
- no T-120 QB1 newly inactive under complete qualified evidence => `S_QB = 0`.

Candidate 4 does not estimate a QB magnitude.

No backup quality score, Elo delta, EPA point value, betting line delta, analyst estimate, LLM judgment or manual override is permitted.

## 6. Candidate 4 primary decision rule

Candidate 4 is evaluated only on games with:
- a valid frozen F-ST incumbent;
- qualified T-120 and T-60 market state;
- >=5 common sportsbooks;
- complete Candidate 4 QB source coverage.

Otherwise the row is marked **INELIGIBLE** and is not reconstructed later.

For an eligible game, switch from `W_FST` to `W_M60` **only if all are true**:

1. `W_M60 != W_FST`;
2. `sign(D)` points toward `W_M60`;
3. `abs(B) >= 0.50`;
4. `S_QB != 0`;
5. `S_QB` points toward `W_M60`.

Direction convention:
- market winner home => required `D > 0`, `B > 0`, `S_QB = +1`;
- market winner away => required `D < 0`, `B < 0`, `S_QB = -1`.

Otherwise retain `W_FST`.

Frozen Candidate 4 probability for secondary proper-score diagnostics:
- retain case: `P_C4 = P_FST`;
- switch case: `P_C4 = M60`.

This is not claimed to be an optimal probability blend.

## 7. Mandatory controls and ablations

On the exact Candidate 4 eligible sample, report:

1. frozen F-ST incumbent;
2. raw T-60 market;
3. **level-only switch control**: use `W_M60` whenever `W_M60 != W_FST`;
4. **path-only gate**: conditions 1–3, omit QB conditions;
5. **QB-only gate**: conditions 1, 4 and 5, omit path conditions;
6. **Candidate 4 primary**: conditions 1–5;
7. `D=0` ablation => F-ST;
8. `S_QB=0` ablation => path-only gate.

Candidate 4 cannot claim independent information if its net gain is fully reproduced by the level-only control and the primary switch set does not show incremental selectivity.

## 8. Immutable decision records

For every eligible T-60 decision attempt, preserve:
- game ID;
- candidate ID/version;
- preregistration commit SHA;
- code SHA;
- incumbent lock timestamp and probability;
- T-120/T-60 market request timestamps;
- market provider;
- selected event ID;
- common sportsbook names/count;
- `D`, `B`, `M60`;
- T-120 QB1 team/name/GSIS ID and depth timestamp;
- inactive article raw SHA and capture timestamp;
- `S_QB`;
- each gate boolean;
- Candidate 4 probability and pick;
- control probabilities/picks;
- decision timestamp;
- kickoff timestamp;
- all source qualification flags.

The decision row is append-only and content-hashed.

No result/score field is permitted in the lock constructor.

Outcomes may be joined later by a separate grader without mutating locked inputs.

## 9. Primary estimand

Primary:

`accuracy(Candidate4) - accuracy(F-ST)`

on exactly paired **eligible, prospectively locked** games.

Mechanism decomposition:
- switches;
- Candidate-4-only correct;
- F-ST-only correct;
- switch win rate;
- net correct switches.

Mandatory comparator:
- Candidate 4 versus the level-only control on the same eligible rows.

## 10. Secondary metrics

Report:
- Brier;
- log loss;
- calibration intercept/slope when sample permits;
- T-60 market accuracy/Brier/log loss;
- disagreement rate;
- switch rate;
- path breadth and common-book distributions;
- QB-shock prevalence;
- source/missingness coverage.

Winner accuracy remains primary.

## 11. Statistical inference

Once sample size permits:
- exact two-sided McNemar for Candidate 4 vs F-ST;
- exact paired test for Candidate 4 vs level-only control;
- week-block bootstrap of paired accuracy difference;
- week-block bootstrap of Brier difference;
- leave-one-week-out;
- leave-one-team-out;
- single-switch deletion;
- source/book concentration.

Bootstrap:
- 10,000 draws;
- seed `20260927`;
- NFL week is the resampling block.

## 12. Sample-size interpretation

Sparse-switch evidence is switch-count limited.

Approximate 80% power against a 50% switch-win null at two-sided alpha 0.05:
- true 55% switch win rate: about 783 switches;
- 60%: about 194;
- 62.5%: about 124;
- 65%: about 85;
- 66.7%: about 68.

Therefore the remaining 2026 season is primarily a **prospective falsification and mechanism-coherence test**, not a realistic path to proving a tiny long-run uplift.

No positive result with fewer than 30 switches may be described as validated.

Formal `PROSPECTIVELY_VALIDATED` is not available under Candidate 4 V1 unless all are true:
- >=200 eligible games;
- >=14 distinct NFL weeks;
- >=100 Candidate 4 switches;
- positive paired accuracy delta;
- Candidate-4-only correct > F-ST-only correct;
- Candidate 4 beats the level-only control on net correct switches;
- week-block 95% lower bound for accuracy delta >= 0;
- no single game/week/team supplies the entire net gain;
- Brier worsening <= 0.0025;
- all PIT/source-integrity gates pass;
- explicit human promotion authorization is later granted.

If the season ends below these counts, the default positive disposition is **INCONCLUSIVE / CONTINUE PROSPECTIVE COLLECTION**, not validated.

## 13. Harm / stop conditions

Candidate 4 may be labeled **REJECTED** before the full validation count if:
- its frozen rule produces a statistically resolved negative paired accuracy effect under the preregistered inference;
- or a source/timing defect invalidates the intended construct and cannot be mechanically corrected without creating a new candidate identity.

Ordinary sparse/no-switch behavior is not a reason to tune thresholds.

## 14. PIT/source failure rules

Fail closed on:
- post-cutoff market row;
- missing T-120 or T-60 market row;
- <5 common sportsbooks;
- mixed event identity;
- mixed provider identity within a selected request;
- future or ambiguous QB1 depth state;
- inactive source captured after T-60;
- incomplete due-game inactive cohort;
- unresolved QB identity;
- missing source hashes/timestamps;
- any post-kickoff source use.

A later successful source capture may not repair a missed earlier game.

## 15. Production firewall

Candidate 4 is research-only.

It may not change:
- official F-ST probabilities;
- Sunday Signal picks;
- production forecast generation;
- public confidence labels;
- production market source;
- production history.

Promotion requires a separate explicit later authorization after prospective evidence exists.

## 16. Defect policy

A mechanical implementation defect may be fixed only when:
1. the original artifact/behavior is preserved;
2. the defect is documented;
3. the correction does not use completed Candidate 4 outcomes;
4. the mathematical candidate definition is unchanged.

A change to thresholds, source semantics, QB shock definition, horizons, required book count, probability rule, or winner rule is a **new candidate version and new prospective clock**.

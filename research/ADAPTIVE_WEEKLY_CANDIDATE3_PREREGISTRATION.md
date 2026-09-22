# Adaptive Weekly Learning — Candidate 3 preregistration

Status: **FROZEN BEFORE CANDIDATE 3 TARGET EVALUATION**  
Candidate ID: **ADAPTIVE-MARKET-PATH-INNOVATION-V1**  
Program: LEVLINE ADAPTIVE WEEKLY LEARNING RESEARCH PROGRAM  
Production authorization: **NONE**

## 1. Hypothesis

A robust, same-book change in sportsbook no-vig win probability between an early pregame state and a later but still pre-T-120 state contains incremental information about the game that is not fully represented by frozen F-ST.

Candidate 3 tests **information arrival**, not raw market level and not generic weekly refitting.

Null: after conditioning on frozen F-ST, the preregistered market-path innovation does not improve paired straight-up winner accuracy.

## 2. Target sample

Primary historical target is the **2025 NFL regular season only**, exactly the 272 rows in the chronology-clean F-ST held-out 2025 vector produced by `build_chronological_logit_stack` from:

`challenger_outputs/fst/provenance/training_frame_keyed.csv`

The frozen 2025 F-ST benchmark must reproduce **179/272 = 65.8088235%** before Candidate 3 can be scored.

Postseason rows in the external archive are excluded because they are outside the 272-row benchmark.

No 2026 NFL-season outcome may be loaded by the Candidate 3 evaluation.

## 3. Historical market-path source contract

Source:
- public repository: `bobby-king3/nfl-market-movement-tracker`
- release: `v1.1.1`
- asset: `nfl_odds.duckdb`
- required SHA256: `b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c`
- qualified relation: `main.stg_odds`

Historical source qualification receipt:
`research/ADAPTIVE_WEEKLY_CANDIDATE3_PIT_AUDIT.json`

The source is **not** qualified as exact T-120/T-60/T-45/T-30 history.

Primary bands are frozen as:

- **EARLY**: latest book snapshot with `kickoff-36h <= captured_at <= kickoff-24h`.
- **LOCK**: latest book snapshot with `kickoff-6h <= captured_at <= kickoff-2h`.

Every selected snapshot must satisfy `captured_at < kickoff`.

Closing data, post-kickoff data, and observations later than T-120 may not backfill LOCK.

## 4. Game identity

Market events are mapped to frozen F-ST game IDs only from:
- season = 2025;
- archive `nfl_week` in 1..18;
- away-team abbreviation;
- home-team abbreviation.

Canonical game ID:
`2025_<week:02d>_<AWAY>_<HOME>`.

No fuzzy outcome-based matching is permitted. Duplicate or ambiguous identity fails closed.

## 5. Book-level probability construction

Use `market_type='h2h'` only.

For a sportsbook/capture/event:
1. require one home and one away American moneyline;
2. convert American prices to raw implied probabilities;
3. proportional no-vig normalization:
   `p_home = q_home / (q_home + q_away)`;
4. reject non-finite or non-(0,1) probabilities.

The de-vig method is fixed to proportional normalization because it is already an existing LevLine preregistered transform and is algebraically simple. No de-vig method selection is allowed from Candidate 3 outcomes.

## 6. Same-book path feature

For each sportsbook with both a valid EARLY and LOCK observation:

`delta_book = logit(p_home_lock_book) - logit(p_home_early_book)`.

Require at least **5 common sportsbooks** for a qualified path.

Primary path innovation:

`D = median(delta_book)`.

Also record, for diagnostics only:
- common-book count;
- home-move share;
- away-move share;
- unchanged share;
- median absolute deviation of `delta_book`;
- EARLY consensus;
- LOCK consensus.

EARLY and LOCK consensus are `expit(median(logit(p_book)))` over the same common books.

These diagnostics do not gate or change the primary candidate.

## 7. Frozen Candidate 3 architecture

Let `P_FST` be the chronology-clean F-ST probability for the game.

Primary shrinkage coefficient:

`lambda = 0.50`.

Candidate probability:

`logit(P_C3) = logit(P_FST) + 0.50 * D`.

Candidate winner:
- home if `P_C3 >= 0.5`;
- away otherwise.

No additional magnitude threshold, favorite bin, team rule, QB rule, injury rule, news rule, or hand-coded player value is permitted.

If a game has no qualified path:
- `P_C3 = P_FST`;
- winner remains F-ST;
- the row remains in the 272-game primary paired sample;
- record fail-closed status.

This architecture is deliberately a shrunken state update rather than a learned target-season model.

## 8. Prespecified robustness grid

Run all cells and report all cells:

- lambda = 0.25
- lambda = 0.50 **PRIMARY**
- lambda = 0.75
- lambda = 1.00

No value may be selected, promoted, or retuned based on the 2025 target result.

Additional source-window robustness, also report all:
- primary LOCK T-360..T-120;
- stricter LOCK T-300..T-120;
- strictest LOCK T-240..T-120.

EARLY remains T-2160..T-1440 for all window cells.

The primary result remains lambda 0.50 with LOCK T-360..T-120 regardless of which cell scores best.

## 9. Controls

On the relevant identical rows, evaluate:

1. chronology-clean frozen F-ST;
2. frozen stored F-ST market probability;
3. external EARLY market consensus;
4. external LOCK market consensus;
5. external latest-prekickoff consensus, clearly labeled a later-information descriptive comparator rather than a legal lock-time candidate;
6. component-resolved season-forward L2 stack using market logit + logistic + extra_trees + xgboost + catboost logits, `C=1.0`, `lbfgs`;
7. Candidate 1 unchanged if its canonical prediction vector is recoverable;
8. naïve weekly F-ST refit unchanged if its canonical prediction vector is recoverable;
9. Candidate 2 unchanged if its canonical prediction vector is recoverable;
10. **level-only control**:
   `logit(P_LEVEL) = logit(P_FST) + 0.50 * (logit(P_LOCK) - logit(P_FST_MARKET))`;
11. **market-trend control**:
   `logit(P_TREND) = logit(P_LOCK) + 0.50 * D`.

Controls with missing external market state are reported on the qualified complete-case subset. F-ST-vs-Candidate3 primary inference remains all 272 rows because Candidate 3 fails closed.

## 10. Primary and secondary metrics

Primary:
- paired straight-up accuracy difference Candidate 3 minus F-ST.

Also report:
- correct count;
- accuracy;
- number of winner switches;
- candidate-only correct;
- F-ST-only correct;
- switch win rate;
- path coverage;
- fail-closed count.

Secondary:
- Brier score;
- log loss;
- calibration intercept;
- calibration slope.

## 11. Inference

Primary paired inference:
- exact two-sided McNemar diagnostic;
- week-block bootstrap of paired correctness difference, 10,000 draws;
- seed `20260922`.

Also report:
- week-block bootstrap for Brier difference;
- leave-one-week-out accuracy delta;
- leave-one-team-out accuracy delta;
- switch concentration by week/team;
- single-game deletion effect on net correct gain.

Because only one historical season has qualified path data, **no multi-season superiority claim is allowed**.

## 12. Adversarial tests

Mandatory:
- single-game dependence;
- single-week dependence;
- single-team dependence;
- single-book deletion;
- path-feature ablation (`D=0` => F-ST);
- level-only control;
- raw market explanation;
- stricter LOCK windows;
- lambda robustness grid;
- F-ST boundary concentration;
- feature missingness/fail-closed audit;
- post-lock timestamp audit;
- latest-prekickoff information firewall;
- 2026-season outcome load guard.

## 13. Success bands

Historical Candidate 3 can be labeled **PROMISING / REQUIRES PROSPECTIVE VALIDATION** only if all are true for the frozen primary cell:

1. accuracy delta > 0;
2. at least 10 winner switches;
3. Candidate3-only correct > F-ST-only correct;
4. week-block bootstrap 95% lower bound is >= 0;
5. no single game supplies the entire net gain;
6. deleting any single week does not make the aggregate delta negative;
7. no single team supplies more than 50% of the net correct gain;
8. lambda 0.25, 0.50, and 0.75 are all non-negative versus F-ST;
9. level-only control does not fully reproduce Candidate 3's net winner gain;
10. probability quality is not pathological and Brier worsening is <= the existing +0.0025 research alert.

Disposition:
- **REJECTED** if the frozen primary cell has accuracy delta < 0, or if the switch record is <=50% with at least 10 switches and no compensating probability-only value.
- **INCONCLUSIVE** for zero gain, positive-but-fragile gain, fewer than 10 switches, concentration failure, or uncertainty that materially includes harm.
- **PROMISING / REQUIRES PROSPECTIVE VALIDATION** only under the ten conditions above.
- **PROSPECTIVELY VALIDATED** is impossible from this historical experiment alone.

No historical result authorizes production promotion.

## 14. Prospective requirement if historical evidence is not rejected

If Candidate 3 is not rejected, the exact frozen architecture may enter a research-only prospective shadow after this historical closeout, but only under a new immutable prospective-start receipt.

Earliest descriptive checkpoint:
- >=200 eligible games and >=14 weeks.

This is not automatically enough for validation; the repository's accuracy-first power analysis shows small winner deltas may require much larger samples.

## 15. Prohibited data/actions

Prohibited:
- completed 2026 NFL-season outcomes for design or evaluation;
- post-kickoff information;
- post-T-120 snapshots as LOCK inputs;
- reconstructed T-60/T-45/T-30 claims from this four-daily archive;
- target-result-driven feature changes;
- threshold scans;
- team/QB/player-specific outcome tuning;
- selecting the best robustness cell as the candidate;
- production F-ST/Sunday Signal changes.

## 16. Defect policy

If a genuine implementation defect is found after this preregistration:
1. preserve the original result;
2. document the defect;
3. version the candidate;
4. explain why the correction is mechanical/scientific rather than performance tuning.

Candidate 3 ends after its final historical finding/receipt. Candidate 4 must not begin automatically.

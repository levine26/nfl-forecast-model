# LevLine Post-Week-4 Phase 3 — Pre-result Candidate Contract (A/B/C)

**Frozen on:** 2026-10-07, before any new A/B/C candidate result in this program.  
**Parent:** `research/LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md` (the sole authoritative roadmap) and `research/LEVLINE_POST_WEEK4_PHASE1_2_FINDINGS.md`.  
**Production identity:** `F-ST-01-FROZEN-2026`; no production writes or promotions.  
**Additional sources:** Alexandria is EXCLUDED from A/B/C, as required by the separate PIT feasibility addendum.

## Evaluation and data firewall

1. The **1,087-game 2022–2025** chronology-clean paired universe is the target when source identities allow; base F-ST architecture is **741/1,087**, market **735/1,087**. Historical **740/1,087** is a different, final-coefficient F-ST reconstruction, **not** the primary OOS comparator. Load immutable recovered F-ST base OOF and frozen training-frame artifacts, verify hashes, keyed identity, target, exact row counts; do **not** use 2026 outcomes.
2. Train each target season using **strictly earlier seasons**, including all preprocessing, calibrators and component fits. Never use a target year's outcome in fitting, sigma/penalty estimation, missing-value or threshold selection. Freeze candidates and ablations before evaluation. For all candidates: p>=0.5 picks home, otherwise away; exclude ties from binary forecast grading and document identity.
3. Report exact paired rows, correct/incorrect, season-by-season and Weeks 1–4/1–6, market-strength and component disagreement where available, challenger-only vs F-ST-only wins, total switches, switch win rate, Brier, log loss, calibration intercept/slope, 2,000-resample season-week block-bootstrap 95% accuracy interval (seed 26) and season-deletion sensitivity. Accuracy is primary; proper scores are diagnostics/guardrails, not retroactive feature selectors. Do not combine A/B/C post-results. Explicitly report missing/failed input qualification as **NOT EVALUABLE**.
4. Reuse the frozen F-ST season-forward implementation rather than fitting a new baseline. If the common population or baseline reconstruction differs from 1,087 and 741, **fail closed**, investigate input identity and do not publish a replacement accuracy. No 2026 performance feedback may be used anywhere in design, tuning or selection.

## A — `MKT-COMP-RESIDUAL-V1`

**Hypothesis:** separate Logistic, Extra Trees, XGBoost, CatBoost departures from game-level moneyline contain small information lost by aggregate PURE. **Fixed candidate features** from *frozen historical OOF*: four logit(component)−logit(market) residuals, their mean, population standard deviation, range, and absolute market logit. Fixed clip only for numerical logit at 1e−6. Use the market logit with coefficient **fixed at 1** as the GLM offset; train intercept and residual coefficients with mean-log-loss plus L2 penalty `0.02 * ||beta||²/2` (intercept exempt), pretarget z-score normalization (zero-variance → 0), `scipy.optimize.minimize(L-BFGS-B)`, deterministic. Fixed ablations: 4 component residuals only; all 8 (primary); market baseline. No threshold, team-ID, component-vote override, or tuning grid.

Train 2022–2025 season-forward from frozen 2020–2025 training rows. Historical failure mode: previously observed 2022-only uplift of a related, *not identical* component stack. If gain is season-concentrated, classify **INCONCLUSIVE**.

## B — `MARGIN-RESIDUAL-WIN-V1`

**Hypothesis:** independently trained expected home margin contributes binary winner information after conditioning on contemporary moneyline.

**Prerequisite:** reproducible historical, game-keyed schedule/PBP, strictly pregame shifted features and point-in-time-compatible moneyline; no 2026 outcomes; market/target identity exactly match frozen panel. No filling missing markets from future closings.

**Margin engine:** research-only `SimpleImputer(median) + StandardScaler + Ridge(alpha=100)` on the same fixed `core_columns()` used by the existing engine, trained on earlier seasons 2012–prior year. Produce season-forward margin predictions 2015–2025. For target year S, estimate residual standard deviation from **prior-year-only OOF margin residuals** of years 2015..S-1, with population RMS, minimum 50 observations, and fixed floor 1.0; never estimate using year S. Convert to `P(home win) = NormalCDF(predicted_margin / prior_RMS)`, clip for logit numerics 1e-6.

**Winner stage:** for each 2022–2025 target, use earlier **2020–S−1** game rows to fit market offset+single margin logit-minus-market logit residual using same fixed mean-log-loss/L2 penalty `0.02` and pretarget scaling as A. **Primary** market+margin residual; fixed diagnostics: margin-only, raw market, frozen F-ST. A **F-ST+margin** combination requires separately qualified pre-2022 F-ST OOF history and may only be reported when such data is verified; never train the F-ST+margin residual on target 2022 data. Do not treat contemporaneously refitted in-sample margin predictions as OOF.

## C — `EARLY-STATE-SHRINKAGE-V1`

**Hypothesis:** offseason carried-forward team offense/defense EPA should be explicitly shrunk rather than carried unmodified. **Prerequisite:** historical game-level team PBP aggregated from completed REG games only, chronology-valid ordered games, original game/team identity and pregame market, no post-kickoff opponent states.

Research-only team-state transform for `off_epa` and `def_epa_allowed` at each next fixture:
- `prior_form` = previous season's last eight completed team games' mean for that side; if missing, prior season league mean.
- `prior_center` = `0.6*prior_form + 0.4*previous_season_league_mean`.
- `current_form` = mean of this season's **already completed** team games; if zero, use prior_center.
- `state = (n*current_form + 6*prior_center)/(n+6)`, where `n` = this season's completed prior games.
- Team home-minus-away difference for both offense/defense. Additional pregame state: season observation count for home and away and an **optional separate, independently qualified QB continuity state** derived only from previous games. Any QB starter/event state without an actual pregame timestamp/identity is excluded with a missingness receipt; no retrospectively inferred next starter from current game's snaps.
- Historical `elo_home_prob` as a control when provably pregame.

Winner model: market-logit **fixed offset** plus the fixed z-scored `off_state_diff`, `def_state_diff`, and `abs(n_home−n_away)/(n_home+n_away+6)` features; regularized L2 `0.02`; each target 2022–2025 trained only on prior 2020–S−1 seasons. If an eligible QB continuity input exists it must be **separately preregistered before looking at target outcomes**, not introduced silently. Fixed comparator is frozen F-ST. Report Weeks 1–4 and 1–6 separately. Do not edit the live `features.py` or wire config controls into production.

## Results and governance

- Each candidate produces one immutable identifier, exact game-level OOF predictions, qualified source manifests, and per-candidate metrics. Failures count as failures; no after-the-fact re-specification under the same ID.
- Classify **ADVANCE FOR INDEPENDENT PROSPECTIVE SHADOW**, **INCONCLUSIVE**, **REJECT**, or **NOT EVALUABLE**. Historical success is not production promotion. Multiple candidates require a separate multiplicity-aware review before any joint winner selection.
- D/E/F not implemented. Alexandria not used. All official F-ST/Sunday Signal outputs untouched.

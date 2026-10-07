# Phase 4 — Independent Prospective C Shadow: Pre-result Contract

**Status:** PREREGISTERED RESEARCH DESIGN; not operational until separate implementation/preflight is proven.  
**Registered:** 2026-10-07, before any prospective Candidate C grade or C/2026 tuning.  
**Single authoritative roadmap:** `research/LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md`.  
**Incumbent:** immutable official `F-ST-01-FROZEN-2026`; no production edits, no promotion without separate explicit approval.  
**Research candidate ID:** `EARLY-STATE-SHRINKAGE-V1-SHADOW-2026-10-07`, frozen **same feature architecture** as historical C (not a new optimized model).  
**Historical evidence:** prior 2022–2025 C = 749/1087 vs chronology-clean F-ST 741/1087 with uncertainty crossing zero; *hypothesis generation only*. No completed 2026 result is allowed in candidate fitting, feature selection, cutoff selection, gate setting or source qualification.

## 1. Frozen training and architecture

- Use `research/post_week4_phase3/run_candidates.py` implementation of `early_state_features`, `fit_offset`, and `predict_offset` **without changing their scientific definitions**. Freeze the exact implementation SHA on model build.
- Model feature order exactly `["off_state_diff", "def_state_diff", "state_uncertainty"]`; home minus away team EPA for `off_epa` and `def_epa_allowed`; year-boundary prior = 0.6 × previous-season team last-eight form + 0.4 × previous-season league mean; current blend = n/(n+6); unqualified next-QB-state omitted.
- Fit one market-logit **coefficient-one fixed offset** with intercept and z-scored three residual features, L2 0.02, L-BFGS-B, `ftol=1e-12`, maxiter=1000, numeric clip 1e-6, standardizer trained on prior years only; p(home)>=0.5 selects home.
- Fit **exactly once** on recovered hash-validated F-ST historical training panel from 2020–2025 (1,615 rows) and an independently reconstructed `nflreadpy` 2012–2025 *REG* football feature frame, with game ID/season/outcome validation. Persist trained coefficients, normalization, panel SHA, source identity, input dimensions and program SHA to an immutable research-only artifact. No new hyperparameter grid, later refit, or automatic weekly learning.
- **Legacy training-label caveat:** historical C training uses frozen `home_win` binary label, including tied games as `0`. This is NOT a strictly tie-excluded historical training corpus; report that limitation. Live tied games are excluded from evaluation and never treated as away wins. A scientifically strict tie-excluded historical refit is a separate preregistered challenger and cannot replace this frozen candidate silently.
- No outcome beyond 2025 in training, even if source load includes later live data.

## 2. Fair prospective point-in-time comparison

Prospective start is **the creation timestamp of the first independently verified, strictly pre-kickoff eligible captured snapshot AFTER this preregistration and frozen-artifact construction**. Do not backfill Week 1–4/older completed games, and do not select a favorable start later.

For each scored game require one immutable per-game research envelope with:
- unique `game_id`, exact season/week/home/away identity, valid source `kickoff_utc`, official `fst_lock_timestamp_utc` and official locked `fst_home_prob` and `market_home_prob`;
- source/capture timestamps `features_observed_at_utc`, `feature_source_asof_utc`, `snapshot_recorded_at_utc`; **feature capture and observation must occur no later than official F-ST lock**, all strictly before kickoff;
- numerical `off_state_diff`, `def_state_diff`, `state_uncertainty` derived *solely from completed earlier team games* under the historical state formula; linked hash and provenance for immutable raw research snapshot and generator identity;
- official F-ST frozen identity and unmodified production lock, verified that it was a lock rather than a later final-state reconstruction;
- one `candidate_home_prob` from frozen model artifact; no manual odds movement, injury report, market-quality data, later corrections or Alexandria features.

Fail closed on any duplicate, missing team/game key, missing origin/capture time, source timestamp after F-ST lock, missing upstream hash, non-finite/out-of-range input, kickoff at/before capture, revised old snapshot, source uncertainty or run after cutoff. Preserve an **ineligibility/missingness receipt**; never substitute later state for a missed lock. No status that labels late evidence as on-time.

Operational boundary: **isolated research-only program**, no editing `outputs/`, `site/`, `src/nfl_forecast/`, `scripts/run_week.py`, official history, F-ST/scoring/lock/ATS grading. No automated collector until PIT provenance and legal data rights are verified. Source snapshots should be immutable, access-limited, and not publish licensed raw feeds on public GitHub. Only candidate predictions, hashed provenance and aggregate grade are acceptable research artifacts.

## 3. Prospective grading and stopping

- Eligible predictions must exist as immutable pregame captured records before kickoff. Evaluation joins outcomes **later** and treats them as labels only. Ties excluded from winner accuracy/Brier/log loss with explicit count and game IDs; missing grades remain pending, not losses.
- Exact paired **same-game, same-horizon** comparison: frozen C versus **official locked F-ST** and contemporaneous market at its lock. No season-forward reconstructed F-ST substitution, no latest prices.
- Primary: difference in correct winner picks, switch count, C-only correct, F-ST-only correct, switch win rate. Secondary: Brier, log loss, calibration and by-week/season/per-confidence slices; week-block 95% interval and leave-one-week-out/season sensitivity when statistically possible. No post-result threshold, intercept, feature or window tuning.
- **Earliest formal checkpoint:** >=200 newly eligible *non-tie* games and >=14 distinct NFL week-blocks after first eligible prospective snapshot. Below that: `ACCUMULATING_EVIDENCE`; intervals descriptive only. Passing the checkpoint does not establish superiority.
- Candidate is `PROMISING_PROSPECTIVE_SHADOW` only if positive paired accuracy advantage, week-block 95% lower bound >0, and no material one-week or one-season dominance; Brier/log-loss/calibration must be reported and reviewed, with deterioration >0.0025 Brier flagged. Invalid probability, extreme loss, unverified timestamps or data identity fail the gate. No automatic promotion irrespective of results.
- Stop/reject for ineligible PIT source or irreproducible feature identity. If evidence cannot distinguish candidate from F-ST, **retain F-ST**. No post-hoc combination with D/E/F or new conditional gate. A/B remain rejected under the original Phase 3 IDs.
- A full NFL season may be required; at 2026-10-07 only a minority of this season remains, so **prospective predictive-superiority validation cannot be completed in the current session**.

## 4. Parallel independent workstreams

Parallel tracks are allowed, not mixed into this candidate: (a) source/time/label and tie/early-week audit, (b) standalone snapshot schema and fail-closed scorer, (c) low-cost Alexandria terms/coverage design, not activation. Each uses separate research-only PR, no synthetic historical success claims or 2026 tuning. Existing unified roadmap remains the source of truth.

**Phase 4 delivery distinction:** a passing scorer/test suite, frozen research model artifact and validated end-to-end *synthetic* snapshot receipt count as `INFRASTRUCTURE_READY`, **not** `PROSPECTIVE_RESULTS_COMPLETE`. If no actual qualified pre-kickoff candidate snapshots have been collected, status is `AWAITING_ELIGIBLE_LOCKS`.

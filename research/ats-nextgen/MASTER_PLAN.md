# LevLine ATS Next-Generation Research Program — Master Plan

**Status:** authoritative program charter  
**Repository:** `levine26/nfl-forecast-model`  
**Canonical directory:** `research/ats-nextgen/`  
**Initialized:** 2026-09-23 America/Los_Angeles  
**Phase-1 base main:** `21f153d69ad579f6bd67250d75330b2c77ea1228`  
**Production control:** `F-ST-01-FROZEN-2026` — unchanged

GitHub is the institutional memory for this program. This program is a new scientific family, not a rescue of the completed Spread & Points Next-Generation program.

## 1. Motivation and accepted prior evidence

The prior program is closed. Its negative results are fixed evidence:

- current independent margin regression historical MAE ≈ **9.962**;
- historical market spread MAE ≈ **9.494**;
- raw independent-margin model-side ATS hit rate ≈ **48.77%**;
- large model-market disagreement was not a validated edge;
- ≥6-point disagreements were materially worse than the market in continuous margin error;
- A0 and B0 did not beat the market as standalone margin models;
- C0 did not establish incremental football information around the historical closing/late market benchmark;
- `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1` (Candidate 5) did not improve F-ST and is rejected;
- generic historical mean-residual stacking is therefore not reopened under a new name.

The new hypothesis is materially different: **ATS should be modeled as a conditional discrete margin distribution and cover/push/loss probability problem around the exact quoted line and price, not merely as unconditional conditional-mean margin prediction.**

## 2. Scientific objects

Canonical notation:

- `M = home_score - away_score`;
- `L = sportsbook_home_spread`, sportsbook convention (home favorite -3 => `L=-3`);
- `C = -L`, the market-implied home margin center;
- `R = M + L = M - C`, the home ATS residual;
- home cover iff `R>0`, push iff `R=0`, loss iff `R<0`.

The Phase-2 candidate family is frozen to exactly three primary experiments:

1. **Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`**: regularized linear quantile regression for `R` at τ = 10/21, 1/2, and 11/21.
2. **Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`**: discrete integer-margin PMF, generalized-normal primary base, fixed Gaussian/Student-t/empirical comparison arms, conditional scale, and training-only key-number excess mass.
3. **Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`**: direct cover/push/loss probability model using a structurally correct hurdle formulation with L2-regularized logistic heads.

No unrestricted model tournament is authorized.

## 3. Market is the primary null

The sportsbook market is the central benchmark, not simply one feature.

- **M0:** quoted spread, no LevLine adjustment.
- **M1:** market-derived discrete probability distribution using only qualified market variables and prior-data distribution calibration.
- **M2:** market + simple line-level calibration only, with no football variables.

Q1/Q2/Q3 may claim incremental football information only when they improve the relevant market null under the preregistered proper-score/quantile metrics. Calibration usefulness and betting-selection usefulness are distinct claims.

## 4. Evidence boundary

Seasons **2022–2025 are development/non-pristine evidence**. They have been heavily inspected in prior LevLine programs. They may be used for chronology-clean OOF development, representation tests, mechanism tests, calibration analysis and bounded candidate comparison, but a positive result cannot by itself authorize production.

Completed **2026 outcomes are firewalled** from architecture, features, hyperparameters, distribution choice, key-number parameters, thresholds, blending, calibration and rescue. Outcome-blind live 2026 market/input data may be used only to qualify prospective sources.

Any Phase-3 survivor can earn at most `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`. Production promotion requires later prospective evidence and explicit human authorization.

## 5. Program phases

- **Phase 1 — Deep ATS Research, Problem Reformulation & Preregistration.** Research/design only. No Q1/Q2/Q3 execution.
- **Phase 2 — Controlled Implementation & Historical Development.** Implement the frozen designs; 2022–2025 remains development/non-pristine; no production.
- **Phase 3 — Scientific Synthesis, Candidate Selection & Freeze.** Classify each architecture `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`; no production promotion.
- **Phase 4 — Conditional future prospective shadow validation.** Start only if Phase 3 earns eligibility and the user explicitly authorizes continuation.

## 6. Production firewall

Phase 1 may edit only research/governance material. It must not modify F-ST artifacts/coefficients, the production winner path, Sunday Signal numerical forecasting, public fair-spread semantics, official locks/history, or grading.

The current production control remains `F-ST-01-FROZEN-2026`.

## 7. Anti-rescue rule

Once Phase 1 closes, the candidate identities, chronology, feature hierarchy, metrics, key-number buckets, blend grid, selective-evaluation policy and evidence boundaries are frozen. If Phase 2 exposes a scientific specification error, fix it only by versioning the affected candidate, recording the pre-result reason, and resetting any impacted evidence clock. Poor results are not a specification error.

## 8. Canonical control files

Future chats must read at minimum:

- `MASTER_PLAN.md`;
- `PHASE_STATUS.md`;
- `CURRENT_STATE_AND_NEXT_STEPS.md`;
- `PHASE1_RESEARCH_CHARTER.md`;
- Q1/Q2/Q3 preregistrations;
- `EVALUATION_PROTOCOL.md`;
- `CHRONOLOGY_AND_EVIDENCE_BOUNDARY.md`;
- `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`;
- latest immutable phase receipt.

If chat memory conflicts with these files, the repository controls unless the user explicitly amends the program.
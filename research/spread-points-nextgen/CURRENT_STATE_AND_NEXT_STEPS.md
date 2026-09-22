# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-22 America/Los_Angeles  
**Program authority:** \`research/spread-points-nextgen/MASTER_PLAN.md\`  
**Phase 0:** **COMPLETE**  
**Phase 1:** **COMPLETE**  
**Phase 2:** **IN PROGRESS — CLOSEOUT / EXACT-HEAD VALIDATION**  
**Phase 3:** **NOT STARTED**  
**Active branch:** \`research/spread-points-nextgen-phase2\`  
**Primary PR:** #520

## Phase 2 state

Phase 2 research/design is analytically complete and has passed hostile methodological review. No Phase 3 challenger has been implemented and no A/B/C 2025 challenger result has been inspected.

The branch was synchronized with current main through compatibility PR #521. The synced main-only work belongs to the separate adaptive-weekly-learning research program and is preserved without making Spread & Points Phase 2 dependent on it.

## Frozen initial Phase 3 shortlist

- **A — Dynamic Opponent-Adjusted Joint Score:** football-only. Initial identity is bounded A0: time-decayed, partially pooled offense/defense score model.
- **B — Possession / Drive Score Process:** football-only. Independent B0 must model possessions plus TD/FG/empty drive outcomes without consuming A0 predictions. No B+A sensitivity is part of the initial Phase 3 search.
- **C — Market Residual Margin / Total:** market-aware. Initial C0 is Ridge-only and must report M0 market-only, M1 line-calibration-only, M2 football-residual, and M3 full residual arms.
- **D — Ensemble / reconciliation:** conditional only. Do not build unless at least two frozen candidates survive development and nested OOF combination adds information beyond the best constituent.

A1 explicit state-space expansion, player/QB/personnel overlays, and weather are **not** automatically authorized initial extensions.

## Frozen chronology

Initial training history is **candidate-specific earliest complete required-feature coverage**; Phase 3 may not search alternate training-start years for better performance.

Development outer targets are exactly:

- 2022 — prior seasons only;
- 2023 — prior seasons only;
- 2024 — prior seasons only.

For each outer target, use expanding prior-only inner folds; a fold requires at least two complete prior training seasons. Use the **latest four valid inner validation seasons**, or all valid folds when fewer are available. If fewer than two valid inner validation seasons exist, use the candidate's frozen fallback rather than borrowing later data. All preprocessing, latent-state construction, residual variance/covariance estimation and tuning are training-only.

Final historical challenger holdout:

- **2025** — open once in Phase 4 only after candidate identities freeze.

Completed 2026 outcomes:

- **zero permitted for architecture, features, tuning, thresholds, stacking, survival, or candidate selection.**

Phase 1 did inspect baseline 2025 failures, so 2025 is not philosophically pristine. No A/B/C output existed then. This caveat remains mandatory and Phase 5 prospective evidence is still required.

## Data / PIT state

Initial A/B/C can be built from free/open data.

Allowed foundations include chronology-safe prior-game nflverse PBP, derived dynamic states, schedule/home/rest, and historical schedule market lines labeled only as closing/late benchmark.

Conditional or blocked:

- QB/personnel: no uniform fixed-horizon 2022–2025 starter/availability history;
- injuries/OL: qualified 2025 slice and prospective evidence only unless older PIT history is proven;
- weather: blocked from initial historical selection until exact venue plus forecast-as-of history is qualified;
- prospective multi-book T-120 market: current research collector issue remains HTTP 401 / no qualified current ledger at the Phase 1 audit;
- historical market rows may **not** be relabeled T-120.

## Paid-data decision

**NO PAID DATA DEPENDENCY REQUESTED.**

A/B/C are testable with free/open sources. Paid injury/OL/route/coverage/participation data may be reconsidered only after a specific residual failure is isolated and a bounded incremental-value test justifies cost.

## Research hardening completed in closeout

- explicit evidence-quality classification for peer-reviewed, technical/open-source, practitioner and opaque sources;
- deeper David Sasser review with product observations separated from reproducible evidence;
- deterministic candidate-specific nested chronology/tie-breaking;
- A0/A1 boundary tightened;
- independent B0 reference required;
- C0 reduced to Ridge-only; no tree fallback;
- four-arm market-null hierarchy frozen;
- feature-source/PIT feasibility matrix frozen;
- D ensemble gate tightened;
- 2025 holdout caveat red-teamed and retained.

## Exact next action before Phase 2 can become COMPLETE

1. Run/observe **fresh exact-head** \`LevLine research firewall\` and full \`LevLine research validation\` on PR #520 after the final control-file commit.
2. Fix only genuine defects; never weaken the firewall.
3. If both exact-head checks pass, mark PR #520 ready for review and merge it.
4. Verify the merged Phase 2 artifacts directly from \`main\`.
5. Record the merge SHA and exact CI run IDs in these control files on \`main\`.
6. Leave Phase 3 **NOT STARTED** and stop.

## DO NOT REPEAT

- Do not rerun Phase 1.
- Do not redo the entire Phase 2 literature/external-model review.
- Do not broaden the model search after seeing results.
- Do not inspect 2025 challenger outcomes during Phase 3.
- Do not use completed 2026 outcomes for candidate selection.
- Do not call historical closing/late market data T-120.
- Do not use final starter/injury/weather state without PIT proof.
- Do not force an ensemble.
- Do not force player features.
- Do not add paid data without the documented escalation gate.
- Do not revive retired Props orchestration.
- Do not weaken F-ST production safeguards.
- Do not treat David Sasser public record claims as validation without reconstructable methodology/chronology.
- Do not convert failed A0/B0/C0 references into an unconstrained rescue search under the same candidate identity.

## Phase 3 handoff — prepare only, do not execute here

Once Phase 2 is formally complete, the next chat should:

1. read the canonical control files and Phase 2 artifacts from current main;
2. build shared chronology-safe data/evaluation scaffolding;
3. implement A0 reference;
4. implement independent B0 bounded drive model;
5. implement C0 Ridge residual reference and M0/M1/M2/M3 null hierarchy;
6. run development OOS evaluation through 2024 only;
7. run only the frozen A0/B0/C0 reference implementations and required null/diagnostic comparisons; do not open deferred A1/B-alternative/C-nonlinear searches;
8. determine D eligibility only from the frozen numeric gate;
9. freeze candidate identities;
10. **do not score 2025**;
11. stop for Phase 4.

No Phase 3 code or challenger output belongs in Phase 2.

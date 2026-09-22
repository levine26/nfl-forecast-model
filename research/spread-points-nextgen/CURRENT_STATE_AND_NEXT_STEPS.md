# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-22 America/Los_Angeles  
**Program authority:** \`research/spread-points-nextgen/MASTER_PLAN.md\`  
**Phase 0:** **COMPLETE**  
**Phase 1:** **COMPLETE**  
**Phase 2:** **COMPLETE**  
**Phase 3:** **NOT STARTED**  
**Completed branch:** \`research/spread-points-nextgen-phase2\`  
**Merged PR:** #520  
**Merge SHA:** \`405906942013252c158244c9b033a3240baa37f8\` — merged at `405906942013252c158244c9b033a3240baa37f8`

## Phase 2 state

Phase 2 research/design is **COMPLETE**. It passed hostile methodological review, exact-head firewall/validation, merge verification, and post-merge artifact verification. No Phase 3 challenger has been implemented and no A/B/C 2025 challenger result has been inspected.

The branch was repeatedly synchronized with concurrent `main` as unrelated work advanced. The final pre-merge synchronization preserved adaptive Candidate 2 closeout state through `e93127963c76cd309cdddf17d91291c04a60a659`; the final Phase 2 head was `076dc9d6f6c052eec4744a155070c42c1b99ae82`. Concurrent adaptive, Sunday Signal, T-120 shadow, and generated-output work remained provenance-only and was not used to select or redefine Spread & Points challengers.

## Frozen initial Phase 3 shortlist

- **A — Dynamic Opponent-Adjusted Joint Score:** football-only. Initial identity is bounded A0: time-decayed, partially pooled offense/defense score model.
- **B — Possession / Drive Score Process:** football-only. Independent B0 must model possessions plus TD/FG/empty drive outcomes without consuming A0 predictions. No B+A sensitivity is part of the initial Phase 3 search.
- **C — Market Residual Margin / Total:** market-aware. Initial C0 is Ridge-only and must report M0 market-only, M1 line-calibration-only, M2 football-residual, and M3 full residual arms.
- **D — Ensemble / reconciliation:** conditional only. For a target, do not build unless abs error correlation is <0.90, pooled 2022–2024 convex-blend MAE improves by >=0.10 points, both 2023 and 2024 improve, and season+week block-bootstrap P(improvement) is >=0.75.

A1 explicit state-space expansion, player/QB/personnel overlays, and weather are **not** automatically authorized initial extensions.

## Frozen chronology

Historical training floor for A0/B0/C0 is **2016 regular season**. Inner validation targets begin in **2019**. Phase 3 may not search alternate training-start years for better performance.

Development outer targets are exactly:

- 2022 — prior seasons only;
- 2023 — prior seasons only;
- 2024 — prior seasons only.

For each outer target, use expanding prior-only inner folds with training history beginning in **2016** and validation season **V >= 2019**. Use the **latest four eligible inner validation seasons**, or all eligible folds when fewer are available. If fewer than two eligible folds exist because a required source lacks coverage, use the candidate's frozen fallback rather than borrowing later data. All preprocessing, latent-state construction, residual variance/covariance estimation and tuning are training-only.

Final historical challenger holdout:

- **2025** — open once in Phase 4 only after candidate identities freeze.

Completed 2026 outcomes:

- **zero permitted for architecture, features, tuning, thresholds, stacking, survival, or candidate selection.**

Phase 1 did inspect baseline 2025 failures, so 2025 is not philosophically pristine. No A/B/C output existed then. This caveat remains mandatory. Phase 5 now performs Candidate 5 historical F-ST-anchored integration, and Phase 6 prospective evidence remains mandatory before any promotion claim.

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
- deterministic fixed-2016 nested chronology/tie-breaking;
- A0/A1 boundary tightened;
- independent B0 reference required;
- C0 reduced to Ridge-only; no tree fallback;
- four-arm market-null hierarchy frozen;
- feature-source/PIT feasibility matrix frozen;
- D ensemble gate tightened;
- 2025 holdout caveat red-teamed and retained.

## Phase 2 completion receipt

- exact-head research firewall `35751402751`: **SUCCESS**
- exact-head full research validation `35751402726`: **SUCCESS**
- validated head: `076dc9d6f6c052eec4744a155070c42c1b99ae82`
- synchronized pre-merge main: `e93127963c76cd309cdddf17d91291c04a60a659`
- PR #520: **MERGED**
- merge commit: `405906942013252c158244c9b033a3240baa37f8`
- canonical Phase 2 artifacts and control files: **verified directly from main after merge**
- production behavior: **unchanged**
- Phase 3: **NOT STARTED**

## Program amendment — future Candidate 5 integration

A governance amendment adds a new downstream integration phase without changing the immediate execution path:

- **Phase 5 — Historical F-ST-Anchored Winner Integration**
- working candidate ID: `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`;
- primary form: strongly regularized logistic residual/offset around frozen F-ST;
- primary component inputs: chronology-clean OOF A0/B0 outputs and compact uncertainty/disagreement summaries;
- market-aware C0 information remains a separately labeled historical diagnostic unless same-horizon market receipts exist;
- all stack inputs must be genuine OOF predictions for their game;
- 2025 is an underlying-component holdout and must not be misrepresented as a pristine Candidate 5 holdout;
- honest Candidate 5 historical development evidence should come from nested chronology/OOF component surfaces, principally 2022-2024;
- prospective Phase 6 evidence is mandatory for promotion;
- expected +0.4 to +0.8 percentage-point uplift is a **pre-result research prior only**, never an optimization target or promise.

The amendment reflects the Adaptive Weekly Learning evidence:

- Candidate 1 generic residual learning was rejected (722/1,087; ~-1.75 pp vs F-ST; 42.15% switch accuracy; worse Brier/log loss);
- naive weekly F-ST refitting was rejected (739/1,087; ~-0.184 pp);
- calibration-only preserved all 741 winners and produced only tiny proper-score gains;
- Candidate 2 was inconclusive/sparse;
- Candidate 3 was inconclusive and did not establish market-path information beyond market level;
- Candidate 4 remains a frozen, independent prospective experiment and does **not** block the Spread & Points program.

Candidate 4 may continue collecting clean prospective PIT market/QB evidence. Its outcomes may not tune Candidate 5 V1; any later personnel/market extension requires a separately versioned Candidate 5.x contract.

An earlier unmerged Phase 3 startup-only branch may exist, but canonical `main` remains authoritative: Phase 3 is **NOT STARTED** until substantive Phase 3 work is merged/recorded through the normal program controls. This governance amendment does not start or implement Phase 3.

The roadmap is now:

Phase 0 complete -> Phase 1 complete -> Phase 2 complete -> **Phase 3 controlled implementation -> Phase 4 historical validation/underlying 2025 holdout -> Phase 5 Candidate 5 historical integration -> Phase 6 prospective shadow/hardening -> Phase 7 final synthesis/promotion package**.

## Exact next action

**STOP Phase 2.** In the next Phase 3 execution chat, read the merged control files and canonical Phase 2 artifacts from current `main`, then implement only the frozen Phase 3 program below. Do not reopen Phase 1/2 merely because the chat is new.

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
- Do not start Candidate 5 before Phase 4 is complete.
- Do not independently rebuild A0/B0/C0 inside Candidate 5; consume frozen OOF component surfaces.
- Do not wait for Candidate 4 to mature before continuing Spread & Points Phases 3-5.
- Do not use Candidate 4 outcomes to tune Candidate 5.
- Do not use in-sample A0/B0/C0/D predictions as Candidate 5 stack inputs.
- Do not call 2025 a pristine Candidate 5 holdout merely because it was the underlying-model holdout.

## Phase 3 handoff — prepare only, do not execute here

Once Phase 2 is formally complete, the next chat should:

1. read the canonical control files and Phase 2 artifacts from current main;
2. build shared chronology-safe data/evaluation scaffolding;
3. implement A0 reference;
4. implement independent B0 bounded drive model;
5. implement C0 Ridge residual reference and M0/M1/M2/M3 null hierarchy;
6. run development OOS evaluation through 2024 only;
7. run only the frozen A0/B0/C0 reference implementations and required null/diagnostic comparisons; do not open deferred A1/B-alternative/C-nonlinear searches;
8. determine D eligibility only from the frozen strict target-specific gate (correlation <0.90, pooled gain >=0.10 MAE, improvement in both 2023 and 2024, bootstrap probability >=0.75);
9. freeze candidate identities;
10. **do not score 2025**;
11. stop for Phase 4.

No Phase 3 code or challenger output belongs in Phase 2.

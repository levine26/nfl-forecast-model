# CURRENT STATE AND NEXT STEPS

Program: `LEVLINE_ATS_FRONTIER_V2`

## Current state

Phases 1, 2 and 3 are complete.

Phase 4 has completed its accepted scientific execution and immutable evidence preservation, but repository closeout is still in progress:

`PHASE4 = EVIDENCE_COMPLETE__PENDING_REPOSITORY_MERGE`

`PHASE5 = NOT_STARTED`

Production remains `F-ST-01-FROZEN-2026` and is unchanged.

Completed-2026 outcomes used in Phase 4: `0`.

Historical market label remains:

`HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`

## Accepted Phase-4 provenance

Canonical accepted workflow run: `36025306390`.

Artifact: `10820230932` (`ats-frontier-v2-phase4-36025306390`).

Validated scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`.

Accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`.

Config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`.

Dataset identity SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

The prior workflow run `36023376614` is superseded and explicitly unaccepted because pre-acceptance contract review found implementation/reporting defects. Those defects were corrected without changing the frozen hypotheses, then re-gated before the accepted run.

## M3 evidence

Candidate: `FV2-HIST-M3-DSSM-01`.

Null: `M3-NULL-MARKET-NORMAL-01`.

Phase-4 evidence label: `NEGATIVE_PRIMARY_EVIDENCE`.

- OOF/common N: `1087`.
- candidate primary log loss: `0.7811502028797036`.
- null primary log loss: `0.7804795705044401`.
- paired candidate-minus-null delta: `+0.0006706323752636537` (higher is worse).
- 10,000 week-block bootstrap 95% interval: `[-0.00031937461835433695, +0.001655686764502027]`.
- descriptive probability delta is favorable: `0.0889`.
- per-season deltas: 2022 `+0.0023128`; 2023 `+0.0000905`; 2024 `+0.0001692`; 2025 `+0.0001160` — unfavorable in all four seasons.
- static-state log loss: `0.7814028169431046`; dynamic full improves static by about `0.0002526` but still fails the market null.
- dynamic-no-QB log loss: `0.7808845344047226`; adding QB worsens the full model by about `0.0002657`.
- calibration intercept/slope: `-0.0008003 / -1.40645`.
- ATS diagnostic: `518-540-29`, ex-push hit rate `48.96%`; `REFERENCE_MINUS110` sensitivity `-6.53%` ROI on risked units; no actual historical ROI is claimed.

M3 did not demonstrate tangible incremental information beyond its market null in Phase 4.

## M4 evidence

Candidate: `FV2-HIST-M4-DMARGIN-01`.

Null: `M4-NULL-STUDENTT-CONSTANT-01`.

Phase-4 evidence label: `POSITIVE_PRIMARY_EVIDENCE`.

- OOF/common N: `1087`.
- candidate integer-margin log score: `3.85297516860494`.
- null integer-margin log score: `3.9356468604011363`.
- paired candidate-minus-null delta: `-0.08267169179619614` (lower is better).
- 10,000 week-block bootstrap 95% interval: `[-0.10748699203380639, -0.057962887776498655]`.
- descriptive probability delta is favorable: `1.0`.
- per-season deltas: 2022 `-0.081388`; 2023 `-0.081155`; 2024 `-0.067786`; 2025 `-0.100354` — favorable in all four seasons.
- conditional-scale-only contribution versus null: `+0.0001251` (slightly worse).
- key-mass-only contribution versus null: `-0.0827184` (essentially the entire gain).
- full minus constant-scale-key: `+0.0000467`, so the full model is very slightly worse than the simpler preregistered key-mass ablation.
- calibration intercept/slope: `0.0147701 / 0.4366584`.
- ranked probability score: `6.9151236594419325`.
- ATS diagnostic: `540-518-29`, ex-push hit rate `51.04%`; `REFERENCE_MINUS110` sensitivity `-2.56%` ROI on risked units; no actual historical ROI is claimed.
- PMF/tail numerical audit: `PASS`; no finite support and no endpoint folding.

M4 demonstrated tangible distributional improvement versus the strong null on the primary proper score, consistently across all four seasons. The ablation attribution is crucial: the gain is a key-mass representation effect, not evidence that the conditional-scale component adds value. Formal survivor classification remains Phase 5.

## Red-team / firewall state

Red-team audit: `PASS`.

Exact common rows: `1087` for both M3 and M4; zero missing market rows in the evaluated outer population.

No target-game PBP, future state, eventual target QB identity, completed-2026 outcome, expanded hyperparameter grid, post-result feature/distribution change, threshold fishing, tail truncation or endpoint folding entered the accepted evidence.

## Next repository actions — still Phase 4

1. Resolve current live `main` and reconcile unrelated advances.
2. Confirm the Phase-4 branch contains only research/governance/workflow changes and leaves protected production surfaces unchanged.
3. Open the Phase-4 primary PR.
4. Require exact-head `LevLine research firewall` and `LevLine research validation` success (and any Phase-4 exact-run gate triggered by the PR).
5. Merge the primary PR only if the exact validated head remains clean.
6. Verify merged `main`.
7. From that primary merge, create the closeout branch and write `FINAL_PHASE4_RECEIPT.md` plus final Phase-4 status ledgers.
8. Require exact-head closeout CI, merge the closeout PR, verify final `main`, and stop.

## Exact Phase-5 starting action — do not execute yet

Read the immutable accepted Phase-4 evidence package, verify exact provenance/hashes and red-team PASS, then apply the frozen `EVALUATION_PROTOCOL.md` Phase-5 classification criteria to M3 and M4 independently using only the accepted OOF, paired bootstrap, calibration, ablation and stability evidence. Do not refit, redesign, recompute candidates, introduce rescue candidates, construct an M3+M4 combination, or begin prospective shadowing before survivor classification is complete.

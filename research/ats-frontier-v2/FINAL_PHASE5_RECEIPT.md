# FINAL PHASE 5 RECEIPT

Program: `LEVLINE_ATS_FRONTIER_V2`

Phase: **5 — Scientific synthesis, candidate classification & survivor freeze**

Final state: `COMPLETE`

Historical Phase-6 state at close: `NOT_AUTHORIZED`

## Repository provenance

Primary Phase-5 branch: `research/ats-frontier-v2-phase5`.

Opening live `main`: `5e93d8c274ae3edf18689e6a36d8d049d3104b33`.

Primary Phase-5 PR: `#578` — **Classify ATS Frontier V2 Phase 5 candidates**.

Exact validated Phase-5 PR head: `53e8420fabf0ecd9b2b9753a65e9cd27c3e1e72c`.

Primary Phase-5 merge SHA: `f6c1b62690c069f6b3e3ef1d8bf721bddcdeef4b`.

Primary merge timestamp: `2026-09-24T18:29:28Z`.

Primary merge was independently verified on live `main` before this closeout receipt was written.

Closeout branch: `research/ats-frontier-v2-phase5-closeout`, created from the verified primary merge.

## Exact-head CI evidence

All relevant exact-head workflows completed successfully on `53e8420fabf0ecd9b2b9753a65e9cd27c3e1e72c`:

- `LevLine research firewall` — run `36040603014`: `SUCCESS`.
- `LevLine research validation` — run `36040602757`: `SUCCESS`; foundation, v0.8 isolated regeneration, paired statistical uncertainty audit, margin-disagreement forensics, Phase-2 market-reliance/horizon study, production-surface proofs, and aggregate validation gate all passed.
- `ATS Frontier V2 Phase 4 pre-result gate` — run `36040602883`: `SUCCESS`.

The primary Phase-5 diff changed only `research/ats-frontier-v2/**`. Production forecasting surfaces were not modified.

## Canonical Phase-4 evidence bound into Phase 5

Phase-4 primary PR: `#576`.

Exact validated Phase-4 PR head: `93ed709d24d53d8469f6bc7eaaf49d2a38d7cea3`.

Phase-4 primary merge: `e425220c1b929629f3a5420bc1915c74835b2a34`.

Canonical Phase-4 workflow/artifact: `36025444929` / `10820397832`.

Canonical artifact digest independently verified in Phase 5: `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`.

Accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`.

Config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`.

Dataset SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

M3 OOF SHA-256 independently verified: `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`.

M4 OOF SHA-256 independently verified: `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`.

Workflow `36023376614` remains `INVALID / NOT ACCEPTED` and supplied no Phase-5 metric or conclusion.

Workflow `36025306390` remains a valid reproducibility check only; it was not substituted for the canonical package.

Completed-2026 outcomes used: `0`.

## Permitted Phase-5 null-calibration synthesis

The only new evidence calculation was the explicitly authorized null-side calibration diagnostic from already-preserved canonical OOF probabilities, using the frozen `phase4_core.py::calibration_report` definition. No model fitting, recalibration, prediction regeneration, tuning, architecture change, or outcome-dependent transform was performed.

### M3 null calibration

- non-push rows: `1058`;
- null intercept: `0.0`;
- null slope: `0.0`;
- candidate intercept: `-0.0008002656550699535`;
- candidate slope: `-1.4064471514780361`;
- absolute-intercept worsening: `0.0008002656550699535` — below `0.03`;
- slope-departure-from-1 worsening: `1.406447151478036` — above `0.10`.

Conclusion: M3 is materially degraded versus null under the frozen slope-calibration rule. The exception is unavailable because M3 does not have a significant primary-score improvement.

### M4 null calibration

- non-push rows: `1058`;
- null intercept: `0.0`;
- null slope: `0.0`;
- candidate intercept: `0.01477013532177962`;
- candidate slope: `0.4366590498000353`;
- absolute-intercept worsening: `0.01477013532177962` — below `0.03`;
- slope departure from 1 improves from `1.0` to `0.5633409501999647`.

Conclusion: M4 passes the frozen calibration-relative gate without an exception.

## M3 final Phase-5 disposition

Candidate: `FV2-HIST-M3-DSSM-01`.

Null: `M3-NULL-MARKET-NORMAL-01`.

Final classification: **`REJECTED`**.

Accepted evidence:

- common OOF rows: `1087`;
- candidate CPL log loss: `0.7811502028797036`;
- null CPL log loss: `0.7804795705044401`;
- candidate-minus-null: `+0.0006706323752636532`;
- 95% week-block interval: `[-0.00031937461835433245, +0.0016556867645020252]`;
- descriptive probability favorable: `0.0889`;
- primary delta unfavorable in 2022, 2023, 2024 and 2025;
- `DYNAMIC_NO_QB` outperformed the full candidate; adding QB worsened the primary score by `+0.0002656684749809774`;
- chronology/leakage/red-team audit: `PASS`;
- ATS diagnostic: `518-540-29`, `48.96%` ex-push, diagnostic only.

Frozen rules triggering rejection:

1. the M3-specific preregistered failure condition is triggered because `DYNAMIC_FULL` fails to improve paired primary proper score versus `MARKET_ONLY`;
2. the frozen Phase-5 worse-than-null/futility rejection rule applies to the unfavorable point estimate with week-block uncertainty leaving only a small near-zero favorable tail and excluding a practically meaningful improvement for this frozen candidate/null comparison;
3. independently, M3 fails the Phase-5 calibration eligibility gate because slope calibration is materially degraded versus null.

No no-QB rescue, state expansion, process-variance change, market-treatment change, distribution switch, ATS rescue, or recalibration was used.

## M4 final Phase-5 disposition

Candidate: `FV2-HIST-M4-DMARGIN-01`.

Null: `M4-NULL-STUDENTT-CONSTANT-01`.

Final classification: **`REJECTED`**.

Accepted evidence:

- common OOF rows: `1087`;
- candidate integer-margin log score: `3.852975162486858`;
- strong-null integer-margin log score: `3.935646861629811`;
- candidate-minus-null: `-0.08267169914295289`;
- 95% week-block interval: `[-0.10748698706212485, -0.05796293485132338]`;
- descriptive probability favorable: `1.0`;
- favorable primary delta in all four outer seasons;
- numerical audit: `PASS`;
- tail audit: `PASS`;
- calibration-relative gate: `PASS`;
- ATS diagnostic: `540-518-29`, `51.04%` ex-push, diagnostic only.

Decisive frozen ablation evidence:

- `CONDITIONAL_SCALE_NO_KEY - null`: `+0.00012506107970626913` — slightly worse;
- `CONSTANT_SCALE_KEY - null`: `-0.08271839184340689` — reproduces essentially the entire gain;
- `FULL_CONDITIONAL_SCALE_KEY - CONSTANT_SCALE_KEY`: `+0.00004669270045401389` — the full candidate is slightly worse than the simpler preregistered key-mass ablation.

Frozen rule triggering rejection:

- the `EVALUATION_PROTOCOL.md` rejection clause applies because the claimed full mechanism contains a component that contributes no improvement while a simpler preregistered component reproduces the result.

Phase 5 explicitly answers the required M4 ablation question: **YES, the simpler-preregistered-ablation rejection clause applies to `FV2-HIST-M4-DMARGIN-01`.**

The M4 mechanism was not redefined after observing results.

## Key-mass scientific finding

`CONSTANT_SCALE_KEY` is recorded as **`FUTURE_VERSION_HYPOTHESIS_ONLY`**.

It is not `M4-V2`, not `FV2-HIST-M4-KEY`, not a historical survivor, and not Phase-6 authorized. The evidence supports a future hypothesis about discrete NFL scoring/key-number representation only.

Any future key-mass-only candidate requires a new identity, new preregistration, fresh governance, and a legitimate future validation path. The 2022–2025 development result cannot be backdated into confirmatory evidence for that future candidate.

## Historical survivor and Phase-6 authorization

Historical Phase-5 survivor count: `0`.

Historical Frontier Phase-6 authorization: **`NONE`**.

No historical-survivor prospective-shadow protocol was created because no M3/M4 candidate is `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

Phase 7 remains unavailable for a historical Frontier survivor.

## M1/M2 prospective status

The historical Phase-5 decision does not reopen or cancel the separately frozen prospective-only identities:

- `FV2-PROS-M1-MARKETSTATE-01` — historical reconstruction remains blocked; prospective point-in-time market-state data capture/research remains legitimate under its existing contracts.
- `FV2-PROS-M2-QBDELTA-01` — prospective-only expected-QB-value information-delta research remains legitimate under its existing contracts.

Neither is combined with M3 or M4 and neither is represented as a historical Phase-5 survivor.

## Scientific synthesis preserved

V2 learned:

- the frozen compact dynamic offense/defense/QB market-correction candidate did not establish incremental historical proper-score information beyond the market benchmark;
- within frozen M3, the QB state worsened primary score relative to the no-QB ablation;
- explicit discrete integer-margin key-number mass at 0/|3|/|7| produced a strong historical representation signal;
- the tested conditional-scale mechanism did not add value and slightly degraded the simpler key-mass representation;
- historical dynamic market-state research remains blocked by point-in-time data qualification, while prospective M1 capture remains scientifically legitimate;
- negative findings are preserved and no post-result combination or rescue was created.

These development-set findings do not establish a durable betting edge or production readiness.

## Firewalls preserved at close

- completed-2026 outcomes used: `0`;
- new model fitting in Phase 5: `NO`;
- retuning/recalibration: `NO`;
- new candidate/rescue candidate: `NO`;
- M3+M4 combination/ensemble: `NO`;
- prospective shadow execution: `NO`;
- ATS/ROI used to select a survivor: `NO`;
- production changed: `NO`.

Production remains `F-ST-01-FROZEN-2026`. Sunday Signal numerical forecasts, official fair spreads, winner probabilities, score projections, ATS picks, history, grading and deployment remain unchanged by Phase 5.

## Final phase state

- Phase 1: `COMPLETE`
- Phase 2: `COMPLETE`
- Phase 3: `COMPLETE`
- Phase 4: `COMPLETE`
- Phase 5: `COMPLETE`
- Phase 6: `NOT_AUTHORIZED` for historical M3/M4 Frontier candidates
- Phase 7: `NOT_STARTED` / unavailable for a historical Frontier survivor

## Exact next authorized action

Do **not** start historical M3/M4 Phase 6.

The next scientifically legitimate work is limited to either:

1. continuing already-governed prospective M1/M2 point-in-time data capture/research under their existing identities and contracts; or
2. opening a separately governed future-version research program for a new key-mass-only candidate with a new identity, preregistration, and legitimate future validation path.

No refit, rescue, historical composition, completed-2026 retrospective design look, or production modification is authorized by this closeout.

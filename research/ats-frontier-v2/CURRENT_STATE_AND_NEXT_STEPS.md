# CURRENT STATE AND NEXT STEPS

Program: `LEVLINE_ATS_FRONTIER_V2`

## Current state

Phases 1–5 are `COMPLETE`.

Phase 5 was merged through primary PR `#578` after all exact-head research gates passed, and the immutable closeout is recorded in `FINAL_PHASE5_RECEIPT.md`.

- M3 `FV2-HIST-M3-DSSM-01`: `REJECTED`.
- M4 `FV2-HIST-M4-DMARGIN-01`: `REJECTED`.
- historical survivor count: `0`.
- historical Phase-6 authorization: `NONE`.
- Phase 6: `NOT_AUTHORIZED` for M3/M4.
- Phase 7: unavailable for a historical Frontier survivor.

Production remains `F-ST-01-FROZEN-2026` and unchanged.

Completed-2026 outcomes used: `0`.

Historical market label remains `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`.

## Phase-5 repository provenance

- opening live `main`: `5e93d8c274ae3edf18689e6a36d8d049d3104b33`;
- primary branch: `research/ats-frontier-v2-phase5`;
- primary PR: `#578`;
- exact validated Phase-5 head: `53e8420fabf0ecd9b2b9753a65e9cd27c3e1e72c`;
- primary merge: `f6c1b62690c069f6b3e3ef1d8bf721bddcdeef4b`;
- exact-head firewall run `36040603014`: `SUCCESS`;
- exact-head research-validation run `36040602757`: `SUCCESS`;
- exact-head ATS Frontier safety run `36040602883`: `SUCCESS`.

The primary Phase-5 diff was restricted to `research/ats-frontier-v2/**`. Production forecasting surfaces were not modified.

## Canonical Phase-4 evidence provenance

Phase-4 primary PR `#576`, validated head `93ed709d24d53d8469f6bc7eaaf49d2a38d7cea3`, merge `e425220c1b929629f3a5420bc1915c74835b2a34`.

Canonical scientific workflow/artifact: `36025444929` / `10820397832`.

Artifact digest independently verified in Phase 5: `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`.

Accepted code/config/data hashes remain `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`, `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`, and `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

Canonical OOF hashes independently verified: M3 `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`; M4 `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`.

Workflow `36023376614` remains invalid/unaccepted. Workflow `36025306390` remains a reproducibility check only.

## Phase-5 calibration synthesis

Using the frozen `phase4_core.py::calibration_report` on canonical preserved OOF probabilities only:

- M3 null intercept/slope: `0.0 / 0.0`.
- M3 candidate: `-0.0008002656550699535 / -1.4064471514780361`; slope-departure worsening `1.406447151478036` > `0.10`, so calibration is materially degraded.
- M4 null intercept/slope: `0.0 / 0.0`.
- M4 candidate: `0.01477013532177962 / 0.4366590498000353`; intercept worsening stays below `0.03` and slope departure improves, so the calibration-relative gate passes.

No probabilities were recalibrated or changed.

## M3 final disposition

M3's candidate primary log loss `0.7811502028797036` is worse than market-null `0.7804795705044401`; delta `+0.0006706323752636532`. Its 95% week-block interval is `[-0.00031937461835433245, +0.0016556867645020252]`, only `8.89%` of bootstrap draws favor the candidate, and every outer season is unfavorable. `DYNAMIC_NO_QB` also outperforms the full candidate, so the QB component is negative evidence rather than a rescue candidate.

Final classification: `REJECTED` under the frozen M3 failure condition and Phase-5 rejection/futility rule. M3 also materially degrades null-relative slope calibration. ATS `518-540-29` is diagnostic only.

## M4 final disposition

M4's full candidate improves the strong null by `-0.08267169914295289`, with 95% interval `[-0.10748698706212485, -0.05796293485132338]`, favorable direction in all four seasons, numerical/tail/red-team `PASS`, and a passing calibration-relative gate.

But `CONDITIONAL_SCALE_NO_KEY` is slightly worse than null (`+0.00012506107970626913`), while preregistered `CONSTANT_SCALE_KEY` reproduces slightly more than the full gain (`-0.08271839184340689` versus null; full-minus-key `+0.00004669270045401389`). The frozen simpler-ablation rejection clause therefore applies.

Final classification: `REJECTED`. ATS `540-518-29` is diagnostic only.

## Future-version evidence and prospective identities

`CONSTANT_SCALE_KEY` is `FUTURE_VERSION_HYPOTHESIS_ONLY`. It is not M4-v2, not a Phase-5 survivor, and not Phase-6 authorized. A future key-mass-only candidate requires a new identity, preregistration, fresh governance, and a legitimate future validation path.

Existing prospective-only identities remain separate and unchanged:

- `FV2-PROS-M1-MARKETSTATE-01` — historical reconstruction remains blocked; existing prospective market-state capture/research may continue under its contracts.
- `FV2-PROS-M2-QBDELTA-01` — prospective-only QB information-delta research remains under its contracts.

## Exact next authorized action

Do not start historical M3/M4 Phase 6. The only next scientific work authorized by this program state is already-governed prospective M1/M2 point-in-time data capture/research, or a separately governed future-version program with a new preregistered key-mass-only candidate identity and a legitimate future validation path.

Do not refit, rescue, combine M3/M4, inspect completed-2026 outcomes for retrospective design, or modify production.
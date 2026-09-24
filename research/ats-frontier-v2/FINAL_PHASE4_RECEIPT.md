# FINAL PHASE 4 RECEIPT

Program: `LEVLINE_ATS_FRONTIER_V2`

Phase: **4 — Controlled historical development, ablation & empirical validation**

Final state: `COMPLETE`

Phase 5 state at close: `NOT_STARTED`

## Repository provenance

Primary Phase-4 PR: `#576` — **Complete ATS Frontier V2 Phase 4 historical evidence**.

Exact validated PR head: `93ed709d24d53d8469f6bc7eaaf49d2a38d7cea3`.

Primary merge SHA: `e425220c1b929629f3a5420bc1915c74835b2a34`.

Primary merge was verified on live `main` before this closeout branch was created.

Exact-head PR validation on `93ed709d24d53d8469f6bc7eaaf49d2a38d7cea3`:

- `LevLine research firewall` run `36030756862`: `SUCCESS`.
- `LevLine research validation` run `36030756719`: `SUCCESS`; every parallel validation lane and the aggregate research-validation gate passed.
- `ATS Frontier V2 Phase 4 pre-result gate` run `36030756851`: `SUCCESS`; compilation, result-blind contract tests, corrected preflight, literal completed-2026 firewall, and protected-production-surface proof all passed.

The final PR diff was restricted to Phase-4 research/governance/workflow surfaces after unrelated live-output refresh files were reconciled back to current `main`.

## Canonical accepted scientific execution

Final canonical workflow run: `36025444929`.

Artifact: `10820397832` (`ats-frontier-v2-phase4-36025444929`).

Artifact digest: `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`.

Execution commit: `7eda9cacd471a3161424699958509c02a260fc05`.

Validated scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`.

Accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`.

Config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`.

Dataset identity SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

M3 OOF SHA-256: `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`.

M4 OOF SHA-256: `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`.

Bootstrap seed: `20260924`.

Bootstrap resamples: `10000`, season-stratified NFL-week blocks.

Completed-2026 outcomes used: `0`.

Production forecasting behavior changed: `NO`.

Red-team audit: `PASS`.

Historical market label: `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`.

## Execution provenance correction

Workflow run `36023376614` remains `INVALID / NOT ACCEPTED`. Its metrics are excluded from the scientific record because pre-acceptance contract review identified static-ablation, market-missing state-update, and required M4 diagnostic implementation/reporting defects.

Workflow run `36025306390` is retained as a successful corrected reproducibility execution. It is scientifically consistent with the final canonical package but not byte-identical. M3's primary delta differs only at machine precision; M4's paired primary delta differs by approximately `7.35e-9`. Selected hyperparameter identities, row counts, per-season effect direction, uncertainty conclusion, ablation attribution, and Phase-4 evidence labels are unchanged. No result shopping occurred.

## M3 accepted Phase-4 evidence

Candidate: `FV2-HIST-M3-DSSM-01`.

Null: `M3-NULL-MARKET-NORMAL-01`.

Phase-4 technical evidence label: `NEGATIVE_PRIMARY_EVIDENCE`.

- Common OOF rows: `1087`.
- Candidate CPL log loss: `0.7811502028797036`.
- Market-null CPL log loss: `0.7804795705044401`.
- Paired candidate-minus-null delta: `+0.0006706323752636532` (higher is worse).
- 95% week-block interval: `[-0.00031937461835433245, +0.0016556867645020252]`.
- Primary delta was unfavorable in all four outer seasons.
- Dynamic-no-QB ablation outperformed the full M3 model; adding QB worsened primary score by approximately `0.0002657`.
- ATS diagnostic only: `518-540-29`, `48.96%` ex-push.

Phase 4 therefore found no tangible incremental proper-score information for M3 beyond its market null. This is an evidence statement, not the formal Phase-5 survivor classification.

## M4 accepted Phase-4 evidence

Candidate: `FV2-HIST-M4-DMARGIN-01`.

Null: `M4-NULL-STUDENTT-CONSTANT-01`.

Phase-4 technical evidence label: `POSITIVE_PRIMARY_EVIDENCE`.

- Common OOF rows: `1087`.
- Candidate integer-margin log score: `3.852975162486858`.
- Strong-null integer-margin log score: `3.935646861629811`.
- Paired candidate-minus-null delta: `-0.08267169914295289` (lower is better).
- 95% week-block interval: `[-0.10748698706212485, -0.05796293485132338]`.
- Primary delta was favorable in all four outer seasons.
- `CONSTANT_SCALE_KEY` reproduced essentially the entire primary gain: key-mass-only contribution versus null `-0.08271839184340689`.
- Conditional scale alone was slightly worse than the strong null: `+0.00012506107970626913`.
- Full M4 was slightly worse than the simpler `CONSTANT_SCALE_KEY` ablation by `+0.00004669270045401389`.
- PMF/tail numerical audit: `PASS`.
- ATS diagnostic only: `540-518-29`, `51.04%` ex-push.

Phase 4 therefore found strong distributional evidence for the discrete key-mass representation, not evidence that the conditional-scale component adds value. Formal survivor classification remains Phase 5.

## Boundaries preserved at close

- No Phase-5 `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` classification was applied.
- No M3+M4 combination was constructed.
- No rescue candidate, post-result calibration rescue, threshold search, or selective betting subset was introduced.
- Historical M1/M2 were not resurrected.
- ATS and `REFERENCE_MINUS110` remained diagnostics only; no actual historical ROI claim was created.
- Completed-2026 outcomes remained sealed from Phase 4.
- Production remains `F-ST-01-FROZEN-2026`.

## Authorized next action

Phase 4 is closed. The next program action, only when Phase 5 is explicitly begun, is to read this receipt plus the immutable canonical Phase-4 evidence package and apply the frozen `EVALUATION_PROTOCOL.md` Phase-5 survivor criteria to M3 and M4 independently. Do not refit, redesign, recompute candidates, introduce rescue candidates, combine M3+M4, or begin prospective shadowing before that classification is complete.

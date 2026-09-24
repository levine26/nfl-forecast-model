# CURRENT STATE AND NEXT STEPS

Program: `LEVLINE_ATS_FRONTIER_V2`

## Current state

Phases 1, 2, 3 and 4 are complete.

`PHASE4 = COMPLETE`

`PHASE5 = NOT_STARTED`

Production remains `F-ST-01-FROZEN-2026` and unchanged.

Completed-2026 outcomes used in Phase 4: `0`.

Historical market label remains:

`HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`

## Final Phase-4 repository provenance

Primary PR: `#576`.

Exact validated PR head: `93ed709d24d53d8469f6bc7eaaf49d2a38d7cea3`.

Primary merge SHA: `e425220c1b929629f3a5420bc1915c74835b2a34`.

Exact-head gates all passed:

- research firewall `36030756862`.
- research validation `36030756719`.
- Phase-4 frozen/pre-result gate `36030756851`.

The final PR diff was restricted to Phase-4 research/governance/workflow files after unrelated live-output refresh files were restored from current `main`.

## Final canonical scientific provenance

Canonical workflow run: `36025444929`.

Artifact: `10820397832` (`ats-frontier-v2-phase4-36025444929`).

Artifact digest: `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`.

Execution commit: `7eda9cacd471a3161424699958509c02a260fc05`.

Validated scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`.

Accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`.

Config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`.

Dataset identity SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

M3 OOF SHA-256: `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`.

M4 OOF SHA-256: `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`.

Corrected workflow run `36025306390` is preserved as a successful reproducibility execution. It is scientifically consistent with the canonical package but not byte-identical; the M4 paired primary delta differs by approximately `7.35e-9` with no change in evidence direction, selected hyperparameters, row counts, per-season sign pattern, uncertainty conclusion, or ablation attribution.

Workflow run `36023376614` is explicitly invalid/unaccepted and excluded from the scientific record.

## M3 evidence

Candidate: `FV2-HIST-M3-DSSM-01`.

Null: `M3-NULL-MARKET-NORMAL-01`.

Phase-4 evidence label: `NEGATIVE_PRIMARY_EVIDENCE`.

- OOF/common N: `1087`.
- candidate primary log loss: `0.7811502028797036`.
- null primary log loss: `0.7804795705044401`.
- paired candidate-minus-null delta: `+0.0006706323752636532` (higher is worse).
- 10,000 week-block bootstrap 95% interval: `[-0.00031937461835433245, +0.0016556867645020252]`.
- primary delta unfavorable in all four outer seasons.
- dynamic-no-QB log loss: `0.7808845344047226`; adding QB worsens the full model by about `0.0002657`.
- ATS diagnostic only: `518-540-29`, ex-push hit rate `48.96%`.

M3 did not demonstrate tangible incremental information beyond its market null in Phase 4. This is not yet the formal Phase-5 survivor classification.

## M4 evidence

Candidate: `FV2-HIST-M4-DMARGIN-01`.

Null: `M4-NULL-STUDENTT-CONSTANT-01`.

Phase-4 evidence label: `POSITIVE_PRIMARY_EVIDENCE`.

- OOF/common N: `1087`.
- candidate integer-margin log score: `3.852975162486858`.
- null integer-margin log score: `3.935646861629811`.
- paired candidate-minus-null delta: `-0.08267169914295289` (lower is better).
- 10,000 week-block bootstrap 95% interval: `[-0.10748698706212485, -0.05796293485132338]`.
- primary delta favorable in all four outer seasons.
- conditional-scale-only contribution versus null: `+0.00012506107970626913`.
- key-mass-only contribution versus null: `-0.08271839184340689`.
- full minus constant-scale-key: `+0.00004669270045401389`.
- numerical/tail audit: `PASS`.
- ATS diagnostic only: `540-518-29`, ex-push hit rate `51.04%`.

M4 demonstrated strong distributional improvement versus its strong null, but the preregistered ablation attributes essentially all of the gain to key-mass representation rather than conditional scale. Formal survivor classification remains Phase 5.

## Scientific boundary at Phase-4 close

- Red-team audit: `PASS`.
- Exact common rows: `1087` for M3 and M4.
- No completed-2026 outcomes used.
- No target-game PBP, future state, eventual target QB identity, expanded hyperparameter grid, post-result feature/distribution change, threshold fishing, tail truncation, or endpoint folding entered accepted evidence.
- No M3+M4 combination, rescue candidate, or calibration rescue was created.
- ATS and `REFERENCE_MINUS110` remained diagnostics only.
- Production remains unchanged.

## Exact Phase-5 starting action — do not execute unless Phase 5 is explicitly begun

Read `FINAL_PHASE4_RECEIPT.md`, `PHASE4_RESULT_REGISTRY.json`, the canonical OOF/metrics/ablation/calibration/bootstrap/red-team evidence, and the frozen `EVALUATION_PROTOCOL.md`. Verify provenance and hashes, then classify M3 and M4 independently under the preregistered Phase-5 criteria. Do not refit, redesign, recompute candidates, introduce rescue candidates, construct an M3+M4 combination, begin prospective shadowing, or alter production before survivor classification is complete.

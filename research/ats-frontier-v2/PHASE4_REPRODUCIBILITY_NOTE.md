# PHASE 4 REPRODUCIBILITY NOTE

Program: `LEVLINE_ATS_FRONTIER_V2`

Phase: `4 — CONTROLLED HISTORICAL DEVELOPMENT, ABLATION & EMPIRICAL VALIDATION`

## Purpose

Two corrected, result-blind-authorized Phase-4 executions completed from the same accepted scientific code/config surface. Their outputs are scientifically consistent but not byte-identical. This note preserves that fact rather than silently treating the packages as exact duplicates.

## Corrected execution A

- workflow run: `36025306390`
- execution commit: `4fce9805c2ba9ed9dc6de388600fe40787605720`
- artifact: `10820230932` (`ats-frontier-v2-phase4-36025306390`)
- artifact digest: `sha256:c31c5c324db4e56f63488c883252ca2601f39aecf2989d645790aa21704f4fcf`
- M3 OOF SHA-256: `f15bb97c9947bffb123f70658b2b75ebd900a341b9aefe680fbe86beaaf30c40`
- M4 OOF SHA-256: `2653434b7264a73166429f6702f83a4da87f2d59eb023c3839d3222afff18190`

## Corrected execution B — final canonical package

- workflow run: `36025444929`
- execution commit: `7eda9cacd471a3161424699958509c02a260fc05`
- artifact: `10820397832` (`ats-frontier-v2-phase4-36025444929`)
- artifact digest: `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`
- M3 OOF SHA-256: `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`
- M4 OOF SHA-256: `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`

Execution B is the canonical package because it is the final evidence package preserved on the Phase-4 branch after all authorized corrected executions completed.

## Shared scientific identities

Both corrected executions used:

- validated scientific head lineage: `c1eead294c5ac897041fc35f628b2fec393ab064`;
- accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`;
- config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`;
- dataset identity SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`;
- game-ID SHA-256: `03156647fbed7dc936c953a2a6c3400b2423fc3c8ff245388261c9bddd3b2a4f`;
- bootstrap seed: `20260924`;
- 10,000 season-stratified NFL-week bootstrap resamples;
- 1,087 M3 OOF rows and 1,087 M4 OOF rows;
- zero completed-2026 outcomes;
- unchanged production forecasting surfaces.

## Observed numerical drift

The packages are not byte-for-byte identical. The observed scientific drift is numerically tiny and does not alter candidate selection, hyperparameter identities, per-season direction, uncertainty conclusion, ablation attribution, or Phase-4 evidence labels.

### M3

- execution A paired candidate-minus-null delta: `+0.0006706323752636537`
- execution B paired candidate-minus-null delta: `+0.0006706323752636532`
- absolute difference: approximately `5e-19`
- evidence direction: unfavorable in both executions
- evidence label: `NEGATIVE_PRIMARY_EVIDENCE` in both executions

### M4

- execution A paired candidate-minus-null delta: `-0.08267169179619614`
- execution B paired candidate-minus-null delta: `-0.08267169914295289`
- absolute difference: approximately `7.35e-9`
- execution A 95% week-block interval: `[-0.10748699203380639, -0.057962887776498655]`
- execution B 95% week-block interval: `[-0.10748698706212485, -0.05796293485132338]`
- evidence direction: favorable in both executions and in all four outer seasons
- ablation attribution: key-mass component reproduces essentially all primary-score improvement in both executions
- evidence label: `POSITIVE_PRIMARY_EVIDENCE` in both executions

## Interpretation and boundary

The exact low-level source of the byte-level numerical difference has not been isolated and is not asserted here. The observed difference is preserved as a reproducibility fact. It is not used to alter a candidate, tune a threshold, choose a favorable execution, or create a rescue model.

The final branch package from workflow run `36025444929` is the sole canonical Phase-4 evidence package for downstream repository closeout and Phase-5 synthesis. Execution `36025306390` remains preserved as an independent corrected execution demonstrating that the scientific conclusions are stable to the observed numerical drift.

The earlier pre-correction workflow run `36023376614` remains `INVALID / NOT ACCEPTED` and is not part of this corrected-run reproducibility comparison.

Phase 5 remains `NOT_STARTED`.

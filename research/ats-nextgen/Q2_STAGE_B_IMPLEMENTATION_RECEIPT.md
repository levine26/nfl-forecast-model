# ATS Next-Generation — Q2 Stage B Implementation Freeze

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** B — Q2 only  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Status at receipt:** **IMPLEMENTATION FROZEN; NO ACCEPTED Q2 HISTORICAL RESULT**  
**Branch:** `research/ats-nextgen-phase2-q2`  
**Stage-A merge / Stage-B base:** `a2581a62e3797a6ac466d614326bc72b7d5a1c57`  
**Canonical pre-result implementation head:** `5c67c0c55f6f8a23a9036866075209f083f04981`

## 1. Pre-result evidence boundary

This receipt is finalized before accepting any Q2 historical result. Earlier Stage-B heads are superseded for evidentiary purposes.

A temporary pre-result development state contained an unused alternative `q2_eval.py` / `q2_runtime.py` implementation path. It was identified as an unnecessary duplicate before any accepted Q2 historical evidence and removed without changing the scientific contract, candidate grids, fitting rules, scoring rules, or canonical runner. The canonical head above therefore has one Q2 execution path: `challenger_ats_nextgen_q2.py` + `challenger_ats_nextgen_q2_experiment.py` + `challenger_ats_nextgen_q2_reporting.py` + the fail-closed runner.

At this boundary:

- Q2 accepted historical performance: **NONE**;
- Q2 result interpretation: **NONE**;
- Q2 rescue/redesign after results: **NONE**;
- Q3 started: **NO**;
- completed-2026 outcomes used: **0**;
- production F-ST/Sunday Signal behavior changed: **NO**.

Only an exact-head run that includes this finalized receipt, passes the Q2 contract, and then completes the historical job may be accepted as Stage-B evidence.

## 2. Frozen upstream identities

The Stage-B runner must prove before its first Q2 fit:

- Phase-2 gate canonical SHA-256: `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- Stage-A Q1 outer OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- generalized Stage-B Q1 median helper reproduces frozen Stage-A Q1 median predictions by `game_id` for every outer season 2022–2025.

A failure of any one of those checks occurs before Q2 fitting and invalidates execution.

## 3. Frozen implementation blobs

The canonical scientific implementation at pre-result head `5c67c0c55f6f8a23a9036866075209f083f04981` is:

- Q2 distribution core `src/nfl_forecast/challenger_ats_nextgen_q2.py`: blob `d551c4d3dbaa808556e3183fd65d6d20e8e92212`;
- Q2 nested experiment driver `src/nfl_forecast/challenger_ats_nextgen_q2_experiment.py`: blob `9249b39ebc2c42e4013a13b763d010c75939bd74`;
- Q2 reporting contract `src/nfl_forecast/challenger_ats_nextgen_q2_reporting.py`: blob `f7bc779e402b2d05230008b1779665484e9f11a6`;
- fail-closed Q2 historical runner `scripts/run_challenger_ats_nextgen_q2.py`: blob `36612cdb6517b1a3f2c777720fc7aa0458ec99f7`;
- Q2 core tests `tests/test_challenger_ats_nextgen_q2.py`: blob `4a691a354b1e577fb64ae66767bee6eb2e985fc2`;
- Q2 experiment/reporting tests `tests/test_challenger_ats_nextgen_q2_experiment.py`: blob `943dba552d61165fb8f196582cd31af1585ab281`;
- Q2 Stage-B workflow `.github/workflows/research_ats_nextgen_q2.yml`: blob `d261d6d92a25aaedf477e99bdde939ed1727a04f`;
- authoritative opening receipt `research/ats-nextgen/Q2_STAGE_B_OPENING_RECEIPT.md`: blob `548c60fbaf44cb10fb47bfed3255ed30feb1cbae`;
- scoring/reporting receipt `research/ats-nextgen/Q2_STAGE_B_SCORING_RECEIPT.md`: blob `c41a181411d246fd87e0693c40bd6e93e3668807`;
- research-validation workflow containing the Q2 contract tests: blob `8da5f0c8d98d22d94a07c47c8199aad6e87481f3`.

The machine registry was subsequently extended only to bind this implementation identity; its scientific grids and opening contract are unchanged.

The runner blob above is the strengthened version that checks the gate hash, full Q1 OOF hash, and direct per-season Q1 median identity before the first Q2 fit.

## 4. Frozen experiment surface

The historical experiment is limited to the bounded Stage-B surface already specified in `Q2_STAGE_B_OPENING_RECEIPT.md` and `Q2_STAGE_B_SCORING_RECEIPT.md`:

- support `-75..+75` with integrated half-integer bins and endpoint tail folding;
- generalized normal, Gaussian, Student-t and empirical residual reference only;
- generalized-normal beta `{1,1.25,1.5,1.75,2}`;
- Student-t df `{4,6,10}`;
- mandatory generalized-normal ablations: no-key conditional-scale, key constant-scale, key conditional-scale;
- Gaussian and Student-t full key+conditional-scale references;
- empirical reference with total symmetric Dirichlet pseudocount `1.0`;
- key numbers `|k|={3,6,7,10,14}` only;
- key penalty `{1,10,100}` only;
- prior-only pooled row-level discrete CRPS for inner selection;
- Q2 target center from chronology-clean frozen Q1 median; M1 target center from the market only;
- Q2 inner target 2019 omitted mechanically; no fallback or random CV;
- outer targets exactly 2022–2025;
- endpoint-mass threshold `1e-3`, fail closed;
- no ATS hit rate or ROI used for model selection.

The primary incremental comparison remains `Q2_GN_FULL` versus paired `M1_GN_FULL` on exact common OOF rows. Reference/ablation arms may explain mechanism but may not redefine the primary candidate after results.

## 5. Execution rule

The dedicated workflow may execute Q2 historical development only through a historical job with `needs: contract`. The exact-head contract must pass first. The historical job must then:

1. regenerate and verify the frozen Phase-2 gate;
2. regenerate and verify the frozen Stage-A Q1 OOF;
3. reproduce the Stage-A Q1 median interface by season;
4. execute only the frozen Q2 arm/grid surface;
5. prove protected production surfaces were not modified;
6. upload the complete Q2 evidence artifact.

If the branch changes, a prior in-flight run is superseded and its result is not accepted.

## 6. Interpretation firewall

The runner may write an uninterpreted primary paired snapshot for integrity, but candidate classification occurs only after the immutable artifact is available. No poor result can motivate a new family, support range, key number, smoothing constant, scale predictor, penalty, calibration layer, threshold or selective slice inside Q2 V1.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.

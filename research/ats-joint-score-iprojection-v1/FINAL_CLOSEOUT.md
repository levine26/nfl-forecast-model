# ATS-JSIP-V1 — Final Scientific Closeout

**Candidate:** `ATS-JSIP-V1`  
**Final classification:** `FAILED`  
**Disposition:** `FAIL_CLOSED_BEFORE_TARGET_SCORING`  
**Production authorization:** NONE  
**Completed-2026 outcomes used:** 0  
**Production behavior changed:** NO

## 1. Executive conclusion

`ATS-JSIP-V1` is closed as a preregistered **structural/numerical failure before target-season challenger scoring**.

The experiment did not fail because its 2022–2025 ATS CPL performance was poor. No `ATS-JSIP-V1` target-season challenger probability, proper score, ATS result, calibration result, bootstrap result, hit rate, or ROI was generated. The mandatory frozen preflight stopped the experiment first.

The accepted primary null, `KMASS-MARKETML-IPROJ`, reproduced successfully on the exact 1,087 canonical 2022–2025 rows. The maximum absolute difference between regenerated and accepted null probabilities/losses was `4.440892098500626e-16`, establishing that baseline identity was not the failure source.

The frozen adaptive-support invariant was infeasible. Under the preregistered Student-t nuisance grid and the hard support ceiling of 160, **all 2,174 home/away team-score axes across the 1,087 canonical games fail every legal `(df, scale)` pair** to achieve omitted upper-tail mass `<1e-12`.

Therefore the experiment correctly failed closed before candidate target scoring, exactly as required by the frozen preregistration.

## 2. Controlling preregistration state

The controlling pre-result commits remain:

- `930320c94ffc1d554f72589328b48a98a3373662`
- `f67cd216b73ee1861e8019c2eb6553438c3aeb64`
- `50264684a74b34dbb1d9fa3b4c6c4455c6e111d3`

The scientific preflight implementation was frozen on canonical `main` before execution by PR #587, merge commit:

- `10c8597dcb94d43cfeaded353812759d53352d2f`

The execution receipt was then generated under GitHub Actions and preserved by PR #588, merge commit:

- `3652ae0851a5957539816ca8826ef55570134d7a`

This ordering preserves the intended chronology: preregistration -> implementation freeze -> execution -> evidence preservation -> closeout.

## 3. Primary-null reproduction

Canonical accepted OOF artifact SHA256:

`c50fa8b5aaa088cfe19ef809e0e92f1a3fef0d979073187f8ba69fd545a38f7b`

Reproduction evidence:

- exact common rows: `1087`;
- target seasons: `2022, 2023, 2024, 2025`;
- row identity SHA256: `781a3595270f77583ade5fa18e5625afb8b129dd233d667cff95a2492ee122ba`;
- regenerated probability payload SHA256: `4fa2fb0a146e25dcfd1863e64c7de11fedf00106756473a44a35a89598fec064`;
- maximum absolute probability/loss difference versus accepted `KMASS-MARKETML-IPROJ`: `4.440892098500626e-16`;
- primary-null reproduction status: `PASS`.

The historical scaffold also retained the accepted historical-game identity and contained zero completed-2026 rows.

## 4. Frozen support failure

Preregistered support rule:

- begin each team-score support at `0..80`;
- expand by 20 points;
- require omitted upper-tail mass `<1e-12` for each team marginal;
- never fold omitted tail mass into the endpoint;
- fail closed if any row requires support above `160`.

Frozen nuisance grid:

- `df in {4, 6, 10}`;
- `scale in {8, 10, 12, 14}`.

The pre-result implementation clarification defined the conservative structural Student-t omitted-tail estimate at support bound `B` as:

`P(X >= B + 0.5 | X >= -0.5)`.

For every canonical target row, preflight evaluated every legal `(df, scale)` pair. Even the best legal pair could not satisfy the tolerance at 160.

Observed best-case tail evidence across all 2,174 team axes:

| Quantity | Result |
| --- | ---: |
| Frozen tolerance | `1.0e-12` |
| Minimum best-case tail at 160 | `2.2375504136638633e-09` |
| Median best-case tail at 160 | `4.417177986724035e-09` |
| Maximum best-case tail at 160 | `9.222892378827844e-09` |
| Team axes failing every legal pair at 160 | `2174 / 2174` |
| Canonical games with failure | `1087 / 1087` |
| Minimum best-case required support bound | `340` |
| Median best-case required support bound | `360` |
| Maximum best-case required support bound | `360` |

The best-case nuisance pair in the diagnostic examples was the thinnest-tailed legal choice, `df=10, scale=8`, and still failed materially above the frozen `1e-12` requirement.

## 5. What was deliberately not run

Because the support invariant failed first, the following were correctly not executed for `ATS-JSIP-V1` target rows:

- joint PMF target forecasts;
- ML projection target forecasts;
- target outcome-mutation invariance testing on completed candidate forecasts;
- chronological nuisance selection for the target candidate;
- CPL candidate log loss;
- candidate multiclass Brier;
- integer-margin candidate log score;
- candidate CRPS/RPS diagnostics;
- candidate calibration diagnostics;
- candidate ATS W-L-P / hit rate;
- candidate reference `-110` sensitivity;
- per-season target deltas;
- 10,000-resample paired week bootstrap;
- advancement-gate evaluation.

These are `NOT_RUN_FAIL_CLOSED`, not missing favorable or unfavorable evidence.

## 6. Leakage and production firewall

The preserved receipt establishes:

- completed-2026 outcomes used: `0`;
- completed-2026 rows in historical scaffold: `0`;
- candidate target probabilities generated: `false`;
- candidate target proper scores generated: `false`;
- candidate target ATS results generated: `false`;
- production changed: `false`;
- canonical primary-null identity/hash: `PASS`;
- production firewall: `PASS`.

No LevLine/F-ST/Sunday Signal production forecasting behavior was altered by this experiment.

## 7. Execution evidence

Frozen preflight workflow:

- GitHub Actions run: `36098581877`;
- job: `107956015240`;
- workflow conclusion: `success` (meaning the fail-closed scientific logic executed and verified correctly);
- immutable artifact: `ats-jsip-v1-preflight-36098581877`;
- artifact ID: `10848990195`;
- artifact ZIP SHA256: `e212b30417a1c16de6185c29157e6e3231ee7f18594c6496ad369a1755e0e94e`;
- preserved repository receipt: `research/ats-joint-score-iprojection-v1/PREFLIGHT_RECEIPT.json`.

The scientific result inside that successful execution is `FAILED` / `FAIL_CLOSED_BEFORE_TARGET_SCORING`.

## 8. Interpretation

The underlying joint-score idea is not empirically rejected by this V1 run, because its historical predictive performance was never measured. Instead, the **specific preregistered numerical realization** was internally incompatible: heavy-tailed Student-t kernels, a stringent `1e-12` omitted-tail standard, and a hard 160-point support ceiling cannot simultaneously hold on the canonical market-implied score locations.

That distinction matters. It would be scientifically incorrect to call this `NO_MATERIAL_IMPROVEMENT`, because no target CPL comparison exists. It would also be scientifically incorrect to relax the tail tolerance or widen support after discovering the incompatibility and continue under the same candidate ID.

## 9. No post-result rescue under V1

`ATS-JSIP-V1` is permanently closed. Under this candidate ID, do not:

- raise the support ceiling above 160;
- relax the `1e-12` tail tolerance;
- fold/truncate omitted mass;
- replace the Student-t kernel;
- change the df or scale grids;
- alter the lattice multiplier;
- add a correlation parameter;
- alter the moneyline projection;
- inspect or optimize against target-season candidate results;
- use completed-2026 outcomes;
- modify production forecasting behavior.

Any such change is a new scientific hypothesis and requires a new candidate ID plus a new preregistration before scoring.

## 10. Next phase boundary

The `ATS-JSIP-V1` phase is complete and closed as `FAILED`.

The next permissible phase is **new-candidate design and preregistration**. A successor may retain the scientifically interesting joint-score premise, but it must resolve numerical support feasibility prospectively rather than retroactively repairing V1. In particular, any successor that changes support bounds, tail semantics, kernel family, or approximation strategy must freeze those choices before target scoring and must preserve the same leakage, canonical-null, chronology, and production-firewall disciplines.

No successor candidate is authorized by this closeout itself. Its design begins only after this closeout is canonical.

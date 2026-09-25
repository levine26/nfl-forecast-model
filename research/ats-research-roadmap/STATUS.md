# LevLine ATS Research — Canonical Status

**As of:** 2026-09-25  
**Research-only snapshot opened from:** `fef9ff9979dbffb3934e77b314884ab76437090e`  
**Production model:** `F-ST-01-FROZEN-2026` remains unchanged  
**Completed-2026 outcomes used in this synthesis:** `0`

## Executive status

The ATS program has accumulated enough negative and structural evidence that the next step is **not** to start another generic historical challenger. The evidence supports a narrower conclusion:

- the sportsbook spread should remain the primary **location anchor**;
- moneyline information can add a small but real **sign-mass** refinement to a spread-centered distribution;
- discrete NFL scoring/key-number mass is a legitimate distributional mechanism and is already under a separately frozen prospective program;
- generic football-state corrections, standalone LevLine fair-line edge, direct cover classification, quantile market residuals, static cross-market tilts, conditional scale, and simple line-movement rules have not established stable incremental information beyond strong market baselines;
- rich timestamped market microstructure remains scientifically interesting, but its correct experiment already exists as `FV2-PROS-M1-MARKETSTATE-01` and must not be duplicated under a new name;
- a coherent multi-season historical implementation of that M1 mechanism remains blocked by market-data provenance/cadence, not by engineering preference.

Accordingly, the canonical state is **prospective execution + disciplined representation research**, not another broad historical search.

## Active / preserved programs

| Program | State | What is legitimately open | What is not allowed |
|---|---|---|---|
| `FV2-PROS-M1-MARKETSTATE-01` | `PROSPECTIVE_ONLY`; historical lane `BLOCKED_PENDING_PAID_SOURCE` | Continue governed T-120 multi-book capture; evaluate frozen T-60 future-market intermediate target and later final CPL outcome under its preregistration | Do not relabel coarse/open-close historical data as fixed-horizon market microstructure; do not create a duplicate “market next-state” candidate |
| `FV3-PROS-KMASS-01` | Phase 1 complete; Phase 2 not started in its closeout receipt | Execute the frozen 2010–2025 parameter-estimation procedure once, hash parameters, then create immutable prospective T-120 candidate/null shadow forecasts | No confirmatory outcome scoring before its formal evidence conditions; no positive early stop; no production promotion from Phase 1 |
| `FV2-PROS-M2-QBDELTA-01` | prospective evidence/capture preserved; field completeness not fully certified | Continue only point-in-time information-delta research where state was genuinely available before the decision horizon | Do not backfill missing QB/player states with later knowledge; do not revive generic QB/team-strength features as a historical rescue |

## Closed / negative empirical lanes

### Standalone LevLine fair-line ATS policy

The canonical fair-line policy audit did not establish ATS value. Across 1,087 expanding-season OOF decisions from 2022–2025 it recorded 517 wins, 541 losses, 29 pushes; non-push hit rate was 48.8658%, and the LevLine margin estimate had worse MAE than the market center. Model edge versus ATS residual was near zero. The correct inference is that winner-prediction success does not automatically transfer to spread-cover prediction.

**Status:** do not rescue with threshold fishing, post-hoc edge cutoffs, or confidence slicing.

### F-ST cross-market transfer

Cross-market transfer candidates did not materially improve the ATS distribution and were worse than the strongest matched market-only null. The retained positive finding was market-moneyline coherence: adding moneyline-informed sign mass improved CPL log loss relative to the spread-only key-mass null.

**Status:** close F-ST transfer as an ATS information source; retain the moneyline sign-mass finding.

### Static market-manifold / within-sign tilts

Static cross-market shape tilts failed to improve the accepted market-centered distribution. A smooth residual within-sign tilt worsened the primary score, and the prior-only selector ultimately returned to no tilt in later seasons.

**Status:** spread remains location anchor; do not reopen generic static shape tilt, center replacement, or conditional-scale searches from this evidence.

### NextGen Q1: quantile market residual

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` was structurally valid but rejected. Its primary mean-three-quantile pinball score was slightly worse than the null, and the football block often shrank toward no adjustment.

**Status:** a model called “market residual” is not novel merely because the loss function or learner changes.

### NextGen Q3: direct cover/push/loss hurdle

`ATS-Q3-DIRECT-CPL-HURDLE-V1` was valid and rejected. CPL log loss and Brier score worsened, calibration deteriorated, and performance was worse in most seasons/slices.

**Status:** direct classification cannot be treated as an unexplored shortcut around the market benchmark.

### Frontier V2 M3: dynamic hierarchical football state

`FV2-HIST-M3-DSSM-01` was rejected. Primary log loss was worse than the market null, every outer season was unfavorable, and the no-QB ablation outperformed the full candidate.

**Status:** do not revive generic dynamic team/QB state without a genuinely different point-in-time information mechanism.

### Frontier V2 M4: conditional discrete margin model

The full M4 model improved the market null, but the gain was fully explained by the simpler preregistered constant-scale key-mass ablation; conditional scale did not add value and the full candidate was slightly worse than key-mass only.

**Status:** M4 itself is rejected; the isolated key-mass hypothesis moved into the separately governed V3 prospective program and must remain separate.

### Adaptive market-path Candidate 3

The 2025 coarse same-book market-path experiment produced only three winner switches and a +1 winner point estimate while worsening Brier and log loss. A later-market-level-only control reproduced the same net winner gain, so the experiment failed to establish independent path information beyond market level.

**Status:** a simple line-movement rule is not enough; the richer M1 prospective design is the existing legitimate successor.

## Structurally invalid / not empirically answered

### JSIP V1 joint-score architecture

`ATS-JSIP-V1` failed closed before target scoring because its finite support/tail contract was numerically infeasible for the frozen Student-t nuisance grid. No candidate probabilities, proper scores, ATS records, or ROI were produced.

This is important: the **specific V1 implementation is invalid**, but the joint-score/discrete-score representation mechanism was not empirically rejected.

**Status:** a future successor is scientifically permissible only as a new identity with a tail-safe/unbounded numerical contract, preregistration, strongest market-centered null, explicit key-mass ablation, and no use of completed-2026 outcomes in design or tuning. It is a representation study, not the primary current information-edge hypothesis.

## Historical M1 blocker

The free-source audit established that no coherent 2020–2025 public panel currently qualifies for the frozen M1 fixed-horizon contract. The problem is not simply “missing some rows.” The available sources have materially different temporal semantics:

- older provider caches are genuine but mostly sparse/fixed-time gameday snapshots and include a documented historical timing defect in an older configuration;
- the 2025 public market-movement corpus is genuinely timestamped and multi-book, but four captures per day are too coarse to guarantee fresh T-120/T-60/T-30 states and can cause multiple horizons to inherit the same stale quote;
- opener/closer archives are horizon-opaque and cannot be relabeled as fixed-horizon observations;
- older Wayback-era material is heterogeneous and should not be stitched into a modern panel merely to increase sample size.

Therefore historical M1 remains `BLOCKED_PENDING_PAID_SOURCE` unless a new, outcome-blind data-qualification amendment is completed before target performance is viewed. No purchase is authorized by this roadmap.

## Retained scientific knowledge

1. **Market level is the benchmark, not a nuisance covariate.** Any ATS candidate must beat a same-horizon, same-information market null.
2. **Moneyline and spread are not perfectly redundant.** The repo’s strongest accepted static increment is moneyline-informed sign-mass calibration on top of a spread-centered discrete distribution.
3. **Discrete key mass is structural, not a betting rule.** Its value is probability representation/calibration around NFL scoring masses; its prospective validity is being tested separately in V3.
4. **Information timing matters more than model complexity.** The most credible open mechanism is genuinely point-in-time information not already contained in the contemporaneous spread/price/ML/total state.
5. **Proper probability scores control advancement.** ATS hit rate and ROI are downstream diagnostics and cannot rescue a model that loses on its preregistered proper score.
6. **Negative results narrow the search space.** Renaming rejected mechanisms or changing the learner without changing the information set is not a new hypothesis.

## Canonical decision on “what next?”

There is **no new historical ATS challenger authorized by this status document merely for the sake of continuing experimentation**. The priority is to execute the already-governed prospective programs correctly and to open a new historical identity only when a candidate passes the novelty/data gate in `ROADMAP.md`.

The only presently credible new historical representation lane is a separately preregistered, numerically corrected successor to the invalid JSIP V1 architecture. Even that lane is secondary: it can improve how probabilities are represented, but it does not introduce a new information source and therefore must demonstrate proper-score value against the strongest market-only distributional null before any ATS interpretation.

## Production firewall

This status document changes no production code, forecast, fair spread, score projection, ATS pick, history record, UI, deployment, or public grading. It grants no production authorization to M1, M2, V3 key mass, a future JSIP successor, or any other ATS research candidate.
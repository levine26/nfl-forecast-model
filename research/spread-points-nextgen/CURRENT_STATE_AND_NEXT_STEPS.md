# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-22 America/Los_Angeles  
**Program authority:** `research/spread-points-nextgen/MASTER_PLAN.md`  
**Phase 0:** **COMPLETE**  
**Phase 1:** **COMPLETE**  
**Phase 2:** **NOT STARTED**  
**Active phase:** None. Phase 1 is merged and complete; the next substantive chat starts Phase 2 under the mandatory startup protocol.

## Phase 1 completion state

Phase 1 audited the current LevLine score/spread system without changing production behavior.

Canonical Phase 1 directory:

`research/spread-points-nextgen/phase1/`

Primary Phase 1 branch / PR:

- branch: `research/spread-points-nextgen-phase1`
- PR: **#513 — MERGED**
- merge commit: `a4f7172c0c4ff82b1689411181e7a9042a1628a8`

Final post-sync validation:

- candidate head: `b6b831fd1a77180e8dc97a0eb17495bbdee44ba5`
- research firewall `35741337735`: **SUCCESS**
- research validation `35741337942`: **SUCCESS**
- dedicated Phase 1 audit `35741337832`: **SUCCESS**
- audit artifact `10699778876`
- artifact digest: `sha256:c85bc49458631c6f9b9a14e0a21f1eb213b527017e20ddcc125e9e23b484e0e1`

## Reproduced baseline

Primary universe: **1,087 regular-season games, 2022–2025**.

Independent football score model:

- home points MAE: **7.424**
- away points MAE: **7.485**
- margin MAE: **9.962**
- total MAE: **10.854**

Historical schedule market benchmark:

- spread/margin MAE: **9.494**
- total MAE: **10.189**

Paired season+week bootstrap supports a market advantage on both continuous targets.

Chronology-clean historical F-ST analogue:

- winner accuracy: **68.17%**
- Brier: **0.21065**
- log loss: **0.60871**

Raw market:

- winner accuracy: **67.62%**
- Brier: **0.21020**
- log loss: **0.60765**

Independent-margin ATS diagnostic accuracy is **48.77%** after pushes are excluded.

## Main empirical findings

1. **Score/margin prediction is compressed.** Large realized margins and double-digit favorite environments are under-differentiated.
2. **Totals regress strongly toward the middle.** Model total prediction SD is only 1.83 points versus 4.25 for the market total.
3. **Large LevLine-market disagreement is not a validated edge.** In the >=6-point disagreement slice the model's continuous margin error is materially worse than the market.
4. **The current inverse-MAE four-regressor blend does not beat the best individual ElasticNet OOF MAE** for either margin or total.
5. **The market is the stronger continuous baseline** in every 2022–2025 target season for margin and total.
6. **Recent-form and simple pace slices do not show a strong monotonic residual pattern.** They remain candidate ingredients only if Phase 2 research provides a better structural formulation.
7. **Core OOF data completeness is not the observed problem.** All 44 Core fields are populated on the audited universe before model imputation.
8. **Observed historical weather metadata cannot be treated as a PIT-safe forecast source.** Weather experiments still require archived or prospectively captured forecasts.
9. **2025 availability evidence is suggestive, not decisive.** QB/OL practice-limitation slices have higher margin MAE but one-season uncertainty intervals cross zero.
10. **Current architecture is intentionally split:** independent margin/total regressions, frozen market-conditioned F-ST winner probability, and a public probability-to-margin bridge are different forecast objects.

## Important governance findings

- Base score-regressor OOF predictions are season-held-out, but final inverse-MAE weights reuse the combined evaluation block.
- The ordinary Core classifier meta-model is fit and scored on the same combined base-OOF matrix; its displayed stack OOF metric is not fully nested.
- Frozen F-ST normal scoring remains capped at 2025.
- Current ordinary live Core/margin/total fits may incorporate already-completed 2026 games for later 2026 forecasts; completed 2026 outcomes remain forbidden for research architecture/feature selection.
- Historical nflverse market fields are an opaque closing/late benchmark, not a verified T-120 source.
- Historical starter/injury/weather state must fail closed unless its as-of time is proven.
- Research source qualification does not equal feature or production authorization.

## Data/source state carried into Phase 2

Strong/free foundations include nflverse schedule/PBP, sequential Elo, the qualified 2025 availability composite, 2025+ timestamped depth charts, 2026 prospective injury snapshots, lagged NGS/PFR/FTN research sources, and existing market/weather collection infrastructure.

Operational issues observed during Phase 1:

- prospective multi-book The Odds API collector: latest inspected state reported HTTP 401 and no usable current ledger rows;
- prospective weather capture: blocked on unresolved qualified game-specific venue receipts.

Neither issue changes production, but both constrain same-horizon Phase 2 experiments until resolved.

## David Sasser inclusion

Per user instruction, **davidsasser.com is explicitly part of the external research set**.

Phase 1 used it only as a comparator: its public CFB board separates projected team scores, projected line, opening/current market line, and ATS selection/tracking. The public material inspected does not expose enough reproducible model/data/chronology detail to use its reported record as scientific validation.

**Phase 2 must include a deeper davidsasser.com review** alongside peer-reviewed literature, technical public models, and reproducible open-source systems.

## Canonical Phase 1 artifacts

- `phase1/EVALUATION_CONTRACT.md`
- `phase1/CURRENT_ARCHITECTURE_AUDIT.md`
- `phase1/BASELINE_REPRODUCTION_REPORT.md`
- `phase1/ERROR_DECOMPOSITION_REPORT.md`
- `phase1/DATA_API_INVENTORY.md`
- `phase1/LEAKAGE_PIT_AUDIT.md`
- `phase1/PHASE1_SYNTHESIS.md`
- `phase1/PHASE1_SUMMARY.json`
- `phase1/run_baseline_audit.py`
- `phase1/run_structural_slices.py`
- `phase1/test_run_baseline_audit.py`

## EXACT NEXT ACTION — PHASE 2 CHAT

Do **not** restart Phase 1 and do **not** implement challengers yet.

The next substantive chat must:

1. Resolve current repository `main`.
2. Read the five canonical control files in the required order.
3. Read Phase 1 `PHASE1_SYNTHESIS.md`, `ERROR_DECOMPOSITION_REPORT.md`, `DATA_API_INVENTORY.md`, and `LEAKAGE_PIT_AUDIT.md`.
4. Inspect open PRs/branches and verify Phase 1 is merged/complete.
5. Mark Phase 2 `IN PROGRESS` only when substantive Phase 2 work begins.
6. Perform the Phase 2 **deep external research and challenger-design program**, including:
   - peer-reviewed sports forecasting and statistical score modeling;
   - NFL analytics and market-efficiency research;
   - drive/possession, opponent-adjusted, dynamic/Bayesian/state-space, player/QB/availability, red-zone/explosive-play, uncertainty and ensemble methods;
   - respected public/open-source forecasting systems;
   - **davidsasser.com**, with clear separation between reproducible evidence and opaque claims.
7. Convert Phase 1 residual findings into a deliberately limited challenger shortlist.
8. Freeze a chronology-clean development/validation/untouched-holdout protocol **before challenger results exist**.
9. Specify PIT contracts and data gaps for every proposed feature family.
10. Do not implement Phase 3 challengers in the Phase 2 chat.
11. Update all control/handoff files before Phase 2 stops.

## DO NOT REPEAT

- Do not rerun Phase 1 merely because a new chat did not personally generate it.
- Do not conflate `expected_margin` with the public probability-implied fair spread.
- Do not treat the historical closing/late market as T-120.
- Do not use final historical starter/injury/weather state without PIT proof.
- Do not use completed 2026 outcomes for feature, architecture, threshold or challenger selection.
- Do not resurrect the retired Props orchestration.
- Do not weaken the research firewall.
- Do not make a paid source dependency without the required user escalation.

## Stop condition

**Phase 1 is complete and merged. Phase 2 remains NOT STARTED. The next substantive chat begins Phase 2 from current `main`.**
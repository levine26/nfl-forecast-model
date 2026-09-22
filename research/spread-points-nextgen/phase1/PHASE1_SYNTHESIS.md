# Phase 1 Synthesis — Current LevLine Audit, Baseline Reproduction & Error Decomposition

**Phase status in this document:** **COMPLETE** — exact-head CI/firewall verification passed  
**Production change:** none  
**Primary branch:** `research/spread-points-nextgen-phase1`  
**Merged PR:** #513 (`a4f7172c0c4ff82b1689411181e7a9042a1628a8`)

## What Phase 1 established

Phase 1 has resolved the major baseline uncertainties needed before challenger design.

### Current model architecture

LevLine currently has separate numerical surfaces:

1. football-only independent margin regression;
2. football-only independent total regression;
3. independent team-score projection;
4. frozen market-conditioned F-ST winner probability;
5. public probability-implied fair margin;
6. public score pair combining probability-implied margin with independent total.

The production/public score should therefore not be described as if one model directly predicts every object.

### Reproduced score accuracy

2022–2025 regular season, 1,087 games:

- home points MAE: **7.424**;
- away points MAE: **7.485**;
- independent margin MAE: **9.962**;
- independent total MAE: **10.854**.

Historical market benchmark:

- spread/margin MAE: **9.494**;
- total MAE: **10.189**.

Paired block-bootstrap evidence supports the market advantage on both continuous targets.

### Winner probability

Chronology-clean historical F-ST analogue:

- winner accuracy: **68.17%**;
- Brier: 0.21065;
- log loss: 0.60871.

Raw market:

- winner accuracy: 67.62%;
- Brier: **0.21020**;
- log loss: **0.60765**.

F-ST therefore shows slightly better threshold winner classification in this sample while the raw market remains slightly better on proper probability scores.

### Main score-model failure pattern

The independent score model is **compressed**.

Evidence includes:

- model total prediction SD only 1.83 points versus market-total SD 4.25;
- low-total games are forecast too high;
- high-total games are forecast too low;
- double-digit favorites are forecast too conservatively;
- realized blowouts generate very large margin error;
- >=6 point model-market margin disagreements historically worsen continuous error versus the market.

The current model is best characterized as a stable team-strength baseline that does not sufficiently differentiate extreme game states.

## Validation/governance findings

### Strengths

- team performance is lagged before rolling;
- Elo is sequential/pregame;
- current-game PBP is not used in that game's pregame feature row;
- official F-ST artifact is frozen through 2025;
- dedicated research firewall protects production surfaces;
- 2026 completed outcomes remain prohibited for challenger selection.

### Limitations that Phase 2 must fix in research design

- regression ensemble weights are estimated on the same 2022–2025 OOF block they summarize;
- ordinary classifier meta-stack is fit and scored on the same combined base-OOF rows;
- historical schedule market rows are not a verified T-minus horizon;
- final historical schedule QB identity is not automatically a T-120-safe starter source;
- current live ordinary margin/total/Core fits can incorporate already-completed 2026 games even though F-ST coefficients remain frozen;
- tie semantics are inconsistent with a true three-outcome interpretation.

These are now documented rather than hidden.

## Data/source findings

### Strong existing foundations

- nflverse schedule/PBP;
- sequential Elo;
- 2025 qualified availability composite;
- 2025+ timestamped depth charts;
- 2026 prospective injury snapshots;
- lagged NGS/PFR/FTN research sources;
- market and weather research collectors with explicit as-of contracts.

### Current operational blockers

- latest inspected The Odds API prospective market collector status: HTTP 401 Unauthorized, no current captured multi-book snapshot rows;
- weather capture remains blocked for unresolved game-specific venue receipts in the inspected off-main ledger.

These do not affect current production, but they must be addressed before those source families can support strong Phase 2 experiments.

## David Sasser research inclusion

davidsasser.com was added to the Phase 1 external inventory as requested.

Its current college-football product visibly separates:

- projected team scores;
- projected line;
- opening/current market line;
- ATS pick and tracking.

That is a useful product/model-architecture comparator for LevLine. The inspected public site does not expose enough data provenance, model specification, or point-in-time methodology to treat its reported record as reproducible evidence. Phase 2 should inspect any public source code/methodology that becomes verifiable and extract transferable ideas without copying unvalidated claims.

## Existing research reused instead of repeated

Phase 1 reused prior repository evidence where the target/universe matched:

- margin disagreement forensics;
- F-ST chronology and market-incremental audits;
- v0.8 opponent/QB-aware research;
- source-governance and availability qualification;
- prospective market/weather infrastructure.

Notably, prior QB-aware winner research was mixed: QB features alone did not robustly improve PURE winner accuracy, while some combined opponent-adjusted/QB-aware blends were mildly promising. That evidence does not settle the score-forecasting question.

## Phase 2 challenger-design hypotheses

Phase 1 does **not** authorize implementation yet. The research questions carried forward are:

1. Can a football model predict **residual margin around the market** better than a direct raw-margin target?
2. Can a decomposed scoring model reduce total regression-to-the-middle?
3. Can opponent-adjusted team strength improve score accuracy?
4. Can pregame pace/possession, red-zone, explosive-play and special-teams expectations explain total/margin residuals?
5. Can PIT-safe QB starter quality/continuity/replacement deltas improve score forecasts?
6. Can PIT-safe OL/personnel/availability state add incremental value?
7. Can roof/weather/travel context add value once source timing is qualified?
8. Is a simpler linear score model more robust than the current equal-ish four-model blend?
9. Can a coherent joint score distribution generate winner, margin, total, cover and O/U probabilities without contradictory surfaces?
10. Can any football-only or hybrid challenger add information beyond the market under a strict untouched holdout?

## Required Phase 2 evaluation design

Before seeing challenger results:

- establish a chronology-clean development/validation/untouched-holdout contract;
- nest feature selection, stacking and blend weights inside prior-time folds;
- preserve the completed-2026 selection firewall;
- compare all candidates on the same games and same market horizons;
- require paired uncertainty;
- require subgroup robustness;
- separate score accuracy from betting/ATS performance;
- do not promote from one season, one metric, or one high-edge subgroup.

## Phase 1 exit-criteria mapping

| Exit criterion | Evidence |
|---|---|
| Architecture documented | `CURRENT_ARCHITECTURE_AUDIT.md` |
| Reproducible baseline | `run_baseline_audit.py`, workflow artifact, `BASELINE_REPRODUCTION_REPORT.md` |
| Market baselines | baseline report + margin forensics |
| Residual decomposition | `ERROR_DECOMPOSITION_REPORT.md` |
| Full data/API inventory | `DATA_API_INVENTORY.md` |
| Leakage/PIT risks | `LEAKAGE_PIT_AUDIT.md` |
| Concrete hypotheses | error report + this synthesis |
| No major baseline uncertainty | definitions frozen in `EVALUATION_CONTRACT.md`; remaining unknowns are explicitly source/PIT research questions, not ambiguity about the current baseline |

Final post-sync exact-head validation passed on `b6b831fd1a77180e8dc97a0eb17495bbdee44ba5`:

- research firewall run `35741337735`: **SUCCESS**;
- research validation run `35741337942`: **SUCCESS**;
- dedicated Phase 1 audit run `35741337832`: **SUCCESS**;
- final audit artifact `10699778876`, digest `sha256:c85bc49458631c6f9b9a14e0a21f1eb213b527017e20ddcc125e9e23b484e0e1`.

PR #513 merged as `a4f7172c0c4ff82b1689411181e7a9042a1628a8`. The exact-head checks finished successfully after the merge and the merged Phase 1 package was re-verified from `main`.

The structural diagnostics additionally found no strong monotonic recent-form or simple pace residual gradient, zero Core-feature missingness across the audited OOF sample, and only descriptive/non-PIT-safe weather associations. Phase 1 is therefore **COMPLETE**. Phase 2 remains **NOT STARTED** until the next substantive chat follows the canonical startup protocol.

## Closeout compatibility sync

Before merge, the Phase 1 branch was synchronized with `main` at `df91b80403a7af3094a9a6a8915afd0a6dce2ad3`. The sync brought forward concurrent repository state outside the Phase 1 research package; Phase 1 did not modify production forecast logic. Fresh pull-request checks then passed on `b6b831fd1a77180e8dc97a0eb17495bbdee44ba5`, and PR #513 merged at `a4f7172c0c4ff82b1689411181e7a9042a1628a8`.
# LevLine Spread & Points Next-Generation Research Program — Master Plan

**Status:** authoritative program charter  
**Canonical directory:** `research/spread-points-nextgen/`  
**Initialized:** 2026-09-21 (America/Los_Angeles)  
**Repository:** `levine26/nfl-forecast-model`  
**Production product:** Sunday Signal powered by LevLine  
**Phase-0 base main:** `536d6ab712028e374b42815db106f9fcb5d28053`

This file is the authoritative project charter for the next-generation LevLine research program covering **spread setting, scoring-margin prediction, team-point prediction, game totals, and joint score distributions**. GitHub, not conversation memory, is the institutional memory for this program.

If a later chat conflicts with this file or the live phase-control files, the repository controls unless the user explicitly overrides it.

---

## 1. Program objective

LevLine has historically been stronger at identifying game winners than at precise score, margin, and total prediction. This program will determine whether a scientifically defensible successor can improve prediction of:

- home points;
- away points;
- final scoring margin;
- fair spread;
- game total;
- scoring distributions;
- uncertainty;
- and incremental information beyond sportsbook markets.

The objective is **not** to manufacture an attractive ATS backtest. The objective is to build the most accurate, reproducible, leakage-safe football scoring and margin system possible.

Historical reference figures previously discussed — including winner accuracy around 68%, margin MAE around 9.6 points, and total error around 10.2 points — are **reference points only** until reproduced from repository evidence during Phase 1.

---

## 2. Absolute production firewall

The current official production winner-probability path is verified in repository state as:

`F-ST-01-FROZEN-2026`

Relevant authoritative production evidence includes:

- `src/nfl_forecast/fst_production.py`
- `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json`
- `research/fst/F-ST-01-FROZEN-2026.json`
- `docs/FST_FREEZE_PROVENANCE.md`
- `tests/test_fst_frozen_identity.py`
- `tests/test_fst_production.py`

The production artifact is explicitly `production_frozen`, the active production strategy is pinned to `F-ST-01-FROZEN-2026`, and its training cutoff remains 2025.

During this research program:

### Permitted

- inspect production code, frozen coefficients, historical forecasts, validation, market comparisons, APIs, and research infrastructure;
- build research-only challengers;
- run historical validation;
- establish prospective shadow evaluation;
- create research artifacts and compact evidence receipts;
- open and merge research/documentation PRs that do not alter production behavior.

### Prohibited

- replace the official winner;
- change the frozen F-ST coefficients or frozen identity;
- alter official historical forecast records or grading;
- rewrite production forecasts to improve research optics;
- silently route challenger outputs into production;
- silently reinterpret a diagnostic score/margin model as the official production line;
- deploy a successor as official LevLine without explicit final human approval.

**Final promotion requires the user’s personal green light after all required research and validation are complete. No automated or implied promotion is permitted.**

Existing research-firewall mechanisms, including `.github/workflows/research_validation.yml`, must be preserved or strengthened. They must never be weakened merely to make CI pass.

---

## 3. Current score/spread architecture boundary

Phase 0 inspected enough of the current implementation to establish the boundary without beginning the Phase 1 audit.

Current production/repository behavior includes:

- `src/nfl_forecast/pipeline.py` fits independent weighted regressions for historical `margin` and `game_total`;
- those models generate `expected_margin`, `expected_total`, residual sigmas, cover/over diagnostics, and score projections;
- `projected_score()` derives home/away points from margin and total;
- official winner probability is scored separately through the frozen F-ST path;
- `src/nfl_forecast/public_forecast.py` maps the official F-ST probability plus `margin_sigma` to a **probability-implied public fair margin/spread**, while the independently fitted margin remains diagnostic;
- current public semantics therefore intentionally distinguish the official probability-derived presentation line from the independent margin model.

Phase 1 must reproduce, document, and evaluate this architecture in full. Phase 0 does not authorize any redesign or tuning.

---

## 4. Scientific principles

### 4.1 Predict football before betting outcomes

Primary model evaluation must emphasize:

- margin MAE and RMSE;
- home-score MAE and RMSE;
- away-score MAE and RMSE;
- total MAE and RMSE;
- probabilistic calibration;
- prediction-interval coverage;
- residual bias;
- distributional accuracy.

Secondary/market-facing evaluation includes:

- ATS accuracy;
- cover-probability calibration;
- ATS by edge bucket;
- ATS by uncertainty;
- Brier score;
- log loss;
- market-relative performance;
- CLV only where legitimate point-in-time market data exists.

**ATS hit rate alone must never select the model.**

### 4.2 Separate football prediction from market incremental value

At least one challenger family must forecast football without simply reproducing sportsbook prices.

At least one market-aware family should test the sportsbook as a strong prior, including structures such as:

`Market expectation + LevLine predicted residual`

The program must answer two different questions:

1. How well can LevLine predict football?
2. Can LevLine add predictive information beyond the market?

Market dependence must be explicit.

### 4.3 Joint scoring is a hypothesis to test

The program must empirically test architectures based on:

`Home scoring distribution + Away scoring distribution -> margin + total + fair spread + win probability + uncertainty`

against simpler alternatives. Joint scoring is not presumed superior merely because it is elegant.

### 4.4 Player modeling is allowed only as a team-scoring hypothesis

The prior Props product is retired and must not be resurrected wholesale.

Authoritative retired-Props references:

- `docs/props/PROPS_RESEARCH_ARCHIVE_2026-09.md`
- `docs/props/README.md`
- `docs/props/RESET_MANIFEST.md`
- archive branch `archive/props-pre-revamp-2026-09-21`

Reusable concepts may include player availability, QB starter state, replacement value, offensive-line state, expected workload, personnel concentration, matchup effects, uncertainty, point-in-time data, market benchmarking, simulation, and immutable receipts.

The program may test a hierarchy such as:

game environment  
-> possessions  
-> offensive plays  
-> pass/rush behavior  
-> dropbacks / carries / routes / targets  
-> efficiency  
-> sacks / pressures / turnovers  
-> explosive plays  
-> red-zone opportunities  
-> touchdowns / field goals / empty possessions  
-> team points  
-> joint score distribution  
-> margin / total

That architecture is a hypothesis, not a requirement.

### 4.5 Emphasize modern NFL data

The primary modern research environment should emphasize approximately **2023-2026**, subject to empirical justification.

Older seasons may support:

- stable structural relationships;
- stronger priors;
- rare-event estimation;
- larger training samples.

Concept drift must be tested. Older environments must not dominate current football without evidence.

### 4.6 Strict chronology and anti-leakage

No fake backtests.

No post-hoc tuning presented as prospective evidence.

No future depth charts, later injury designations, completed-game player usage, closing market data, or post-kickoff information may masquerade as earlier pregame information.

Training, development, validation, final holdout, and prospective evidence must remain distinct.

### 4.7 Free/open data strongly preferred

First maximize current APIs, datasets, feeds, and open-source infrastructure already available to LevLine.

The repository already contains a data-source governance matrix at `research/LEVLINE_DATA_SOURCE_MATRIX.md`, including current/free sources such as nflverse-derived football data and prospective sportsbook research infrastructure.

Strongly prefer:

- free data;
- open-source data;
- already configured APIs;
- nflverse/nflfastR-style ecosystems where useful;
- reliable public information;
- reproducible datasets.

If a paid source appears likely to provide **meaningful incremental predictive accuracy that cannot reasonably be replicated for free**, document and escalate it before dependency creation. The recommendation must state:

- unique information available;
- why current/free sources are insufficient;
- model component affected;
- plausible accuracy value;
- how the benefit can be tested;
- cost if known.

No paid subscription or production dependency is authorized automatically.

### 4.8 Complexity must earn its place

No architecture is entitled to survive because it is sophisticated. Every added layer must demonstrate reproducible out-of-sample value, robustness, or necessary operational capability.

Negative findings are first-class research outputs.

---

## 5. Canonical program-control files

Every substantive chat must use and maintain:

1. `MASTER_PLAN.md` — this authoritative charter.
2. `PHASE_STATUS.md` — live program-control registry.
3. `CURRENT_STATE_AND_NEXT_STEPS.md` — concise handoff and exact next actions.
4. `DECISION_LOG.md` — durable decisions and rationale.
5. `RESEARCH_INDEX.md` — index of relevant code, evidence, data, and future reports.

---

## 6. Phase and branch discipline

Only **one program phase should normally be IN PROGRESS**.

Parallel work is allowed **within** the active phase when scientifically useful. Do not casually run multiple program phases simultaneously.

Recommended branch pattern:

- canonical program documentation on `main`;
- one primary research branch per active phase or coherent implementation block;
- only a small number of specialist branches when parallelization clearly helps;
- merge or close completed branches promptly where tools permit;
- do not recreate the branch explosion seen during Props development.

The live primary branch for each phase must be recorded in `PHASE_STATUS.md`.

---

## 7. Artifact discipline

Do not turn GitHub into a raw-data warehouse.

Prefer:

- normalized evidence;
- compact formats;
- sharding where appropriate;
- source references and hashes;
- reproducible transformations;
- immutable pregame receipts where prospective evidence is required.

Avoid needless duplication. Preserve scientifically important evidence and negative results.

---

# 8. Exact program phases

The phase sequence below is fixed. Do not collapse, reorder, skip, or materially redefine it without:

1. clear empirical necessity documented in `DECISION_LOG.md`; and
2. explicit user approval when the change materially alters the program.

---

## PHASE 0 — MASTER PROGRAM INITIALIZATION

**Purpose:** Establish governance and permanent institutional memory.

**Entry criteria**

- Existing LevLine repository is accessible.
- Current `main`, production winner, key score/spread surfaces, prior research, Props archive, and research firewall can be inspected.

**Required work**

- inspect current repository state;
- verify current `main`;
- verify production winner;
- locate current spread/score implementation;
- locate prior research;
- locate Props archive;
- identify current GitHub governance/firewall mechanisms;
- create this canonical research directory;
- create all permanent planning/handoff documents;
- seed the phase registry;
- establish branch conventions;
- establish artifact rules;
- establish final-approval gate.

**Do not**

- redesign the score model;
- tune coefficients;
- build full challengers;
- run broad feature searches;
- begin massive literature implementation.

**Required outputs**

- `MASTER_PLAN.md`
- `PHASE_STATUS.md`
- `CURRENT_STATE_AND_NEXT_STEPS.md`
- `DECISION_LOG.md`
- `RESEARCH_INDEX.md`
- docs/governance PR and validation evidence.

**Exit criteria**

Phase 0 is complete only when:

- canonical plan exists in GitHub;
- exact phases are recorded;
- phase-status registry exists;
- decision log exists;
- current-state handoff exists;
- research index exists;
- production firewall is documented;
- future-chat protocol is documented;
- documents are committed;
- appropriate checks for the docs/governance change pass;
- the permanent project plan is accessible from normal repository `main`.

Once complete: mark Phase 0 `COMPLETE`, Phase 1 `NOT STARTED`, update the handoff, and **STOP**.

**Dependency:** none.  
**Next phase:** Phase 1 only after all exit criteria are satisfied.

---

## PHASE 1 — CURRENT LEVLINE AUDIT, BASELINE REPRODUCTION & ERROR DECOMPOSITION

**Purpose:** Understand exactly how current LevLine predicts scores/margins and where it fails.

**Entry criteria**

- Phase 0 is `COMPLETE`.
- Program-control files are on current `main`.
- Production firewall is intact.

**Required work**

Document:

- points prediction pipeline;
- margin calculation;
- spread-setting/public line logic;
- team-strength inputs;
- EPA inputs;
- QB treatment;
- injuries/personnel treatment;
- market inputs;
- total calculation;
- home field;
- weather;
- rest/travel;
- calibration;
- simulation, if any;
- feature transformations;
- training/evaluation methodology.

Reproduce baseline performance from repository data, including:

- home-point MAE/RMSE;
- away-point MAE/RMSE;
- margin MAE/RMSE;
- total MAE/RMSE;
- winner accuracy;
- ATS accuracy;
- market spread MAE;
- market total MAE;
- model-vs-market residuals;
- calibration where applicable.

Perform error decomposition by, at minimum:

- favorite/underdog size;
- home/away;
- season/week;
- QB state;
- injury state;
- team;
- high/low totals;
- blowouts;
- one-score games;
- weather;
- pace;
- model-market disagreement;
- recent team form;
- data-quality state.

Test for failure modes including:

- excessive mean reversion;
- incorrect variance;
- favorite compression;
- blowout underprediction;
- poor possession estimates;
- weak QB propagation;
- red-zone noise;
- unstable recent-form features;
- poor injury treatment;
- duplicated market signal;
- improper calibration.

Complete a data/API inventory covering:

- all configured APIs;
- nflverse/equivalent data;
- rosters;
- depth charts;
- injuries;
- player state;
- weather;
- market feeds;
- news;
- schedule;
- historical results;
- advanced metrics;
- rate limits;
- provenance;
- point-in-time limitations;
- missing information.

**Required outputs**

- current architecture report;
- reproducible baseline report;
- error-decomposition report;
- data/API inventory;
- leakage/PIT risk register;
- concrete research hypotheses for Phase 2.

**Exit criteria**

- current architecture documented;
- baseline reproducible;
- current spread/points accuracy quantified;
- sportsbook baselines quantified;
- major residual patterns documented;
- data/API inventory complete;
- leakage/PIT risks documented;
- specific research hypotheses identified;
- no major baseline uncertainty unresolved.

**Do not build the full successor in this phase.**

**Dependency:** Phase 0.

---

## PHASE 2 — DEEP EXTERNAL RESEARCH & CHALLENGER DESIGN

**Purpose:** Determine from scientific and industry evidence which approaches deserve implementation.

**Entry criteria**

- Phase 1 is `COMPLETE`.
- Baseline, residuals, data inventory, and leakage risks are documented.
- Research questions are concrete enough to constrain literature review.

**Required work**

Study:

- peer-reviewed sports forecasting;
- statistical score prediction;
- NFL analytics;
- market efficiency;
- spread/totals forecasting;
- EPA-based models;
- opponent-adjusted ratings;
- state-space models;
- Elo extensions;
- Bayesian/hierarchical models;
- drive and possession models;
- player value and QB value;
- offensive-line and replacement modeling;
- injury modeling;
- red-zone scoring;
- expected points;
- explosive plays;
- uncertainty/calibration;
- ensembles;
- residual-to-market modeling;
- temporal cross-validation;
- concept drift.

Review respected public/open-source forecasting systems where reproducible.

For every external idea, record:

- prediction target;
- data inputs;
- architecture;
- evidence quality;
- retrospective vs prospective evaluation;
- reproducibility;
- limitations;
- transferability to LevLine.

Explicitly distinguish:

- peer-reviewed evidence;
- strong technical research;
- open-source implementations;
- media/industry claims.

Use Phase 1 findings to create a deliberately limited preregistered challenger shortlist. Potential families may include:

A. improved dynamic team-strength / joint-score model;  
B. possession/drive scoring model;  
C. player/personnel-to-team scoring model;  
D. market-residual model;  
E. controlled ensemble of genuinely distinct signals.

Do not force all five.

**Required outputs**

- literature review;
- external-model review;
- candidate architecture specifications;
- feature hypotheses;
- player-model policy;
- market-residual specification;
- preregistered evaluation protocol;
- frozen final-holdout rules;
- data-gap report;
- paid-data escalation memo if warranted.

**Exit criteria**

- literature review documented;
- external-model review documented;
- candidate architectures specified;
- feature hypotheses specified;
- player-model role specified;
- market-residual approach specified;
- evaluation protocol preregistered;
- final holdout rules frozen;
- challenger shortlist deliberately limited;
- required data/API gaps identified;
- any compelling paid-data candidate brought to the user before dependency creation.

**Dependency:** Phase 1.

---

## PHASE 3 — CONTROLLED CHALLENGER IMPLEMENTATION

**Purpose:** Build only the strongest scientifically justified challengers selected in Phase 2.

**Entry criteria**

- Phase 2 is `COMPLETE`.
- Challenger shortlist and evaluation protocol are preregistered.
- Holdout rules are frozen.
- Required data contracts are available or explicitly fail closed.

**Potential implementation, only where justified**

### Challenger A — Football / team-strength model

Possible components:

- opponent-adjusted EPA;
- dynamic latent strength;
- passing/rushing decomposition;
- early-down efficiency;
- explosive rate;
- success rate;
- recency;
- special teams;
- home field;
- rest;
- contextual adjustments.

### Challenger B — Possession / drive model

Possible hierarchy:

possessions  
-> starting conditions  
-> drive efficiency  
-> TD / FG / punt / turnover / downs / end-half probabilities  
-> score distribution.

### Challenger C — Player/personnel model

Potentially model effects from:

- QB;
- QB replacement;
- offensive line;
- receivers;
- RB usage;
- pass rush;
- secondary;
- expected workload;
- player uncertainty.

This must improve team scoring/margin prediction, not revive the Props product.

### Challenger D — Market residual

Possible form:

`market spread/total + football-based correction`

using legitimate point-in-time information.

### Challenger E — Ensemble

Only if base challengers show complementary OOS information. Stacking must use legitimate out-of-fold base predictions.

**Implementation discipline**

- avoid branch explosion;
- prefer one primary implementation branch;
- use only a small number of justified specialist branches;
- preserve feature provenance and as-of semantics;
- version every candidate explicitly.

**Required outputs**

- implemented preregistered challengers;
- unit/integration tests;
- feature/provenance contracts;
- reproducible research runner(s);
- candidate registry.

**Exit criteria**

- chosen challengers implemented;
- tests pass;
- feature provenance clear;
- as-of semantics preserved;
- model versions explicit;
- outputs reproducible;
- no production model changed;
- implementation ready for frozen scientific evaluation.

**Dependency:** Phase 2.

---

## PHASE 4 — HISTORICAL VALIDATION, ABLATION & MODEL SELECTION

**Purpose:** Determine whether any challenger genuinely improves predictive accuracy.

**Entry criteria**

- Phase 3 is `COMPLETE`.
- Candidate implementations are frozen for evaluation.
- Holdout and chronology rules remain intact.

**Required validation**

Use strictly chronological validation, emphasizing approximately 2023-2026 where legitimate.

Keep tuning inside development data. Preserve untouched holdout data.

Compare appropriate versions of:

- current LevLine;
- sportsbook spread;
- sportsbook total;
- simple scoring-average baseline;
- simple EPA baseline;
- dynamic team-strength baseline;
- market-only forecast;
- football-only challenger;
- market-plus-football residual challenger.

Measure:

- home points MAE/RMSE;
- away points MAE/RMSE;
- margin MAE/RMSE;
- total MAE/RMSE;
- distribution calibration;
- prediction intervals;
- ATS;
- cover probabilities;
- Brier;
- log loss;
- market-relative errors;
- subgroup robustness.

Run preregistered ablations for components such as:

- QB;
- non-QB player state;
- team strength;
- EPA;
- possession modeling;
- drive modeling;
- injuries;
- weather;
- market;
- recency;
- matchup effects;
- calibration;
- simulation;
- ensemble.

Report statistical uncertainty and use game/week clustering where appropriate.

A tiny numerical difference is not automatically meaningful.

Preserve failed challengers and negative findings.

**Required outputs**

- frozen validation report;
- holdout report;
- ablation report;
- statistical uncertainty report;
- robustness report;
- finalist/no-finalist determination.

**Exit criteria**

- all preregistered challengers evaluated;
- holdout uncontaminated;
- ablations complete;
- uncertainty quantified;
- seasonal robustness understood;
- overfitting checks complete;
- market comparison complete;
- any credible finalist identified;
- no retrospective result mislabeled prospective.

**Do not promote anything.**

**Dependency:** Phase 3.

---

## PHASE 5 — PROSPECTIVE SHADOW VALIDATION & OPERATIONAL HARDENING

**Purpose:** Determine whether historical improvement survives real future forecasts.

**Entry criteria**

- Phase 4 is `COMPLETE`.
- At least one credible finalist exists.
- Prospective protocol and evidence threshold are frozen before evaluation begins.

**Required prospective receipts**

Freeze before kickoff immutable records containing, as appropriate:

- candidate/version;
- game ID;
- forecast timestamp;
- data cutoff;
- expected home points;
- expected away points;
- expected margin;
- expected total;
- score distribution;
- uncertainty;
- spread available then;
- total available then;
- book/source;
- market timestamp;
- QB starter;
- major player assumptions;
- injuries;
- data-quality flags;
- source provenance.

Append outcomes later. Grade separately. Never overwrite original predictions.

Avoid Props-style monolithic evidence files. Prefer compact/sharded evidence.

Set the evidence threshold from statistical power and practical reliability, not from a desire to declare victory quickly.

Also harden:

- APIs;
- fallback behavior;
- data failures;
- identity resolution;
- late injury updates;
- QB changes;
- market timing;
- deployment reproducibility;
- artifact size;
- workflow complexity.

**Required outputs**

- immutable prospective ledger/receipts;
- prospective grading report;
- reliability/operations report;
- documented evidence-threshold satisfaction.

**Exit criteria**

Phase 5 is complete only when the preregistered prospective evidence requirement is satisfied and operational reliability is demonstrated.

Do not weaken this standard because historical results look strong.

**Dependency:** Phase 4.

---

## PHASE 6 — FINAL SYNTHESIS & PROMOTION PACKAGE

**Purpose:** Present the evidence needed for a human production decision.

**Entry criteria**

- Phase 5 is `COMPLETE`.
- Historical and prospective evidence is complete enough for a production decision.

**Required final report**

Explain:

- current model;
- proposed architecture;
- research performed;
- external evidence;
- data used;
- features used;
- player-model contribution;
- market-residual contribution;
- baseline performance;
- challenger performance;
- historical holdout performance;
- prospective performance;
- calibration;
- ATS results;
- spread/points/total accuracy;
- market-relative performance;
- statistical uncertainty;
- failed models;
- ablations;
- operational complexity;
- data/API dependencies;
- any paid-data recommendation;
- expected production changes;
- migration plan;
- rollback plan;
- monitoring plan.

Explicitly state what evidence supports promotion and what uncertainty remains.

**Required outputs**

- final synthesis report;
- promotion package;
- migration/rollback/monitoring plan;
- explicit list of unresolved risks.

**Exit criteria**

- package is complete;
- all evidence is linked from `RESEARCH_INDEX.md`;
- production impact is explicit;
- user has enough evidence to decide.

Then **STOP**.

The user must personally give the final green light. Do not merge or deploy a successor as official LevLine before that approval.

**Dependency:** Phase 5.

---

# 9. Mandatory future-chat protocol

Every future chat working on this project must do the following **before substantial work**:

1. Resolve current repository `main`.
2. Read:
   - `research/spread-points-nextgen/MASTER_PLAN.md`
   - `research/spread-points-nextgen/PHASE_STATUS.md`
   - `research/spread-points-nextgen/CURRENT_STATE_AND_NEXT_STEPS.md`
   - `research/spread-points-nextgen/DECISION_LOG.md`
   - relevant entries from `research/spread-points-nextgen/RESEARCH_INDEX.md`
3. Inspect open PRs and active branches associated with the current phase.
4. Determine the single active phase from `PHASE_STATUS.md`.
5. Continue that phase from existing evidence.
6. Do **not** restart completed work.
7. Do **not** redo experiments merely because the new chat did not personally run them.
8. Verify prior results when scientifically necessary, while distinguishing verification from redundant rebuilding.
9. Work only within the current phase unless its exit criteria are genuinely satisfied.
10. Before finishing:
    - update `PHASE_STATUS.md`;
    - update `CURRENT_STATE_AND_NEXT_STEPS.md`;
    - update `DECISION_LOG.md` for new durable decisions;
    - update `RESEARCH_INDEX.md` for important new artifacts;
    - commit the handoff changes.

A phase is **not complete merely because code exists**. Its exit criteria must be satisfied and the program-control files must reflect that.

If a future prompt conflicts with canonical phase state, this master plan and the live status files control unless the user explicitly instructs otherwise.

---

# 10. Redundancy prevention

`CURRENT_STATE_AND_NEXT_STEPS.md` must always contain a prominent **DO NOT REPEAT** section.

Record there:

- baselines already reproduced;
- papers/models already reviewed;
- APIs already evaluated;
- features already rejected;
- experiments already failed;
- branches already superseded;
- known leakage traps;
- approaches ruled out;
- results already treated as authoritative.

Expensive work should not be repeated without a concrete scientific reason.

---

# 11. Final promotion gate

No research result, however favorable, automatically changes production.

Promotion requires all of the following:

- Phase 0 through Phase 6 complete;
- historical chronology/holdout integrity preserved;
- prospective evidence requirement satisfied;
- operational reliability demonstrated;
- migration and rollback plans documented;
- production changes identified explicitly;
- **the user personally gives the final green light**.

Until then, `F-ST-01-FROZEN-2026` remains the official frozen production probability strategy and all successor work remains research-only.

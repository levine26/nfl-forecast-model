# LevLine ATS Research — Canonical Roadmap

**Roadmap date:** 2026-09-25  
**Scope:** research sequencing, novelty governance, evaluation gates, and handoffs  
**Production authorization:** none

## 1. Problem reformulation

The program should stop framing ATS as:

> Build a better independent fair spread than the sportsbook and bet the difference.

That framing has now been tested through multiple direct and indirect variants without stable evidence of incremental ATS information.

The higher-value formulation is:

> At a fixed pre-kick decision horizon, treat the contemporaneous betting market as the strongest available public prior. Ask whether a **genuinely new, point-in-time information channel** or a **materially better probabilistic representation of an already-supported signal** improves the full outcome distribution versus a same-horizon market null. Only after that improvement survives chronology, ablation, calibration, and uncertainty gates should the program translate the probability distribution into ATS decisions or economics.

This changes the unit of scientific progress from “new model architecture” to **new information or validated representation**.

## 2. Mandatory novelty gate

No new candidate may be implemented until a one-page candidate card answers all of the following before target outcomes are inspected:

1. **What exact information is new?** If none, what exact representation defect is being repaired from a predecessor that failed structurally rather than empirically?
2. **Which prior LevLine ATS experiment is closest?** The candidate must state why it is not a renamed version of that experiment.
3. **What same-horizon market null must it beat?** A weaker baseline is prohibited.
4. **What timestamp makes every feature available?** If the timestamp cannot be proven, the feature fails closed.
5. **What is the primary proper score?** Accuracy/ATS/ROI cannot be the primary advancement metric.
6. **What single ablation isolates the claimed mechanism?** If the full gain can be reproduced without the new mechanism, the mechanism claim fails.
7. **What observation would falsify the hypothesis?** The card must contain an explicit kill condition.
8. **What target data have already been seen?** Any known prior outcomes must be disclosed and cannot be called prospective confirmation.

A candidate that fails this novelty gate is archived before implementation.

## 3. Explicit do-not-reopen list

Absent materially new information, do not reopen:

- standalone LevLine fair-line edge thresholds;
- post-hoc edge cutoffs or confidence filters on the rejected fair-line estimator;
- generic football feature boosting around the same market snapshot;
- quantile market residuals merely with a different learner;
- direct CPL classification merely with a different learner;
- F-ST-to-ATS transfer or residual stacking without independently validated components;
- generic static spread/moneyline/total shape tilts;
- center replacement of the sportsbook spread by an independent football point estimate;
- conditional scale searches justified by Frontier V2 M4;
- generic dynamic team-strength or QB-strength features without point-in-time information arrival;
- simple line-movement heuristics that do not prove incremental information beyond later market level;
- deep learning as an architecture-first search over the same inputs;
- selector/threshold fishing after target results.

## 4. Ordered research program

### Lane A — Execute the existing M1 prospective market-state experiment

**Identity:** `FV2-PROS-M1-MARKETSTATE-01`  
**Priority:** highest information-edge lane  
**Type:** prospective only under current data qualification

Do **not** create an M1-v2 merely because this roadmap exists. The current preregistration already contains the correct decomposition:

- primary decision horizon: T-120;
- contemporaneous level: spread, spread price, moneyline, total;
- dynamic state: dispersion, breadth, staleness, T-360→T-120 number/price movement, movement breadth, key crossings, spread/ML consistency;
- separately frozen intermediate target: T-60 minus T-120 consensus spread/price state;
- final target: prospectively locked cover/push/loss distribution at the T-120 quoted spread;
- null: same T-120 level/price/ML/total without the path/dispersion/staleness block.

#### M1 advancement gate

The path/microstructure claim advances only if:

1. future-market prediction improves versus the level-only baseline **and** the improvement is attributable to the path block;
2. final CPL proper score improves versus the same-horizon market-state null;
3. gain is not reproduced by a later-market-level-only control;
4. calibration does not materially deteriorate;
5. effect is not dominated by one week, team, event type, or book;
6. timestamps and quote-age contracts pass with no after-horizon leakage.

If the future-market intermediate target fails, that is strong evidence against the proposed information-arrival mechanism and should reduce willingness to wait for an ATS story.

### Lane B — Execute the existing V3 key-mass prospective program

**Identity:** `FV3-PROS-KMASS-01`  
**Priority:** highest distributional-representation lane  
**Type:** prospective confirmation after historical parameter development

The V3 Phase-1 receipt already freezes the scientific design. The next action remains the one stated there:

1. execute the frozen 2010–2025 parameter-estimation procedure once;
2. persist and hash `frozen_parameters.json`;
3. generate immutable candidate/null T-120 shadow forecasts for qualifying post-freeze games;
4. do not use outcomes when creating those records;
5. do not conduct formal confirmatory evaluation before the frozen minimum evidence conditions are met.

The candidate differs from its strong null only through finite log-mass offsets at 0, |3|, and |7| on an unbounded integer lattice. This is exactly the kind of narrow mechanism isolation the ATS program should preserve.

#### V3 advancement gate

Use the program’s existing receipt, including its minimum sample, multi-season, week-block bootstrap, per-season direction, and leave-one-week-out requirements. This roadmap does not weaken or accelerate those gates.

### Lane C — Continue M2 QB/player information-delta capture, but keep it secondary

**Identity:** `FV2-PROS-M2-QBDELTA-01`  
**Priority:** secondary information-arrival lane

The scientifically distinct hypothesis is not “QB quality matters.” The market plainly prices QB quality. The hypothesis is narrower:

> A point-in-time change in expected starter/availability/role contains incremental information before the contemporaneous market fully incorporates it.

Therefore:

- only timestamped information state available by the horizon is admissible;
- missing historical/player-state evidence remains missing;
- realized inactive status, later starter announcements, final snap shares, or hindsight role labels cannot be backfilled;
- generic rolling QB/team ratings are not a substitute for the event-time information delta;
- a same-horizon market response must be included so the experiment tests **unpriced residual information**, not the obvious value of a quarterback.

The historical M3 result, where the QB component hurt the full dynamic-state candidate, is negative evidence against treating generic QB strength as a free ATS edge. M2 remains open only because its mechanism is information timing, not static QB quality.

### Lane D — Optional new historical representation study: tail-safe joint-score successor

**Priority:** secondary / conditional  
**Type:** historical, only after a new preregistration  
**Predecessor:** `ATS-JSIP-V1` failed structurally before target scoring

This is the only clearly non-duplicative historical study presently visible without acquiring new dynamic market data. It is permissible because V1 did **not** generate an empirical result; its numerical support/tail contract failed before scoring.

A successor must be a new identity and satisfy all of the following before any result is viewed:

- unbounded or demonstrably tail-safe score/margin support; no endpoint folding;
- numerical mass/tail audits across the full nuisance grid before target scoring;
- market spread remains the location anchor unless a pre-result derivation proves otherwise;
- strongest accepted spread + moneyline + key-mass market-only distribution is the null where compatible;
- explicit ablation of any joint-score-specific dependence/correlation mechanism;
- proper joint/discrete score is primary; CPL/Brier/calibration secondary; ATS hit/ROI diagnostic;
- chronology-clean rolling/expanding evaluation using only pre-2026 outcomes for design/tuning;
- no completed-2026 outcomes in candidate selection, hyperparameter search, or rescue;
- no architecture search after seeing target-period results.

#### Purpose of Lane D

Lane D asks whether representing home/away scores jointly improves **distribution quality** beyond the best market-centered margin model. It should not be sold internally as a likely new information edge. If it merely generates prettier score distributions without improving a proper score against the strongest market null, it stops.

### Lane E — New historical M1 only if the data gate changes

Historical M1 stays closed under current free data. It may reopen only if a coherent fixed-horizon panel becomes available and is qualified **before** target performance is inspected.

A data amendment must prove:

- season × game × book × horizon coverage;
- stable book identity / rename mapping;
- spread line and side-price completeness;
- moneyline and total completeness;
- quote-age/freshness distributions at each fixed horizon;
- exact at-or-before selection semantics;
- no future interpolation or closing-line backfill;
- no post-kick observations;
- coherent source semantics across seasons;
- licensing/rights class.

Do not stitch heterogeneous free sources across eras to manufacture sample size. No paid-data purchase is authorized by this roadmap.

### Lane F — Calibration and uncertainty only after an information/representation survivor

Possible tools include:

- isotonic or Platt-style calibration where chronology-clean and preregistered;
- distributional calibration diagnostics;
- conformal or adaptive-conformal uncertainty sets for selection/risk control under distribution shift;
- block-bootstrap or hierarchical uncertainty by NFL week/season.

These are **not signal generators**. They may improve honesty, reliability, or selectivity, but they cannot convert a rejected information model into a valid edge.

### Lane G — Decision economics only after probability quality survives

Only after a candidate survives its proper-score and calibration gates should the program study:

- price-aware expected value;
- break-even probability under actual vig;
- no-bet regions;
- uncertainty-aware selectivity;
- stake sizing / Kelly fractions under conservative probability shrinkage;
- closing-line value as a diagnostic where horizon semantics support it;
- ROI and hit rate with confidence intervals.

A profitable-looking historical slice cannot rescue a model that fails its preregistered probability-quality gate.

## 5. Phased execution protocol for any future new candidate

### Phase 0 — Prior-work collision check

Search all ATS branches, receipts, candidate registries, and failure atlases. Produce a nearest-predecessor table. If the idea is substantially the same information source + target + null, stop.

### Phase 1 — Mechanism and source research

Before code:

- peer-reviewed / academic literature;
- professional/public modeling practice;
- open-source implementation review;
- data-source provenance and timing semantics;
- explicit contradictory evidence;
- reason the mechanism might fail.

Deliver a candidate research card and source ledger.

### Phase 2 — Outcome-blind data qualification

Verify timestamp availability, joins, coverage, missingness, book/provider identity, and leakage boundaries. Do not inspect candidate target performance. A failed data gate closes or postpones the candidate.

### Phase 3 — Preregistration and freeze

Freeze:

- identity;
- target and horizon;
- feature list;
- market null;
- model family and limited hyperparameter grid;
- chronology folds;
- primary/secondary metrics;
- ablations;
- uncertainty procedure;
- advancement/futility rules;
- production firewall.

Commit the preregistration before scoring.

### Phase 4 — One canonical historical execution, if historically authorized

Run the frozen design once. Invalid numerical/leakage/data executions are not results and must be logged separately. Do not silently patch a failed experiment and reuse the same identity.

### Phase 5 — Scientific adjudication

Require, at minimum:

- paired primary proper-score delta versus strongest same-horizon market null;
- block-aware uncertainty;
- season stability;
- calibration diagnostics;
- mechanism ablation;
- leave-one-week/team/event concentration checks where relevant;
- null reproducibility;
- leakage/red-team receipt.

### Phase 6 — Prospective shadow, only for a survivor

Freeze exact code/config/data contracts and create immutable pre-kick predictions. No production effect.

### Phase 7 — Production review, only after prospective evidence

Production promotion requires explicit user authorization after the full evidence package is complete. Historical success alone never auto-promotes.

## 6. Universal kill criteria

Stop a candidate if any of the following occurs:

- point-in-time provenance cannot be established;
- required data semantics differ across seasons in a way that confounds the mechanism;
- after-horizon data are needed to create a feature;
- the candidate cannot reproduce the market null on a null-equivalent configuration;
- primary paired proper score does not improve under the frozen gate;
- the claimed mechanism’s ablation reproduces the gain;
- later market level alone reproduces a claimed path-information gain;
- calibration degrades materially enough to negate practical interpretation;
- improvement is concentrated in one season/week/team/event and fails robustness requirements;
- a numerical support/tail contract is invalid;
- candidate success exists only after searching thresholds/hyperparameters on the target set.

## 7. Research priority order

1. **M1 prospective execution** — strongest still-open new-information hypothesis.
2. **V3 key-mass Phase 2 / prospective shadows** — strongest isolated representation hypothesis.
3. **M2 point-in-time QB/player delta** — narrower secondary information-arrival hypothesis.
4. **Tail-safe JSIP successor**, if a historical study is desired — representation research, not assumed edge.
5. **Historical M1 reopening only if a coherent data source is qualified outcome-blind.**
6. **Calibration/selectivity/economics only after a survivor.**

This ordering deliberately avoids another large undirected candidate search. The goal is to spend experiments on hypotheses that are genuinely different from what has already failed.
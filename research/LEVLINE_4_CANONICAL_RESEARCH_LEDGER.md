# LevLine 4 canonical research ledger

Status: **research-only evidence ledger; no production promotion**

As-of: 2026-09-15 America/Los_Angeles / 2026-09-16 UTC

This ledger reconciles the material LevLine 4 research lineage before any new information-residual candidate is executed. It is deliberately conservative: frozen receipts are not rewritten, completed 2026 outcomes are not used for candidate selection, and conflicting historical prediction vectors are namespaced rather than silently collapsed.

## 1. Incumbent and production firewall

The forecast of record is `F-ST-01-FROZEN-2026` at T-120. The frozen winner model is the two-input logistic stack on market logit and nested-PURE logit, with the deployed coefficient/provenance contract preserved separately. LevLine 4 research may collect later market states, inactive/personnel state, uncertainty and structured football intelligence, but may not mutate prior T-120 locks or production probabilities.

The older 75% PURE / 25% MARKET formulation is retained only as a historical benchmark. It is not the current forecast of record.

## 2. F-ST historical benchmark reconciliation

There is **not yet one provenance-safe anonymous F-ST proper-score number**. Three quantities must remain distinct:

| Vector | Meaning | Games | Accuracy | Brier | Log loss | Status |
|---|---|---:|---:|---:|---:|---|
| `FST-ORIGINAL-OOS-LINEAGE` | Original registered season-forward F-ST historical experiment recorded in the experiment ledger | 1,087 | 0.680773 (740/1087) | 0.210774 | 0.608977 | Frozen historical evidence; original prediction-vector artifact still needs exact lineage recovery |
| `FST-FINAL-COEFFICIENT-BACKSCORE` | Final target-2026 coefficients applied back across 2022-2025 | 1,087 | 0.680773 (740/1087) | 0.209888 | 0.606793 | Reconstruction diagnostic only; not an OOS estimate because 2022-2025 informed the final fit |
| `FST-CURRENT-KEYED-CHRONO-AUDIT` | Current reproducible season-forward stack rebuilt from `challenger_outputs/fst/provenance/training_frame_keyed.csv` | 1,087 | 0.681693 (741/1087) | 0.210653 | 0.608713 | Chronology-clean current audit tied to the keyed provenance frame |

Operational resolution:

1. Never cite `0.209888` as historical OOS performance.
2. Never overwrite the original experiment-ledger metrics with the later keyed audit.
3. Any comparison must name the exact vector/artifact lineage used.
4. The current keyed audit is the reproducible current-main chronology audit, while the original experiment vector remains the frozen evidence used at the time of the historical research decision.
5. Issue #182 remains a provenance task until the exact original `FST-ORIGINAL-OOS-LINEAGE` prediction vector or deterministic generator/input digest is recovered. Until then, no single F-ST Brier/log-loss value should be called the canonical historical benchmark without its lineage name.

This resolves the scientific interpretation without rewriting history: the apparent disagreement is a provenance/vector-lineage disagreement, not permission to choose the better-looking score.

## 3. Material historical research ledger

| Work | Hypothesis / candidate | Data / horizon | Evaluation | Result / uncertainty | Disposition | Still relevant? |
|---|---|---|---|---|---|---|
| PR #183 | LevLine 4 market-first, later-information architecture | T-120 incumbent; prospective T-60/T-45/T-30; post-inactive information | Preregistered prospective gate | No outcome selection authorized; >=200 eligible games and >=14 weeks required | **MERGED governance** | Yes; primary governance contract |
| PR #184 | Archive official inactives around game day | Official NFL inactive surfaces, T-100 through T-20 archival | Source preservation, not model evaluation | Raw archive only; no numerical player effect | **MERGED infrastructure** | Yes; H6/H1 source substrate |
| PR #187 | Freeze exact later-horizon shadows | Genuine T-60/T-45/T-30 snapshots | Immutable candidate identity and timestamp checks | Refuses late PURE/market state; no backfill | **MERGED infrastructure** | Yes |
| PRs #190/#192/#193 | Strict timing governance | T-120/T-60/T-45/T-30 | Complete-case, identical-game horizon evaluation; evaluator independently checks timing | Valid timing error `[-7.5, 0]` min; positive error/missing provenance fails closed | **MERGED infrastructure** | Yes; prevents false historical/prospective horizon claims |
| PR #191 | De-vig / consensus ablations | Same request-batch multi-book odds | Frozen proportional / two-outcome Shin / power and robust consensus | No NFL outcome winner selected | **MERGED frozen ablation** | Yes; H5 |
| PR #194 | Consolidated LevLine 4 recommendation | Existing historical + timing evidence | Synthesis | Market-first late-information direction; empirical best horizon unresolved | **MERGED synthesis** | Yes, superseded only where later evidence is more specific |
| PR #196 | Accuracy / boundary research | 1,087 historical games | Chronological accuracy audit, component-resolved comparisons, paired diagnostics | Later current-main keyed audit shows F-ST 741 vs market 735; component stack 744, but tiny disagreement sample and no proven proper-score superiority | **RESEARCH EVIDENCE** | Yes, but vector lineage must be named |
| PR #206 | Selective error-correction gates | Same historical paired universe | Season stability, topology, conformal diagnostics | Component +3 correct not season-stable; filters did not establish robust switch rule | **NOT PROMOTABLE** | Yes; strong warning against post-hoc switching |
| PR #207 | Strict-PIT market path | Genuine four-horizon market ledger | Deterministic path diagnostics only | Net movement, total variation, efficiency, reversals, excursion, acceleration available only when all required PIT states exist | **MERGED infrastructure / prospective only** | Yes; H4 substrate |
| PR #208 | Generic dynamic Elo residual | Historical games, fixed Elo form | OOS comparison | Standalone Elo weak; F-ST+Elo 739 vs F-ST 741; switches 5-7 | **REJECTED** | Yes as negative evidence; does not reject structural-break-specific H7 |
| Issue #4 | Conditional scenario engine | Conditional player/QB state | Requires numerically validated component | UI/context shipped; numeric conditional deltas prohibited until validation | **BLOCKED intentionally** | Yes; H10 |
| Issue #178 | Post-100 optimization program | Historical <=2025 | Model/feature/calibration/ensemble/distribution tournament under firewall | Completed without authorizing a superior production replacement | **COMPLETED** | Yes; constrains duplicate tournaments |
| Issue #182 | F-ST metric reconciliation | 1,087 historical games | Provenance audit | Multiple non-interchangeable F-ST vectors identified; final-coefficient backscore is not OOS; current keyed chrono audit differs from original historical experiment vector | **OPEN provenance** | Critical |
| V09A | Lagged player-value state | Prior-game target/rush value | 2022-2025 chronological OOS | v09A Brier 0.211860 vs v0.8 0.211764; no gain | **REJECTED** | Yes; player value cannot enter merely by intuition |
| V09B original | Availability-weighted player value | Historical pregame availability required at T-120 | Fit prohibited until source qualification | Original run blocked by missing qualifying 2025 status history; later 2025-only reconstruction does not retroactively authorize fit | **SOURCE-BLOCKED / historical disposition preserved** | Yes |
| 2025 availability reconstruction (#142/#143 lineage) | Recover narrow 2025 pregame practice-state chronology | Pinned nflverse + official NFL historical pages + supplemental mirror | Source qualification | 6,064/6,068 canonical rows resolve; matched chronology/practice agreement passed; four unresolved | **QUALIFIED NARROW INFRASTRUCTURE** | Yes, but insufficient for 2022-2025 unified fit |
| Cross-season availability attempt (#148 lineage) | Harmonize 2022-2025 availability | Multiple historical seasons | Coverage/chronology qualification | Failed closed because complete equivalent postseason/official history could not be established | **BLOCKED** | Yes; primary reason H1/H2 are not retrospectively fit now |
| V09C | Unit continuity / rotation state | Prior completed-game state | Chronological OOS, week-block bootstrap | Brier delta vs v0.8 -0.000102, 95% CI approximately [-0.000414, 0.000189]; materially worse than market | **REJECTED** | Yes |
| V09D registered personnel interactions | Personnel-conditioned matchup interactions | Required validated V09C state | Dependency gate | Not executed because V09C failed | **DEPENDENCY-BLOCKED** | Yes; H3 is a materially new version only after H1/H2 validation |
| V09D EWMA interactions | Four generic EWMA offense-defense interactions | Historical shifted pregame EWMA | Chronological OOS | Brier delta vs v0.8 -0.000062, CI crosses zero; significantly worse than market | **REJECTED** | Yes; prohibits generic interaction soup |
| F-MR-01 | Fixed market residual | Historical | Registered OOS | Failed registered gate | **REJECTED** | Yes; no rescue |
| F-MI-01 | Margin-informed probability | Historical | Registered OOS | Failed registered gate | **REJECTED** | Yes |
| F-LS-01 | Generic latent team strength | Historical | Registered OOS | Failed registered gate | **REJECTED** | Yes |
| Joint score-distribution lane | Coherent score/margin distribution | Historical | Winner/Brier/margin metrics | Higher raw winner accuracy but worse Brier and margin MAE | **REJECTED for winner-probability core** | Yes; distributional capability may remain separate |
| Boundary Gate / Selective Upset Gate | Switch F-ST near decision boundary | Historical | Disagreement and season stability | Interesting point estimates, insufficient stable evidence; no safe switch rule | **NOT PROMOTABLE** | Yes |
| Conformal diagnostic | Identify reliable direction/switches | Historical | Split-conformal diagnostic | Many singleton predictions but no validated singleton reversal rule | **DIAGNOSTIC ONLY** | Yes |
| Market path diagnostics | Price-path contains information beyond current state | Prospective strict PIT | No retrospective imputation | Instrumentation exists; no outcome-driven 2026 rule selection allowed | **PROSPECTIVE-ONLY** | Yes |
| Transaction source V5 | Full 2017-2021 transaction recapture | NFL transaction archive | Source-shape/coverage | Failed 72 no-header endpoints; preserved as failure | **FAILED** | Yes as negative evidence |
| Transaction V6 PR #280 | Interpret 72 no-header endpoints | Exact frozen endpoints | Raw-shape audit | 72/72 reproduced explicit `No Transactions Available` shape | **OPEN infrastructure stack** | Yes; source-shape only |
| Transaction V7 PR #281 | Qualify explicit-empty semantics | V6 plus controls | Candidate rule 72 positives / 32 negatives | First run passes source semantic rule; no state/chronology authority | **OPEN stacked infrastructure** | Yes |
| Transaction V8 PR #282 | Full ledger recapture with V7 semantics | 2017-2021 x month x category | Coverage/capture only | Even a pass cannot authorize membership/availability labels; durable archive still separate | **OPEN stacked infrastructure** | Yes |
| Modern identity V3 (#270 lineage) | Resolve modern player-team-game identity | 2017-2021 game-book identity universe | Independent calibration + final resolution | Calibration agreement ~0.9971; 137,800/138,205 resolved; 405 unresolved; zero ambiguous | **QUALIFIED IDENTITY ONLY** | Yes; does not prove game-day membership |
| Modern membership / DNP / roster lanes (#239/#242/#265/#277 lineage) | Derive active game-day membership | Game books / roster status | Semantic/chronology qualification | DNP and weekly roster semantics do not map safely to active membership; chronology/parser gates failed | **NOT QUALIFIED** | Critical blocker for historical lineup fit |

## 4. Current data-governance state by hypothesis

### H1 expected lineup residual — PROSPECTIVE-ONLY / infrastructure

There is enough identity and partial availability infrastructure to define the schema, but not one equivalent 2022-2025 PIT contract for active probability, expected role and game-day membership. Historical fitting now would require fabrication or heterogeneous semantics. Do not fit.

### H2 QB scenario / replacement — PROSPECTIVE-ONLY / infrastructure

Existing v0.8 QB state proves that chronology-safe prior QB features can be useful, but the richer starter-probability/replacement mixture needs contemporaneous starter/availability state. Build and capture it; do not invent conditional deltas.

### H3 personnel-conditioned matchups — BLOCKED BY H1/H2

Generic interactions already failed. The new hypothesis is scientifically distinct because it conditions on actual expected personnel states, but it cannot be executed before those states are qualified.

### H4 market path / microstructure — PROSPECTIVE-ONLY, infrastructure already merged

Strict four-horizon capture and path diagnostics are present. Historical closing lines cannot substitute for true T-minus paths. Continue frozen collection; completed 2026 outcomes cannot be used to design a path rule.

### H5 bookmaker quality / consensus — PROSPECTIVE-ONLY frozen ablation

Per-book rows and de-vig candidates are appropriate. Historical book weights require genuinely PIT book-level history; do not label a book `sharp` from reputation or derive weights from 2026 outcomes.

### H6 inactive information surprise — INFRASTRUCTURE MERGE JUSTIFIED

This is best treated first as an event-study ledger linking pre-event expected state, timestamped official inactives, post-event expected state and market response. It should measure what information arrived and what price changed before asking whether residual direction exists.

### H7 structural regime change — PREREGISTERED, LOWER PRIORITY

Generic Elo failed. A structural-break model remains a different hypothesis only if events such as new QB/coach/system/trade/OL configuration are fixed from PIT evidence before outcomes. No generic strength retuning is authorized.

### H8 structured beat intelligence — SCHEMA / EXTRACTION VALIDATION ONLY

NFL Beat usefully foregrounds HC/OC/DC/QB/personnel/beat context, but its public interface is not evidence of forecast superiority. LevLine may use LLMs to extract timestamped factual states into governed fields; an LLM may not assign probability points or emit a qualitative override.

### H9 uncertainty-aware shrinkage — CAPABILITY INFRASTRUCTURE

Uncertainty is useful for limiting correction magnitude, not for choosing direction. This should be tested only after a directional residual candidate independently exists.

### H10 conditional scenario engine — BLOCKED BY ISSUE #4 DEPENDENCY

Keep context-only scenarios until H1/H2 or another component passes numerical chronological OOS validation.

## 5. Architecture implication before new outcomes

The smallest scientifically defensible target architecture remains:

`same-horizon robust market prior`

plus only if independently additive:

`small regularized football-information residual`

with the residual decomposed into expected-lineup/QB state first, then market-path state, and personnel-conditioned interactions last.

Calibration is a separately evaluated layer, not an automatic transformation.

No evidence currently authorizes replacing `F-ST-01-FROZEN-2026` as the official forecast. The immediate high-value work is source qualification, point-in-time capture, event alignment and frozen challenger construction—not adding unvalidated feature weight.

## 6. Next authorized empirical sequence

1. Finish and durably archive the transaction/source stack without granting semantics it did not test.
2. Qualify a point-in-time expected-lineup observation contract prospectively, including explicit unknown/missing states.
3. Capture QB starter probability/replacement state and official inactive events with timestamps.
4. Continue strict T-120/T-60/T-45/T-30 multi-book collection and market-path diagnostics.
5. Do not execute H3, H9 directional shrinkage or H10 numerical scenarios until their dependencies pass.
6. If a sufficiently equivalent pre-2026 historical source universe is eventually qualified, execute H1 then H2 once under their frozen identities using season-forward evaluation and same-horizon market conditioning. Otherwise keep them prospective-only.
7. Production promotion remains governed by the existing prospective minimum sample and evidence gate; infrastructure merges do not imply probability promotion.

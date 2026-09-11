# LevLine / Sunday Signal — Current Implementation Ledger

_Last reconciled against repository state: 2026-09-11_

This file tracks completion of the **current build / validation / data-capture / research-infrastructure roadmap**. It is not a claim that forecasting accuracy can no longer improve. Model optimization after this roadmap is a separate phase with its own preregistration.

## Non-negotiable production guardrails

- Official 2026 winner probability is the frozen `F-ST-01-FROZEN-2026` production strategy.
- Frozen F-ST coefficients, architecture, T-120 lock behavior, and immutable identity may not change without explicit production-promotion authorization after prospective evidence.
- Completed-2026 outcomes may not select features, model families, architecture, coefficients, hyperparameters, ensemble weights, calibration choices, or decision thresholds.
- Research remains isolated from production and may not mutate official `outputs/`, locks, grading, or Sunday Signal publication.
- Technical source qualification is based on data integrity; active automated research remains constrained to $0 sources unless separately authorized.
- Source qualification never automatically authorizes a probability feature or production dependency.

## Current production foundation — COMPLETE

- Leakage-safe schedule-first forecasting pipeline.
- Sequential pregame Elo and shifted rolling/EWMA football state.
- PURE classification plus margin/total/score infrastructure.
- Historical snapshot and append-only lock/grading semantics.
- Automated weekly, standalone-game, Sunday, and market-refresh workflows.
- Frozen production F-ST stack using market and nested-PURE logits.
- Immutable F-ST training identity, registered literal coefficients, exact artifact verification, reconstruction evidence, runtime provenance, and <=1e-12 reconstruction parity.
- Legacy probability retained for rollback/counterfactual grading without rewriting historical locks.

## Point-in-time market infrastructure — COMPLETE FOR CURRENT ROADMAP

- Vig-free production market conversion remains operational.
- Research market capture preserves constituent books, timestamps, freshness, source counts, and capture horizon.
- T-120 market-state research and additional horizon studies are isolated from production.
- Market refreshes may update generated outputs without rewriting research history.
- Prediction exchanges remain a separate research family rather than being silently folded into sportsbook consensus.

**Production status:** existing production semantics remain frozen. New market research is not automatically promoted.

## Injury / all-position availability — FINAL HISTORICAL GATE IN VALIDATION

Completed:

- Prospective official 2026 injury-report archive with immutable raw-source capture and chronology controls.
- Qualified 2025 Weeks 1-22 composite reconstruction using stable GSIS identity, official NFL historical pages, conservative filing-day chronology before T-120, and explicit unresolved states.
- 2025 qualification achieved 6,064 / 6,068 clean canonical player-week mappings; matched practice-state agreement and matched-row T-120 chronology were 100%; four rows remain unresolved rather than guessed.
- Historical game designation remains diagnostic-only; actual current-game snaps, postgame participation, and hindsight inactive state are prohibited substitutes.

Historical cross-season audit status:

- V1 reached its real 2022 identity gate and **failed** rather than hiding unresolved evidence: 5,543 of 5,683 distinct official rows resolved to unique GSIS IDs (`97.5365%`), below the frozen `99.5%` minimum. The V1 threshold was not relaxed and its failure artifact/receipt is retained.
- V2 is separately preregistered in PR #147. It adds the pinned nflverse GSIS-keyed player master solely as a deterministic alias dictionary; historical team/week membership and all injury/practice state still come from the original historical sources.
- V2 prohibits fuzzy/edit-distance matching, manual result-informed aliases, current/latest-team inference, and use of status/position/outcomes to choose an identity.
- All V1 chronology/state gates remain unchanged: 22 official pages per season, 100% schedule matching, >=99.5% bidirectional identity resolution, >=98.5% practice-status agreement, 100% matched-row T-120 chronology, >=99% fully qualified practice state, and the legacy timestamp integrity gate.
- Passing V2 would qualify only the common 2022-2025 source/state contract. It would not retroactively change V09B's historical disposition, fit V09B, authorize a probability feature, or change production.

**Roadmap status:** pending PR #147 exact-head qualification and merge, or an honest fail-closed disposition if V2 does not satisfy the frozen gates.

## Depth charts / personnel / player-state infrastructure — COMPLETE FOR CURRENT ROADMAP

- Stable-ID chronological player-state foundation from prior completed games.
- Depth-chart state and venue/source qualification infrastructure.
- Snap/role/personnel continuity research surfaces.
- Expected Lineup Impact / Impact Monitor research engine with observed-vs-modeled separation.
- Publication-safe player-impact card schema and redistribution review controls.
- Retrospective same-game snaps/participation are recursively rejected from pregame impact state.

**Production status:** explainability/research only unless a separately preregistered probability experiment qualifies and is explicitly promoted.

## Weather / venue / travel context — COMPLETE FOR CURRENT ROADMAP

- Free-source weather capture contract, due-game scheduler, venue resolution, provenance, missingness handling, and research workflow exist.
- Weather/context state is separated from production probabilities until incremental predictive value is established under a registered experiment.

## Tactical / process / advanced-player research — COMPLETE FOR CURRENT ROADMAP

- FTN process research infrastructure and preregistration.
- NGS/PFR/nflverse advanced-player adapters and chronology policies.
- Opponent-adjusted, QB-context, pressure/process, player continuity, and matchup research have versioned experiments or research contracts rather than silent production insertion.
- Historically rejected candidates remain rejected; dependency-blocked candidates are not mislabeled as empirical failures.

## Provenance / reproducibility / source governance — COMPLETE

- Fail-closed research firewall protects model, lock, generated-output, and site surfaces.
- Research-looking files trigger isolation review independent of branch naming.
- Production F-ST modules are protected from research-scoped modification.
- Source qualification registry separates technical qualification, redistribution metadata, research authorization, and production authorization.
- Durable F-ST identity/reconstruction evidence and 2025 availability qualification receipts are committed.
- Implementation repairs and failed source contracts are append-only and regression-tested; gates are not weakened to make CI pass.

## Challenger / validation infrastructure — COMPLETE FOR CURRENT ROADMAP

- Leakage-safe historical challenger evaluation and season/week-aware paired uncertainty.
- Immutable prospective shadow candidate identity and T-120 alignment.
- Current-main F-ST shadow materialization scores registered frozen literals; reconstruction is verification-only.
- Brier score is the primary probability-quality metric, with log loss, winner accuracy, calibration, disagreement slices, and uncertainty as supporting evidence.
- Historical experiment registry records completed, rejected, dependency-blocked, and source-blocked dispositions without result-informed rescue tuning.

## Evidence-backed explanations / Impact Monitor — COMPLETE AS RESEARCH INFRASTRUCTURE

- Player-impact monitor and card contracts separate source-observed facts from LevLine-modeled impact.
- Availability uncertainty remains explicit rather than converted into fabricated certainty.
- Unsafe/restricted rows can be suppressed rather than republished.
- No explanatory card is allowed to mutate the official winner probability merely by existing.

## Sunday Signal front-facing surface — CURRENT VERSION PRESERVED

- Current Sunday Signal publication remains operational and is intentionally not being redesigned during final roadmap completion.
- Draft PR #128 remains non-production.
- Production UI merge requires explicit authorization.
- Post-roadmap UI/UX work will use the current interface as the baseline and preserve working functionality.

The next design phase will optimize for progressive disclosure: a novice should understand the forecast and writeup immediately, while advanced users can drill into probability decomposition, market disagreement, movement, uncertainty, provenance, and niche football context.

## Historical experiment integrity

- `V09A-PLAYER-VALUE-001`: rejected; no post-result rescue.
- `V09B-AVAILABILITY-001`: original source-blocked/rejected disposition remains historical fact. Later source recovery does not retroactively rerun it.
- `V09C-UNIT-STATE-001`: rejected.
- registered V09D/F-family failures remain rejected or dependency-blocked as recorded.
- Frozen F-ST is the official 2026 production strategy; prospective evidence, not completed-2026 selection, governs any future change.

## Current completion gate

The currently defined implementation / validation / data-capture / research-infrastructure roadmap reaches **100% only after**:

1. the chronology-safe 2022-2025 availability source/state program reaches a defensible terminal state under frozen gates — either qualification and merge, or a documented fail-closed result demonstrating that the current $0 historical evidence cannot safely support the intended state; and
2. this ledger and related high-level documentation are reconciled to that authoritative result.

A failed source hypothesis does not make the software roadmap incomplete forever; hiding or weakening a failed gate would. The roadmap is complete when the infrastructure can reach and preserve the truthful scientific disposition.

Until those items are complete, do not declare the roadmap 100% and do not activate the post-100 model-optimization tournament.

## What happens at 100%

After the current roadmap is closed, LevLine moves into a separately preregistered optimization/maximization phase. That phase may research model families, calibration, ensembles, uncertainty, feature families, and additional $0 NFL data techniques using leakage-safe historical/OOS methodology, but it may not use completed-2026 outcomes for selection.

In parallel, Sunday Signal enters a collaborative UI/UX research and redesign phase. The current interface remains the baseline; redesign should simplify the first layer for non-football users while preserving deep analytical detail through progressive disclosure. No production UI replacement occurs without explicit authorization.

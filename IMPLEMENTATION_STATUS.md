# Implementation Status

_Last reconciled: 2026-09-12_

This file is the authoritative high-level implementation ledger. Historical research documents remain useful evidence, but they should not be read as the current production roadmap.

## Production — built and active

### Forecast/model contract
- Frozen official 2026 winner-probability path: `F-ST-01-FROZEN-2026`.
- Separately preserved football-only and market signals.
- Canonical public forecast contract with one official winner/probability.
- Probability-implied presentation margin/line derived from the official probability.
- Independent margin model preserved only as a diagnostic.
- Coherent projected-score presentation tied to the official probability direction.
- Fail-closed contradiction checks for winner/probability/margin/score semantics.

### Forecast-of-record / accountability
- T−120 pregame lock is the forecast of record.
- Immutable lock rows take precedence over later current/live rows in public presentation.
- Post-kickoff publication without a valid immutable pregame lock is rejected.
- Prediction history is append-only and graded without rewriting the original receipt.
- 2026 History is a first-class Sunday Signal surface.

### Data / scheduled production
- nflverse schedule/results/PBP/EPA pipeline.
- Sequential pregame Elo and leakage-safe rolling/EWMA team features.
- Market implied-probability conversion and recurring market refresh.
- Pregame/daily production workflows with generated-output reconciliation.
- Power-rating and diagnostic publication feeds.

### Context / editorial
- Injuries and personnel context with conservative usage enrichment.
- Scheme/matchup, QB-history, coaching/staff, weather, travel, and scenario context.
- Groq researched matchup editorial with approved/direct-source validation.
- Fail-closed source, coverage, length, banned-language and full-slate publication gates.
- Substantive editorial uniqueness checks with explicit exemption for standardized official injury/status wording.
- Deterministic rationale normalization for clean underlength provider fragments while preserving final publication contracts.

### Sunday Signal product
- Premium responsive desktop/mobile UI.
- Top Signals, search, Model vs Market, Signal Strength presentation tiers, What Changed, The Signal, research provenance, Forecast Movement, Key Developments, Power Ratings, History receipts, and methodology/technical disclosure.
- Presentation tiers are derived UI shorthand only; they are not new model outputs.
- Fail-closed Impact Monitor remains explainability-only unless a probability feature is separately authorized.
- Responsive/browser QA covers 1440, 1180, 1024, 768, 430, 390, and 320 widths.

## Sunday Signal Check remediation status

| Check finding | Current disposition |
| --- | --- |
| Locked forecast replaced by a newer live refresh | **Fixed and regression-tested.** Canonical public build selects the immutable lock row first. |
| Current-week `#VALUE!` spreadsheet errors | **Currently clean.** Repository feed and connected dashboard tabs `THIS WEEK`, `GAME DETAIL`, `RAW FEED`, and `LAST GOOD` were re-audited with no `#VALUE!` matches. |
| Ambiguous `BIGGEST EDGE` / `Model Line` semantics | **Retired.** Public presentation now distinguishes probability-implied line, market line, and LevLine-vs-market probability difference. |
| Standardized injury-report wording triggering uniqueness failures | **Fixed and regression-tested.** Recognized factual/status scaffolding is exempt; substantive prose is still checked. |
| Stale implementation roadmap/docs | **Remediated in the current repository-hygiene pass.** README and this ledger now describe the active system rather than V0.1-era future work. |

## Research-only / unresolved by design

### Historical availability qualification
The 2022–2025 availability lane remains fail-closed. PR #148 records the terminal V3/V4 result: available historical sources could not establish a complete deterministic official-club final injury-report dataset for all affected postseason team-weeks without inference. Downstream qualification was therefore not executed. No production feature should be promoted from this failed lane unless a new independently verifiable source resolves the missing coverage before downstream metrics are inspected.

### Conditional scenario engine — issue #4
The presentation/guardrails exist, but alternative numerical scenario probabilities remain future research. They may be produced only from features that independently pass chronological OOS validation and remain explicitly conditional/separate from the official forecast.

### F-ST legacy freeze provenance — issue #104
The current guardrails/reconstruction evidence are implemented, but the missing original pre-fit candidate-freeze provenance cannot be recreated retroactively. Later evidence must remain labeled as reconstruction/shadow evidence; registered identity/tolerance cannot be rewritten to erase the exception.

### Post-100 research program — draft PR #141
Retained as a preregistration/research workspace only. Any actual challenger implementation should be split into a fresh, narrowly scoped research PR against current `main`, and completed 2026 outcomes remain prohibited for selection/tuning.

## Repository hygiene disposition

- PR #128: closed as superseded by the shipped Sunday Signal redesign/product layer.
- PR #151: closed as superseded by the Groq production editorial pipeline already on `main`.
- PR #163: closed as superseded by the broader underlength-rationale repair already on `main`.
- PR #141: intentionally remains open **draft** as future research preregistration, not a production release candidate.
- Issues #4 and #104: intentionally remain open because they record real unresolved research/governance constraints, not stale implementation tasks.

## Non-negotiable research firewall

- Completed 2026 outcomes may not select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration.
- Research-only sources/features may not silently become production probability inputs.
- Historical locked forecasts may not be mutated.
- Missing/insufficient point-in-time evidence must fail closed rather than be inferred.

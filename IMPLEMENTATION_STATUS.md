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
- Groq and Daily production workflows use isolated concurrency keys so pull-request validation cannot cancel an in-flight `main` editorial run.
- A long Groq research run can reconcile deterministic forecast/diagnostic output advances from a concurrent Daily publish, while context/editorial/code changes remain fail-closed.

### Context / editorial
- Injuries and personnel context with conservative usage enrichment.
- Scheme/matchup, QB-history, coaching/staff, weather, travel, and scenario context.
- Groq researched matchup editorial with approved/direct-source validation.
- A validated provider Read owns the human headline + paragraph 1 for its game across later deterministic context refreshes; paragraph 2 is always regenerated from the current canonical LevLine row.
- Groq API/transport and focused-validation failures are isolated by `game_id` rather than invalidating successful provider Reads for the rest of the slate.
- Failed games can use fresh validated ChatGPT editorial fallback only for the explicitly failed IDs; successful Groq games are not eligible for fallback overwrite.
- A last-valid editorial game can serve as a temporary continuity bridge when Groq and fresh ChatGPT are unavailable, with explicit `requires_chatgpt_refresh` status until current research is supplied.
- Fail-closed source, coverage, length, banned-language and full-slate publication gates remain authoritative after any fallback.
- Substantive editorial uniqueness checks explicitly exempt standardized official injury/status wording.
- Deterministic rationale normalization repairs clean underlength provider fragments while preserving final publication contracts.
- Public-boundary text safety repairs malformed source/guardrail punctuation such as `Achilles LevLine...` without changing sourced status wording or model values.

### Sunday Signal product
- Premium responsive desktop/mobile UI.
- Top Signals, search, Model vs Market, Signal Strength presentation tiers, What Changed, The Signal, research provenance, Forecast Movement, Key Developments, Power Ratings, History receipts, and methodology/technical disclosure.
- Presentation tiers are derived UI shorthand only; they are not new model outputs.
- Fail-closed Impact Monitor remains explainability-only unless a probability feature is separately authorized.
- Responsive/browser QA covers 1440, 1180, 1024, 768, 430, 390, and 320 widths.
- Week Board row typography is explicitly pinned to the normal-width UI stack, with browser regression coverage preventing reintroduction of condensed/compressed matchup text.

## Sunday Signal Check remediation status

| Check finding | Current disposition |
| --- | --- |
| Locked forecast replaced by a newer live refresh | **Fixed and regression-tested.** Canonical public build selects the immutable lock row first. |
| Current-week `#VALUE!` spreadsheet errors | **Currently clean.** Repository feed and connected dashboard tabs `THIS WEEK`, `GAME DETAIL`, `RAW FEED`, and `LAST GOOD` were re-audited with no `#VALUE!` matches. Active browser QA also rejects `#VALUE!` on the Week Board. |
| Ambiguous `BIGGEST EDGE` / `Model Line` semantics | **Retired and regression-tested.** Public presentation distinguishes probability-implied line, market line, and LevLine-vs-market probability difference; active browser QA rejects the stale labels. |
| Standardized injury-report wording triggering uniqueness failures | **Fixed and regression-tested.** Recognized factual/status scaffolding is exempt; substantive prose is still checked. |
| Successful Groq prose replaced solely because deterministic context became newer | **Fixed.** Provider authority is game-scoped; freshness becomes an advisory/regeneration signal rather than an automatic deterministic overwrite. |
| One Groq failure affecting successful games | **Fixed.** API and focused-validation failures are isolated per game and recovered only through validated game-scoped fallback. |
| ChatGPT safety fallback required a complete 14-game replacement | **Fixed.** The failed-game ingest path accepts only IDs marked `requires_chatgpt_refresh` and refuses successful Groq game IDs. |
| Malformed injury/body-part stitching into LevLine guardrails | **Fixed.** Punctuation-only public text normalization repairs the mechanical boundary while preserving factual/status language. |
| Pull-request Groq CI cancelling an active production Groq run | **Fixed.** Workflow concurrency is scoped to the Git ref. |
| Daily forecast publish racing Groq research | **Hardened.** Deterministic output-only advances are reconcilable; context/editorial/code advances still fail closed and latest model facts are rerendered before publication. |
| Compressed/condensed Week Board typography | **Fixed and regression-tested.** Matchup-row text uses the normal UI font stack with normal stretch/variant/kerning. |
| Stale implementation roadmap/docs | **Remediated and maintained.** README and this ledger describe the active architecture, current editorial fallback behavior, and LevLine 4 research boundary. |

## LevLine 4 — research-only, active

The preregistered program is documented in `research/LEVLINE_4_RESEARCH_SPEC.md` with machine-readable contracts under `research/`.

Current implemented/research direction includes:

- preserve production T−120 F-ST as the accountability incumbent;
- prospectively preserve genuine later market horizons including T−60, T−45 and T−30 rather than synthesizing historical late snapshots from closing data;
- preserve point-in-time official inactive/source evidence separately from practice/game-status reporting;
- keep player/lineup, weather, market-construction and calibration candidates behind the research firewall;
- compare later-horizon and model-adjusted candidates against both the T−120 incumbent and the same-horizon market on common eligible games;
- never let shadow research rewrite production locks or probabilities without a separately governed promotion decision.

Active research pull requests are intentionally not described here as shipped behavior until they merge.

## Research-only / unresolved by design

### Historical availability qualification
The 2022–2025 availability lane remains fail-closed. PR #148 records the terminal V3/V4 result: available historical sources could not establish a complete deterministic official-club final injury-report dataset for all affected postseason team-weeks without inference. Downstream qualification was therefore not executed. No production feature should be promoted from this failed lane unless a new independently verifiable source resolves the missing coverage before downstream metrics are inspected.

### Conditional scenario engine — issue #4
The presentation/guardrails exist, but alternative numerical scenario probabilities remain future research. They may be produced only from features that independently pass chronological OOS validation and remain explicitly conditional/separate from the official forecast.

### F-ST legacy freeze provenance — issue #104
The current guardrails/reconstruction evidence are implemented, but the missing original pre-fit candidate-freeze provenance cannot be recreated retroactively. Later evidence must remain labeled as reconstruction/shadow evidence; registered identity/tolerance cannot be rewritten to erase the exception. `F-ST-01-FROZEN-2026` is nonetheless the explicit LevLine 3 production winner-probability path. Historical research metadata such as `production_promotion_authorized=false` does not supersede the later production release decision.

### Historical F-ST metric reconciliation — issue #182
The apparent F-ST Brier mismatch is now understood as two different evaluation quantities: the registered chronology-clean architecture OOS estimate versus a retrospective backscore produced by applying the final target-2026 coefficients to historical rows that contributed to those final coefficients. They must stay separately labeled; the reconstruction backscore must not replace the chronological OOS benchmark for historical model-performance claims.

### Post-100 research program — issue #178
The surviving leakage-safe optimization/preregistration program from draft PR #141 lives in issue #178 as research backlog. Any actual challenger implementation should be split into a fresh, narrowly scoped research PR against current `main`, and completed 2026 outcomes remain prohibited for selection/tuning.

## Repository hygiene disposition

- PR #128: closed as superseded by the shipped Sunday Signal redesign/product layer.
- PR #151: closed as superseded by the Groq production editorial pipeline already on `main`.
- PR #163: closed as superseded by the broader underlength-rationale repair already on `main`.
- PR #141: closed after its surviving post-100 research scope was transferred to issue #178; its product-vision material was already superseded by shipped PRs #174/#175.
- PR #176: merged after full responsive, dashboard, research-firewall, and F-ST validation; fixes Week Board typography and adds Sunday Signal Check browser guards.
- PR #177: merged; repository status/docs were reconciled to the active production architecture.
- PR #195: merged after contextual, Groq, failed-game fallback, research-firewall, and full model-regeneration gates; establishes persistent per-game provider authority, validated game-scoped ChatGPT fallback, and public text-safety repair.
- PR #197: merged after Groq, research-firewall and full model-regeneration validation; isolates production Groq concurrency from PR validation and reconciles deterministic Daily output advances during long provider research.
- Issues #4, #104, #178, and #182 intentionally remain open because they are real research/governance records, not stale production defects.
- Active PRs are intentionally left out of the shipped-disposition list until they merge or close.

## Non-negotiable research firewall

- Completed 2026 outcomes may not select, tune, refit, rescue, or re-freeze production architecture/features/hyperparameters/calibration unless a separately preregistered prospective decision policy explicitly permits grading a previously frozen candidate; outcomes still may not be used to redesign that candidate mid-evaluation.
- Research-only sources/features may not silently become production probability inputs.
- Historical locked forecasts may not be mutated.
- Missing/insufficient point-in-time evidence must fail closed rather than be inferred.

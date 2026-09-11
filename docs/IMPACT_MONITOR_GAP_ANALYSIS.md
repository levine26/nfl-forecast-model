# LevLine Impact Monitor — Gap Analysis

Status: research/explainability only. No player-impact output is authorized as an input to the official F-ST winner probability.

## Existing foundation

LevLine already has most of the hard analytical separation needed for a safe Impact Monitor:

- `player_state_research.py` builds leakage-safe, stable-ID player value from completed prior games. Current-game usage updates state only for later games.
- `player_impact_engine.py` converts explicit modeled player value, replacement quality, expected role and availability uncertainty into player/unit/team explainability. It refuses retrospective snap/outcome fields and always sets `probability_feature_authorized=false`.
- `player_impact_cards.py` keeps source-observed statistics separate from LevLine-modeled impacts, requires provenance/as-of/sample-size/redistribution review, and prohibits fantasy-style projections.
- `availability_qualification.py` fails closed unless a historical availability source proves point-in-time T-120 semantics, stable identity mapping and reconstruction of the specific state being used.
- `injuries.py` can surface current official NFL practice/game-status context but does not infer absence or translate current status into a point adjustment.
- `personnel_impact.py` can add conservative prior-season usage context; ambiguous abbreviated identities are discarded and usage is not converted into an unvalidated forecast adjustment.
- `availability_2025_composite_reconstruction` now supplies a technically qualified 2025-only historical practice-state layer with a durable exact-head receipt; it remains research-only and does not authorize a probability feature.

## Missing layer addressed in Phase 4

`player_impact_monitor.py` is the publication-safe compositor. It provides a deterministic per-game player payload while preserving the research firewall:

1. Only `source_observed` rows whose `redistribution_review_status` is exactly `approved` may be emitted.
2. `pending`, `restricted`, and `do_not_publish` observed rows are suppressed rather than republished.
3. LevLine modeled impacts remain explicitly labeled modeled research and cannot be described as official NFL statistics.
4. Qualified, prospective-unqualified and unknown availability states remain visible as provenance/context, but all are `probability_feature_authorized=false` in this monitor.
5. Retrospective current-game snaps, participation, results, and post-kickoff status reconstruction fail closed recursively.
6. Fantasy-style yardage, reception, touchdown and fantasy-point projections remain outside scope.

## Remaining data gaps

### Cross-season availability harmonization

The former 2025 source-coverage gap is no longer the blocker. PR #142 qualified a 2025 Weeks 1-22 practice-state reconstruction: 6,064 of 6,068 canonical rows map cleanly, matched-row T-120 chronology is 100% under the conservative filing-day bound, and four rows remain unresolved rather than guessed.

The remaining historical availability problem is **cross-season equivalence**. Before any 2022-2025 probability experiment is executed, the 2022-2024 history and the 2025 composite must share one audited contract for status meaning, stable identity, chronology, missingness, source outages, normalization, and feature construction. A source-qualified 2025 table cannot simply be concatenated with earlier seasons and treated as a validated model feature. Final 2025 game designation remains diagnostic-only rather than a feature-authorized state.

### Current availability

The official-current injury-report path is useful for an explanatory monitor, but current injury context is not automatically a validated probability feature. Historical source qualification and current prospective state are separate scopes. The verified Sleeper archive supports 2026-only point-in-time/shadow research from February 1, 2026 onward, with completed-2026 outcomes prohibited from selection.

### Player identity

The modeled-impact engine requires a stable player ID. Conservative name matching in the editorial/personnel layer is not sufficient to authorize a modeled player impact. Any live source adapter must resolve a stable crosswalk or fail closed.

### Advanced observed statistics

Route share, pressure, separation, tracking and similar statistics may be useful in the monitor, but technical accessibility does not imply publication authorization. Each source-specific metric needs an explicit redistribution decision before it can appear in the public-safe payload; those display decisions remain separate from technical source qualification.

### Replacement and expected-role inputs

Expected role share, replacement value and availability probability must be explicit inputs with uncertainty. The engine intentionally refuses to fill missing values from current-game realized snaps or postgame participation.

## Integration policy

The Impact Monitor should be introduced to the site only after its payload contract and source governance are green. The site should hide the panel when no safe rows exist rather than fabricate player estimates or expose restricted data. Initial integration is explanatory only and must not change `final_home_prob`, official LevLine winner, lock behavior, or grading.

Any future proposal to feed player availability/impact into a winner, margin, total or score model requires its own pre-registered experiment, chronology-safe historical evidence, prospective validation where necessary, and explicit production-promotion authorization. Resolving a source blocker after a prior experiment was dispositioned does not retroactively execute or change that experiment's historical result.

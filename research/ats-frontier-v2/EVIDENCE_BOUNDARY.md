# EVIDENCE BOUNDARY

## Canonical football/ATS sign contract

Maintain the existing ATS convention inherited from ATS V1 unless a later governance amendment explicitly changes it:

- margin `M = home_score - away_score`
- home spread `L`
- ATS residual `R = M + L`
- home cover if `R > 0`
- push if `R == 0`
- home loss if `R < 0`

## Phase-1 admissible evidence

- immutable prior LevLine result receipts and registries;
- peer-reviewed/technical literature;
- open-source code and documentation;
- disclosed professional methodology;
- data-provider schema/coverage/pricing documentation;
- outcome-blind source qualification and repository state.

## Phase-1 prohibited evidence

- newly trained Frontier candidates;
- new Frontier OOF predictions;
- new Frontier ATS hit rates, ROI or threshold searches;
- completed-2026 outcomes for architecture/feature/source/model/prior decisions;
- future/closing quotes used to construct an earlier market state;
- final inactives/starters/snaps/weather used before they were actually known.

## Market timestamp rule

Every historical market record used at horizon `T` must have an observation timestamp `<= T`. A provider's “closing” field or nflverse schedule spread cannot be relabeled as an earlier horizon without direct source provenance. Existing opaque historical market is labeled `historical_closing_late_benchmark_exact_horizon_opaque`.

## Player-state rule

Separate ability from information availability. Realized snap counts, game participation and final outcome may train lagged latent ability models after publication, but the target game's pregame feature must be an expectation based on information available at the frozen prediction timestamp.

## Revision rule

A present-day archive that stores only a corrected final record is ex-post unless it can reconstruct the historical as-of state. Revision history and observation timestamp are part of the feature, not metadata that can be ignored.

## Evaluation boundary for later phases

Phase 3 freezes all model/evaluation choices before Phase 4 target results. Phase 4 uses chronology-clean OOF folds and same-row market nulls. Phase 6 uses future games only with immutable pregame records. Results never authorize retrospective rescue.
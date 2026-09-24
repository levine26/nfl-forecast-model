# PHASE 4 HANDOFF

Phase 4 is **Controlled Historical Development & Ablation**.

Phase 4 is `NOT_STARTED` until the Phase-3 primary research PR and immutable closeout are merged.

## Authorized historical candidates only

1. `FV2-HIST-M3-DSSM-01`
2. `FV2-HIST-M4-DMARGIN-01`

No historical M1 or M2 candidate is authorized under the current data gate.

## Exact first Phase-4 action

Before fitting either candidate, implement and run the synthetic/red-team tests in `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`, including:

- M3 chronology/sign/common-row tests;
- M4 normalization/tail/push/sign tests;
- explicit completed-2026 firewall.

The first candidate fit is prohibited until those pre-result tests pass.

## Then implement frozen candidates

Implement **only** the files/contracts frozen in Phase 3:

- `M3_PREREGISTRATION.md`;
- `M4_PREREGISTRATION.md`;
- `MARKET_NULL_CONTRACT.md`;
- `CHRONOLOGY_CONTRACT.md`;
- `FEATURE_AND_INPUT_CONTRACT.md`;
- `MODEL_FAMILY_AND_HYPERPARAMETER_CONTRACT.md`;
- `EVALUATION_PROTOCOL.md`;
- `ABLATION_PROTOCOL.md`;
- `SELECTIVITY_AND_ECONOMICS_CONTRACT.md`;
- `UNCERTAINTY_PROTOCOL.md`.

## Frozen development sequence

For M3:

1. build chronology-safe prior-game state table;
2. implement market-only null;
3. implement static-state ablation;
4. implement dynamic no-QB state;
5. implement full frozen M3;
6. execute nested weekly walk-forward 2022–2025;
7. score proper metrics on paired rows;
8. run 10,000+ week-block bootstrap and concentration diagnostics.

For M4:

1. pass numerical synthetic tests before target scoring;
2. implement constant-scale Student-t null;
3. implement conditional-scale/key ablations;
4. execute the same chronological outer development seasons;
5. score integer-margin log score first, then secondary probability/calibration diagnostics;
6. run paired uncertainty.

## Prohibited in Phase 4

- adding a candidate family;
- adding a feature family;
- adding a horizon/source because results look favorable;
- adding key-number categories beyond 0/|3|/|7|;
- post-hoc calibration rescue;
- selective betting thresholds;
- tuning from ATS/ROI;
- fitting M1 on unqualified free history;
- reviving broad M2 injury history;
- completed-2026 outcomes;
- production changes.

## Failure handling

A failed candidate remains failed under its frozen identity. Record the result and continue to the next frozen candidate. Do not rescue it in place.

## Phase-4 stop

After all frozen candidates/ablations have produced their preregistered development evidence and uncertainty, stop and hand off to Phase 5. Do not promote anything to production.
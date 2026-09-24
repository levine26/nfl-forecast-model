# ATS Next-Generation Phase 2 — Stage D Pre-Execution Correction

**Status:** FROZEN BEFORE ANY ACCEPTED STAGE-D RESULT  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Stage:** D — final evidence synthesis and uncertainty

## Issue found before synthesis

The accepted Q1 and Q3 evidence registries bind every evidence file by SHA-256, including summary JSON files. Those summary JSON files contain their relative output paths. The first Stage-D runner draft would have regenerated Q1/Q3 under nested `stage_d/reproduced_q1` and `stage_d/reproduced_q3` directories. That would have produced pathname-only summary hash drift even if every prediction and metric were identical.

No accepted Stage-D synthesis result existed when this was discovered. The controlling authorization-head synthesis had not completed and is superseded by this correction.

## Correction

Q1 and Q3 are now regenerated at the exact canonical paths used by their accepted workflows:

- `research_outputs/ats_nextgen/q1`
- `research_outputs/ats_nextgen/q3`

The runner still requires every accepted evidence-file SHA-256 to match before Stage-D uncertainty is computed. The Stage-D outputs remain isolated under `research_outputs/ats_nextgen/stage_d`.

## Scientific effect

None. This correction changes only reproduction-path identity. It does not change:

- Q1, Q2, or Q3 code, predictions, tuning, or accepted classifications;
- the Phase-2 historical gate;
- the 10,000-draw `(season, week)` paired bootstrap;
- seed 26 or 95% percentile intervals;
- loss definitions, comparison nulls, slices, hit-rate threshold, or reporting rules;
- completed-2026 firewall;
- production forecasting.

## Revalidation rule

The corrected execution head must independently pass the Stage-D contract before its synthesis job may begin. The earlier contract success remains historical evidence for the pre-correction contract-only head but does not authorize a corrected-head result by itself.

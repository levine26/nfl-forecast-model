# ATS Next-Generation — Q3 Stage C Implementation Freeze

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2  
**Stage:** C — Q3  
**Candidate:** `ATS-Q3-DIRECT-CPL-HURDLE-V1`  
**Status:** **IMPLEMENTATION FROZEN; NO Q3 HISTORICAL RESULT ACCEPTED**  
**Branch:** `research/ats-nextgen-phase2-q3`  
**Stage-B merge / Stage-C base:** `16859845573c3344ed82ae0b9bd27fa8b891eee4`  
**Validated pre-result implementation head:** `d9dbfe24af7fd19f5b22e76fd5f57dd83c606a60`

## Pre-result validation

Dedicated Stage-C contract workflow on head `d9dbfe24af7fd19f5b22e76fd5f57dd83c606a60`: **SUCCESS**.

At this boundary:

- Q3 historical fitting accepted: **NONE**;
- Q3 historical performance generated/accepted: **NONE**;
- Q3 rescue/redesign after result: **NONE**;
- completed-2026 outcomes used: **0**;
- production forecasting changed: **NO**;
- Stage D opened: **NO**.

The workflow at this head was contract-only; no historical Q3 job was reachable.

## Frozen scientific implementation blobs

The following Git blob identities define Q3 V1 before results:

- hurdle/model core `src/nfl_forecast/challenger_ats_nextgen_q3.py`: `c707ec8994fa27038ec9e14c757f5a67e99b6e86`;
- reporting contract `src/nfl_forecast/challenger_ats_nextgen_q3_reporting.py`: `89660aaefeb14624bc16434cf91dd2f08feef067`;
- fail-closed runner `scripts/run_challenger_ats_nextgen_q3.py`: `733a5cac7cbcc9efa6d378fb92edc4eea1585893`;
- hurdle contract tests `tests/test_challenger_ats_nextgen_q3.py`: `2456c5a70c4a74c5672d38e5adcd74f8b954e519`;
- reporting tests `tests/test_challenger_ats_nextgen_q3_reporting.py`: `0d914311f7572f7e7a3e1964900fb24759014f69`;
- contract-only Stage-C workflow `.github/workflows/research_ats_nextgen_q3.yml`: `4ba0358df0f7970f15ec8111850a11f336b43706`;
- opening receipt `research/ats-nextgen/Q3_STAGE_C_OPENING_RECEIPT.md`: `7c1000402134b399a2052fde86aff83e7bd7cb12`;
- scoring receipt `research/ats-nextgen/Q3_STAGE_C_SCORING_RECEIPT.md`: `98c6e2fb56f6fa886bc9d53f237b9589b6014800`;
- opening registry `research/ats-nextgen/phase2_q3_opening_registry.json`: `8897016dc576660ff95f72bcc0e2de97c00905e3`.

The later workflow authorization that makes historical execution reachable may change only CI orchestration. If any frozen scientific blob above changes, the earlier contract success no longer authorizes historical evidence and a new exact-head pre-result validation is required.

## Binding upstream identities

Before the first Q3 fit the runner must still verify:

- Phase-2 canonical gate SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- completed-2026 firewall remains active;
- Q2 classification remains `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`;
- Q2 has no accepted OOF artifact or primary performance result;
- Q2/Q3 blend remains unavailable.

## Frozen primary scientific question

The only primary incremental comparison is:

`Q3` vs `Q3_M2`

on exact common 2022–2025 outer OOF rows using three-outcome multinomial log loss.

Q2 comparison/blending is unavailable, not replaced.

No post-result change to learner, feature contract, C grid, C-pair tie-break, structural half-line push rule, preprocessing, scoring semantics, calibration policy, or comparison set is authorized.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
# ATS Next-Generation Phase 2 — Stage D Accepted-Artifact Loading Correction

**Status:** FROZEN BEFORE ANY ACCEPTED STAGE-D RESULT  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Stage:** D — final evidence synthesis and uncertainty

## Why this correction is required

Stage D is an evidence-synthesis stage. Its frozen scientific contract authorizes no candidate fitting, retuning, rescue, or reconstruction. The authoritative inputs are the immutable evidence artifacts accepted in Stage A and Stage C.

An earlier Stage-D implementation attempted to prove reproducibility by invoking the current Q1 and Q3 runners and then requiring byte-for-byte equality with every accepted upstream file. That is stronger than the Stage-D scientific requirement and, more importantly, makes final synthesis depend on the current repository implementation rather than the already-accepted evidence package.

Workflow `35936031216` demonstrated the problem and failed **before Stage-D uncertainty was computed**. Its contract job `107433187521` succeeded, but synthesis job `107433470129` stopped on:

`Q1 regenerated evidence drifted for q1_inner_alpha_selections.csv: expected=22f9c1f12a359e3861c72c0f6d6f5839356b959944dc187fbaf68574b2f4fe45 actual=253d3389feb7e34b461b8c0c913224ca15e35d16fb5962aab23d495930ddb073`

That failure is a reproduction-plumbing failure, not a Stage-D statistical result and not a reason to modify Q1, Q2, Q3, or the Stage-D uncertainty contract.

No accepted Stage-D synthesis result existed when this correction was frozen.

## Corrected evidence-loading rule

Stage D now consumes the accepted immutable GitHub Actions artifacts directly and verifies every file against the accepted result registries before computing any uncertainty statistic.

### Q1 accepted evidence

- workflow run: `35920622523`;
- artifact ID: `10776898518`;
- artifact name: `ats-nextgen-q1-35920622523`;
- artifact digest: `sha256:b544a4928a3e2ab80861b7b3fcf581a6b51355961b80aa05ddc5e4a0554d0c36`;
- accepted OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`.

### Q3 accepted evidence

- workflow run: `35931071604`;
- artifact ID: `10781521222`;
- artifact name: `ats-nextgen-q3-35931071604`;
- artifact digest: `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`;
- accepted OOF SHA-256: `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`.

The runner verifies the complete Q1 and Q3 file-hash maps already frozen in `phase2_q1_result_registry.json` and `phase2_q3_result_registry.json`. A missing file or any SHA mismatch fails closed before bootstrap.

Q1 and Q3 model runners are no longer invoked by Stage D.

## Scientific effect

None. This correction changes only how accepted evidence bytes are loaded. It does not change:

- Q1, Q2, or Q3 code, predictions, tuning, classifications, or accepted evidence identities;
- the Phase-2 historical gate;
- the frozen Stage-D statistical module or tests;
- the 10,000-draw paired `(season, week)` bootstrap;
- seed `26`, 95% percentile intervals, or delta orientation;
- Q1/Q3 metric definitions;
- the Clopper-Pearson hit-rate diagnostic;
- slice definitions;
- the Q2 structural-invalidity / blend-unavailable rule;
- the completed-2026 firewall;
- production forecasting.

The prior regeneration attempts are superseded and cannot be cited as Stage-D evidence.

## Fresh authorization rule

The corrected exact head must independently pass the Stage-D contract. The synthesis job must depend on that contract, verify the frozen Stage-D scientific blobs, download the exact accepted Q1/Q3 artifacts listed above, verify their registered file hashes, and only then compute Stage-D outputs.

No Stage-D result from a pre-correction or regeneration-based head is acceptable.

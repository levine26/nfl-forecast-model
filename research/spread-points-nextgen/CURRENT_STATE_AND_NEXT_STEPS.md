# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-21 America/Los_Angeles  
**Program authority:** `research/spread-points-nextgen/MASTER_PLAN.md`  
**Observed main at Phase-0 start:** `536d6ab712028e374b42815db106f9fcb5d28053`  
**Active phase:** Phase 0 — Master Program Initialization  
**Phase status:** IN PROGRESS  
**Active branch:** `docs/spread-points-nextgen-phase0`

## Phase objective

Create durable GitHub institutional memory, phase governance, production firewall, research index, and future-chat handoff rules. Do not begin the Phase 1 baseline audit in this chat.

## Work completed

- Verified repository default branch is `main`.
- Verified observed Phase-0 base main SHA: `536d6ab712028e374b42815db106f9fcb5d28053`.
- Verified current production winner-probability strategy is `F-ST-01-FROZEN-2026`.
- Verified production artifact at `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json` is `production_frozen` and production-authorized.
- Verified `src/nfl_forecast/fst_production.py` pins `ACTIVE_PRODUCTION_STRATEGY = F-ST-01-FROZEN-2026`.
- Verified frozen identity/provenance controls and fail-closed tests exist.
- Located current score/margin/total implementation in `src/nfl_forecast/pipeline.py`, `src/nfl_forecast/models.py`, and `src/nfl_forecast/public_forecast.py`.
- Verified the independent margin/total regressions remain diagnostic while the public fair spread is probability-implied from the official winner probability plus margin sigma.
- Located existing research firewall workflow `.github/workflows/research_validation.yml`, including protected production surfaces and research-firewall tests.
- Verified retired Props documentation exists at `docs/props/`.
- Verified full retired Props snapshot branch exists at `archive/props-pre-revamp-2026-09-21`.
- Verified Props is disabled in production and the old implementation is not to be reattached wholesale.
- Located existing data/source governance at `research/LEVLINE_DATA_SOURCE_MATRIX.md`.
- Inspected branch inventory relevant to F-ST, Props, archive, and spread work.
- Confirmed there were no open pull requests at the Phase-0 inspection point.
- Created canonical branch `docs/spread-points-nextgen-phase0`.
- Created `MASTER_PLAN.md`.
- Created `PHASE_STATUS.md`.

## Important findings

1. **Production winner is verified, not assumed.** The active production strategy is F-ST-01-FROZEN-2026.
2. **Current public spread semantics are not the same thing as the independent margin model.** The pipeline fits a margin regressor, but public fair margin/spread is derived from official win probability through a Normal-margin bridge.
3. **Research is already strongly firewalled.** Existing CI explicitly checks research work against protected production surfaces.
4. **Props retirement is authoritative.** The prior Props product was intentionally removed from active production; only scientific concepts may be reused.
5. **Branch explosion is a known operational failure mode.** The new program must use one primary branch per phase/coherent block and only a small number of specialist branches.
6. **The repository already has substantial research/data infrastructure.** Phase 1 should inventory and reuse it rather than rebuilding it.

## Commits on active Phase-0 branch

- `7a5e969933f2239469a89ddcf9f35d81c10d333c` — initialize master plan.
- `ba360428a52705779a86a8265245d5ecc962a6b0` — add phase registry.

Additional Phase-0 control-file commits will be recorded before completion.

## PRs

None yet for this phase. Open the docs/governance PR only after all required control files are present.

## Tests / validation

Not yet run for the Phase-0 branch. The relevant repository workflow is `.github/workflows/research_validation.yml`, which triggers for `research/**` changes and includes production-surface firewall checks.

## Key artifacts inspected

- `README.md`
- `config/model.yaml`
- `src/nfl_forecast/fst_production.py`
- `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json`
- `research/fst/F-ST-01-FROZEN-2026.json`
- `docs/FST_FREEZE_PROVENANCE.md`
- `tests/test_fst_frozen_identity.py`
- `tests/test_fst_production.py`
- `tests/test_official_locking.py`
- `src/nfl_forecast/pipeline.py`
- `src/nfl_forecast/models.py`
- `src/nfl_forecast/features.py`
- `src/nfl_forecast/public_forecast.py`
- `.github/workflows/research_validation.yml`
- `research/LEVLINE_DATA_SOURCE_MATRIX.md`
- `docs/props/PROPS_RESEARCH_ARCHIVE_2026-09.md`
- `docs/props/README.md`
- `docs/props/RESET_MANIFEST.md`
- `archive/props-pre-revamp-2026-09-21`

## Failed approaches worth remembering

- Repository code search for several exact terms returned no results despite the files existing; directory/API inspection was more reliable for Phase 0.
- Do not infer current production status from the research F-ST registry alone: the production-packaged artifact and active production code are the direct production boundary.
- Do not equate the independent margin model with the public official fair spread; current public semantics deliberately separate them.

## Unresolved questions

None that block Phase 0. Detailed architecture, baseline reproduction, data completeness, and residual failure modes belong to Phase 1.

## Blockers

None at this stage.

## Exact next atomic tasks

1. Create `DECISION_LOG.md`.
2. Create `RESEARCH_INDEX.md`.
3. Re-read all five control files on the branch for internal consistency.
4. Compare the branch against `main` and confirm only `research/spread-points-nextgen/**` documentation changed.
5. Open a docs/research-governance PR to `main`.
6. Inspect CI/checks and resolve only genuine docs/governance issues without weakening the research firewall.
7. Merge when validation is satisfactory and the diff is documentation/governance-only.
8. Verify canonical files from current `main`.
9. Update this file and `PHASE_STATUS.md` to record **Phase 0 COMPLETE** and **Phase 1 NOT STARTED**, with the exact Phase 1 starting action.
10. STOP. Do not begin Phase 1 in this chat.

# DO NOT REPEAT

- Do not re-verify from scratch that F-ST-01-FROZEN-2026 is the current production probability strategy unless repository state changes materially.
- Do not rediscover the retired Props preservation branch; it is `archive/props-pre-revamp-2026-09-21`.
- Do not reactivate or wholesale merge retired Props code.
- Do not treat the research F-ST registry’s historical shadow status as the sole source of truth for current production; use the production artifact and active code.
- Do not conflate `expected_margin` with the probability-implied public fair spread.
- Do not redo a broad branch archaeology exercise during Phase 1 without a concrete need; use `RESEARCH_INDEX.md`.
- Do not begin literature review or challenger implementation before Phase 1 exit criteria are satisfied.
- Do not alter F-ST coefficients, official locks, historical grading, or production forecast behavior.

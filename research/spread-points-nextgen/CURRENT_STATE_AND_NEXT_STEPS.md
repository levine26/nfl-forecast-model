# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-21 America/Los_Angeles  
**Program authority:** `research/spread-points-nextgen/MASTER_PLAN.md`  
**Phase-0 base main:** `536d6ab712028e374b42815db106f9fcb5d28053`  
**Phase-0 governance merge SHA:** `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25`  
**Phase 0 status:** **COMPLETE**  
**Phase 1 status:** **NOT STARTED**  
**Active phase:** None. The next chat may begin Phase 1 only after following the mandatory startup protocol.

## Completed Phase 0 objective

GitHub is now the authoritative institutional memory for the next-generation LevLine research program covering spread setting, scoring margin, team points, totals, and joint score distributions.

Phase 0 created, validated, merged, and verified the permanent governance/handoff layer without changing production forecast behavior and without beginning the Phase 1 baseline audit.

## Work completed

- Resolved the repository default branch as `main`.
- Recorded the Phase-0 base main SHA `536d6ab712028e374b42815db106f9fcb5d28053`.
- Verified current production winner-probability strategy from direct production surfaces as `F-ST-01-FROZEN-2026`.
- Verified the packaged production artifact is `production_frozen` and the active production strategy is pinned to F-ST.
- Verified F-ST frozen identity, provenance, reconstruction-tolerance, and fail-closed test contracts.
- Located the current score/margin/total implementation in `pipeline.py`, `models.py`, `features.py`, and `public_forecast.py`.
- Verified current semantics distinguish:
  - the independently fitted diagnostic margin/total regressions; and
  - the probability-implied public fair margin/spread derived from the official F-ST winner probability.
- Located and verified the existing research firewall workflow and protected production surfaces.
- Verified the retired Props implementation is disabled in production.
- Verified retired Props research is preserved in `docs/props/` and branch `archive/props-pre-revamp-2026-09-21`.
- Located existing source/data governance in `research/LEVLINE_DATA_SOURCE_MATRIX.md`.
- Inspected relevant branch/PR state and confirmed no pre-existing open PR blocked Phase 0.
- Created the canonical directory `research/spread-points-nextgen/`.
- Created all five permanent control documents:
  - `MASTER_PLAN.md`
  - `PHASE_STATUS.md`
  - `CURRENT_STATE_AND_NEXT_STEPS.md`
  - `DECISION_LOG.md`
  - `RESEARCH_INDEX.md`
- Recorded the exact Phase 0 -> Phase 6 sequence, entry/exit criteria, dependencies, outputs, branch discipline, artifact discipline, anti-leakage rules, free/open-data policy, paid-data escalation rule, and final human approval gate.
- Recorded the mandatory future-chat startup and shutdown protocol.
- Opened docs/research-governance PR **#512**.
- Verified the PR diff contained exactly five files, all under `research/spread-points-nextgen/`.
- Preserved the existing CI/firewall rules unchanged.
- Passed the repository’s research firewall.
- Passed the full existing research-validation workflow and final gate.
- Merged PR #512.
- Verified all five canonical files directly from `main` at merge SHA `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25`.
- Updated `PHASE_STATUS.md` on `main` to mark **Phase 0 COMPLETE** and **Phase 1 NOT STARTED**.

## Important findings

1. **Production winner is verified, not assumed.** The active production strategy is `F-ST-01-FROZEN-2026`.
2. **The current score/spread system has two distinct semantics.** The pipeline fits an independent margin model, but Sunday Signal’s official public fair line is derived from the official win probability and margin sigma.
3. **Research is already strongly firewalled.** Existing CI protects production surfaces and fail-closes cross-boundary research changes.
4. **Props retirement is authoritative.** The old player-prop product is intentionally removed from active production. Scientific concepts may be reused; the implementation must not be resurrected wholesale.
5. **Branch/workflow proliferation is a known failure mode.** This program uses one active phase and one primary branch per phase/coherent block unless a specialist branch has a concrete justification.
6. **The repository already contains substantial LevLine 4, market, player-state, availability, and score-distribution research.** Phase 1 should inventory and reuse valid evidence rather than rebuilding it by default.
7. **Historical headline accuracy figures remain reference points until Phase 1 reproduces them under the exact current semantics and data universe.**

## Phase 0 commits and PR

Phase-0 branch commits:

- `7a5e969933f2239469a89ddcf9f35d81c10d333c` — initialize master plan.
- `ba360428a52705779a86a8265245d5ecc962a6b0` — add phase registry.
- `43bb03e1c94f21723539b38d8a671916971000eb` — add current-state handoff.
- `c0ff5370fd82a0c33b6ed8547ace09b812f59a2b` — add decision log.
- `44c25c8500770e9cee716139252659455c4cb30d` — add research index.

Integration:

- PR **#512** — `docs: establish spread-points nextgen research program`
- merge SHA: `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25`
- post-merge Phase-0 status commit: `dd95dcacfb7e480e73d163fa4c3c9c5179845f9a`

## Validation

### LevLine research firewall

Workflow run `35691355664`: **SUCCESS**

This validated the existing research path/import firewall without modifying or weakening it.

### LevLine research validation

Workflow run `35691355478`: **SUCCESS**

Successful jobs:

- foundation;
- v0.8 isolated regeneration;
- Phase 2 market reliance and horizon study;
- paired statistical uncertainty audit;
- margin disagreement forensics;
- research validation gate.

No production surface was intentionally changed by the Phase 0 PR.

## Key artifacts inspected

Production/governance:

- `README.md`
- `config/model.yaml`
- `src/nfl_forecast/fst_production.py`
- `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json`
- `research/fst/F-ST-01-FROZEN-2026.json`
- `docs/FST_FREEZE_PROVENANCE.md`
- `tests/test_fst_frozen_identity.py`
- `tests/test_fst_production.py`
- `tests/test_official_locking.py`
- `.github/workflows/research_validation.yml`

Current score/spread architecture:

- `src/nfl_forecast/pipeline.py`
- `src/nfl_forecast/models.py`
- `src/nfl_forecast/features.py`
- `src/nfl_forecast/public_forecast.py`
- `src/nfl_forecast/market.py`
- `src/nfl_forecast/market_t120.py`

Prior research/data:

- `research/LEVLINE_DATA_SOURCE_MATRIX.md`
- existing LevLine 4 research indexed in `RESEARCH_INDEX.md`
- existing player/personnel and availability research indexed in `RESEARCH_INDEX.md`

Retired Props:

- `docs/props/PROPS_RESEARCH_ARCHIVE_2026-09.md`
- `docs/props/README.md`
- `docs/props/RESET_MANIFEST.md`
- `archive/props-pre-revamp-2026-09-21`

## Failed approaches / cautions worth remembering

- Exact GitHub code search terms did not reliably surface several files that were present; directory/API inspection was more dependable during Phase 0.
- Do not infer current production authorization solely from the historical research F-ST registry. The packaged production artifact, active production code, and current repository contract are the direct production boundary.
- Do not equate `expected_margin` with the official public probability-implied fair spread.
- Do not rebuild old Props orchestration merely because some player-state or simulation concepts are scientifically useful.
- Do not run expensive experiments again solely because a new chat did not personally generate them.

## Unresolved questions for Phase 1

These are deliberate Phase 1 work, not Phase 0 blockers:

- exact reproducible home/away-point, margin, total, winner, ATS, and market baseline metrics under current semantics;
- full decomposition of margin/score residuals;
- exact treatment and predictive contribution of EPA, team form, QB/player state, injuries, weather, rest/travel, and market inputs;
- concept-drift evidence and optimal modern-season boundary;
- full current API/data inventory, rate limits, provenance, and point-in-time limitations;
- exact failure modes that should generate Phase 2 research hypotheses.

## Blockers

None.

# EXACT NEXT ACTION — PHASE 1 CHAT

The next chat must **not** restart the project. It must:

1. Resolve current repository `main`.
2. Read, in this order:
   - `research/spread-points-nextgen/MASTER_PLAN.md`
   - `research/spread-points-nextgen/PHASE_STATUS.md`
   - `research/spread-points-nextgen/CURRENT_STATE_AND_NEXT_STEPS.md`
   - `research/spread-points-nextgen/DECISION_LOG.md`
   - relevant sections of `research/spread-points-nextgen/RESEARCH_INDEX.md`
3. Inspect open PRs and active branches relevant to Phase 1.
4. Confirm Phase 0 is `COMPLETE` and Phase 1 is `NOT STARTED`.
5. Mark Phase 1 `IN PROGRESS` when substantive Phase 1 work actually begins.
6. Create or use **one primary Phase 1 audit branch**.
7. Begin by documenting the current architecture and reproducing the current baselines from repository evidence.
8. Perform the required error decomposition and complete API/data inventory.
9. Do **not** implement successor challengers or begin the Phase 2 literature/design program during Phase 1.
10. Before that chat finishes, update all required control/handoff files and commit the handoff.

# DO NOT REPEAT

- Do not redo Phase 0 governance setup.
- Do not recreate the canonical directory or duplicate the five control files.
- Do not re-prove from scratch that `F-ST-01-FROZEN-2026` is the active production probability strategy unless repository state materially changes.
- Do not rediscover the retired Props preservation branch; it is `archive/props-pre-revamp-2026-09-21`.
- Do not reactivate or wholesale merge retired Props code.
- Do not treat the research F-ST registry’s historical shadow status as the sole source of truth for current production.
- Do not conflate independent `expected_margin` with the probability-implied public fair spread.
- Do not rerun the Phase 0 CI merely to prove that the Phase 0 docs existed; PR #512 already passed the repository firewall and full research-validation gate.
- Do not begin Phase 2 literature review or Phase 3 challenger implementation before Phase 1 exit criteria are satisfied.
- Do not alter F-ST coefficients, official locks, historical grading, or production forecast behavior.
- Do not weaken governance or CI to accelerate the program.

## Phase 0 stop condition

**Phase 0 is complete. Phase 1 remains not started. Stop this chat here.**

# Spread & Points Next-Generation — Research Index

**Authority:** `MASTER_PLAN.md`  
**Purpose:** Make prior and future research discoverable without branch archaeology.  
**Initialized:** 2026-09-21 America/Los_Angeles

This index is a map, not an authorization mechanism. A file appearing here does not make it production-ready or scientifically authoritative beyond its stated scope.

## 1. Current production and score/spread implementation

| Area | Canonical path(s) | Why it matters |
|---|---|---|
| Main forecasting pipeline | `src/nfl_forecast/pipeline.py` | Builds historical/current games; fits winner, margin, and total models; applies frozen F-ST; emits expected margin/total and score diagnostics. |
| Regression/classification models | `src/nfl_forecast/models.py` | Contains stacked classifiers and weighted regression used by the current pipeline. |
| Matchup/team features | `src/nfl_forecast/features.py` | Builds historical matchup features, score targets, margin, total, rest, Elo, and team-form inputs. |
| Official frozen F-ST production scoring | `src/nfl_forecast/fst_production.py` | Active winner-probability production boundary and exact frozen-identity validation. |
| Packaged production artifact | `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json` | Direct production artifact; status `production_frozen`. |
| Public forecast semantics | `src/nfl_forecast/public_forecast.py` | Converts official probability to coherent probability-implied public fair margin/spread; preserves independent margin as diagnostic. |
| Market ingestion/diagnostics | `src/nfl_forecast/market.py`, `src/nfl_forecast/market_t120.py`, `src/nfl_forecast/market_diagnostics.py` | Current market probability, point-in-time market, and diagnostic support. |
| Weekly/publication flow | `scripts/run_week.py`, `scripts/refresh_market.py`, `scripts/pregame_due.py`, `scripts/verify_pregame_lock.py` | Production orchestration surfaces protected by the research firewall. |
| Repository overview | `README.md`, `IMPLEMENTATION_STATUS.md` | Current product state and implementation ledger. |

## 2. Official F-ST governance and production firewall

| Artifact | Path | Scope |
|---|---|---|
| Frozen research identity registry | `research/fst/F-ST-01-FROZEN-2026.json` | Frozen candidate identity/history. Its historical research status must not be mistaken for the current packaged production artifact. |
| Production artifact | `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json` | Current production authorization and frozen constants. |
| Freeze provenance contract | `docs/FST_FREEZE_PROVENANCE.md` | Required persistence, reconstruction, tolerance, provenance, and future candidate freeze rules. |
| Frozen identity tests | `tests/test_fst_frozen_identity.py` | Fail-closed frozen identity/reconstruction checks. |
| Production tests | `tests/test_fst_production.py` | Production F-ST behavior. |
| Official lock tests | `tests/test_official_locking.py` | Pregame immutable lock behavior. |
| Research validation/firewall workflow | `.github/workflows/research_validation.yml` | Research CI and explicit protected production surfaces. |
| Research firewall tests | `tests/test_research_firewall.py` | Research-to-production isolation contract. |

## 3. Historical accuracy and prior LevLine research

Phase 1 must verify which prior figures are directly reproducible and which are historical references.

Important existing research starting points include:

- `research/LEVLINE_4_ACCURACY_FIRST_THESIS.md`
- `research/LEVLINE_4_ACCURACY_TIEBREAKER_FINDING.md`
- `research/LEVLINE_4_CANONICAL_RESEARCH_LEDGER.md`
- `research/LEVLINE_4_CONDITIONAL_MARKET_RELIANCE_THESIS.md`
- `research/LEVLINE_4_DECISION_MEMO_2026-09-15.md`
- `research/LEVLINE_4_EVALUATION_GOVERNANCE_V2.md`
- `research/LEVLINE_4_FINAL_RESEARCH_RECOMMENDATION.md`
- `research/LEVLINE_4_LITERATURE_REVIEW.md`
- `research/LEVLINE_4_RESEARCH_SPEC.md`
- `research/LEVLINE_4_SELECTIVE_UPSET_GATE_THESIS.md`
- `research/levline3_boundary_accuracy_audit_v1.json`
- `research/levline3_chronological_accuracy_audit_v1.json`
- `research/levline3_fst_market_accuracy_audit_v1.json`

Relevant current scripts/tests include:

- `scripts/run_challenger_margin_forensics.py`
- `scripts/run_challenger_market_reliance.py`
- `scripts/run_challenger_probability_margin_bridge.py`
- `tests/test_challenger_margin_forensics.py`
- `tests/test_challenger_market_reliance.py`
- `tests/test_challenger_probability_margin_bridge.py`

**Phase 1 rule:** reuse valid prior evidence where its data universe, chronology, target, and semantics match the new question; verify rather than blindly rebuild.

## 4. Existing market research

Key surfaces:

- `src/nfl_forecast/challenger_market_incremental.py`
- `src/nfl_forecast/challenger_market_reliance.py`
- `src/nfl_forecast/challenger_market_sources.py`
- `src/nfl_forecast/challenger_probability_margin_bridge.py`
- `scripts/run_challenger_market_capture.py`
- `scripts/run_market_audit.py`
- `research/LEVLINE_4_CONDITIONAL_MARKET_RELIANCE_THESIS.md`
- `research/LEVLINE_4_EVALUATION_GOVERNANCE_V2.md`
- `research/LEVLINE_DATA_SOURCE_MATRIX.md`
- `.github/workflows/research_market_capture_v2.yml`
- `.github/workflows/research_market_horizons.yml`
- `.github/workflows/research_market_state_v1.yml`

Existing governance already distinguishes same-horizon market comparisons, prospective timestamps, market construction candidates, and market-vs-model incremental value.

## 5. Existing player/personnel state infrastructure

Potentially reusable scientific/infrastructure surfaces include:

- `src/nfl_forecast/advanced_player_context.py`
- `src/nfl_forecast/injuries.py`
- `src/nfl_forecast/personnel_impact.py`
- `src/nfl_forecast/player_impact_engine.py`
- `src/nfl_forecast/player_impact_cards.py`
- `src/nfl_forecast/player_impact_monitor.py`
- `src/nfl_forecast/player_state_research.py`
- `src/nfl_forecast/career_qb_context.py`
- `src/nfl_forecast/qb_history.py`
- `research/availability/`
- `research/depth_chart_state_contract_v1.json`
- `research/depth_chart_state_v1.py`
- `research/expected_lineup_qb_capture_v1_contract.json`
- `research/expected_lineup_state_v1.py`
- `research/injury_snapshot_archive_contract_v1.json`
- `research/injury_snapshot_archive_v1.py`

These are inputs for Phase 1 inventory and possible Phase 2 hypotheses. Their existence does **not** authorize them as successor-model features.

## 6. Data/API/source governance

Canonical current source inventory starting point:

- `research/LEVLINE_DATA_SOURCE_MATRIX.md`
- `research/data_source_governance.json`
- `research/advanced_player_source_governance.json`
- `research/free_only_policy.json`
- `config/model.yaml`
- `src/nfl_forecast/data.py`
- `src/nfl_forecast/source_policy.py`

The existing matrix currently discusses, among others:

- nflverse game/schedule data;
- The Odds API prospective multi-book research data;
- constituent sportsbook feeds through aggregators;
- prediction-exchange candidates;
- historical/prospective injury and availability sources;
- the verified 2026-only Sleeper archive;
- official NFL availability sources;
- paid candidates held inactive under the $0 policy;
- advanced-player sources such as FTN/nflverse-derived data where technically qualified.

Phase 1 must create a complete, current API/data inventory rather than assuming this matrix is exhaustive or current enough for the new program.

## 7. Retired Props research archive

**Do not reactivate wholesale.**

Canonical active-repository references:

- `docs/props/PROPS_RESEARCH_ARCHIVE_2026-09.md`
- `docs/props/README.md`
- `docs/props/RESET_MANIFEST.md`

Full preservation branch:

- `archive/props-pre-revamp-2026-09-21`

Reusable ideas include:

- point-in-time player availability;
- QB starter/replacement state;
- role/workload modeling;
- opportunity decomposition;
- player uncertainty;
- market benchmarking;
- coherent simulation;
- timestamped source provenance;
- immutable forecast receipts;
- append-outcomes-later grading.

The old production/live orchestration, Props-specific workflow sprawl, and monolithic evidence patterns are explicitly non-targets.

## 8. Existing joint-distribution / score-related research

Potentially relevant starting points:

- `src/nfl_forecast/challenger_joint_distribution.py`
- `.github/workflows/research_phase3_joint_distribution.yml`
- `.github/workflows/research_phase3b_probability_margin_bridge.yml`
- `src/nfl_forecast/challenger_probability_margin_bridge.py`

Phase 1 must identify exactly what these artifacts did, their data universe, whether they remain reproducible, and whether they answer the new scoring/margin question.

## 9. Future program artifacts

As phases advance, add canonical links here rather than forcing future chats to search the entire repository.

### Phase 1 — complete

- current architecture report — `research/spread-points-nextgen/phase1/CURRENT_ARCHITECTURE_AUDIT.md`
- reproducible baseline report — `research/spread-points-nextgen/phase1/BASELINE_REPRODUCTION_REPORT.md`
- error-decomposition report — `research/spread-points-nextgen/phase1/ERROR_DECOMPOSITION_REPORT.md`
- data/API inventory — `research/spread-points-nextgen/phase1/DATA_API_INVENTORY.md`
- leakage/PIT risk register — `research/spread-points-nextgen/phase1/LEAKAGE_PIT_AUDIT.md`

Additional Phase 1 control/evidence:

- evaluation contract — `research/spread-points-nextgen/phase1/EVALUATION_CONTRACT.md`
- synthesis / Phase 2 hypotheses — `research/spread-points-nextgen/phase1/PHASE1_SYNTHESIS.md`
- machine-readable summary — `research/spread-points-nextgen/phase1/PHASE1_SUMMARY.json`
- reproducible runner — `research/spread-points-nextgen/phase1/run_baseline_audit.py`
- structural diagnostic runner — `research/spread-points-nextgen/phase1/run_structural_slices.py`
- helper tests — `research/spread-points-nextgen/phase1/test_run_baseline_audit.py`
- final post-sync exact-head validation — firewall `35741337735`; research validation `35741337942`; Phase 1 audit `35741337832`
- final dedicated audit artifact — `10699778876`, digest `sha256:c85bc49458631c6f9b9a14e0a21f1eb213b527017e20ddcc125e9e23b484e0e1`
- PR #513 — merged at `a4f7172c0c4ff82b1689411181e7a9042a1628a8`

External comparator explicitly carried into Phase 2: **davidsasser.com**.

### Phase 2 — closeout candidate / exact-head CI pending

- literature review — `research/spread-points-nextgen/phase2/LITERATURE_REVIEW.md`
- external-model review — `research/spread-points-nextgen/phase2/EXTERNAL_MODEL_REVIEW.md`
- challenger design/preregistration — `research/spread-points-nextgen/phase2/CHALLENGER_PREREGISTRATION.md`
- feature/player policy — `research/spread-points-nextgen/phase2/FEATURE_HYPOTHESES_AND_PLAYER_POLICY.md`
- market-residual specification — `research/spread-points-nextgen/phase2/MARKET_RESIDUAL_SPECIFICATION.md`
- frozen evaluation/holdout protocol — `research/spread-points-nextgen/phase2/EVALUATION_HOLDOUT_PROTOCOL.md`
- data/source-gap report — `research/spread-points-nextgen/phase2/DATA_GAPS_AND_SOURCE_POLICY.md`
- paid-data decision — `research/spread-points-nextgen/phase2/PAID_DATA_DECISION.md`
- synthesis / Phase 3 handoff — `research/spread-points-nextgen/phase2/PHASE2_SYNTHESIS.md`
- machine-readable design summary — `research/spread-points-nextgen/phase2/PHASE2_RESEARCH_SUMMARY.json`
- bounded implementation/search-space contract — `research/spread-points-nextgen/phase2/BOUNDED_IMPLEMENTATION_SPEC.md`
- red-team closeout is recorded in `phase2/PHASE2_SYNTHESIS.md`
- deterministic nested-fold contract is recorded in `phase2/EVALUATION_HOLDOUT_PROTOCOL.md`
- feature/source/PIT feasibility matrix is recorded in `phase2/DATA_GAPS_AND_SOURCE_POLICY.md`
- Challenger C M0/M1/M2/M3 null hierarchy is recorded in `phase2/MARKET_RESIDUAL_SPECIFICATION.md`
- evidence-quality ledger and final publisher/technical-source verification are recorded in `phase2/LITERATURE_REVIEW.md`
- normalized external-system audit and required four-way Sasser classification are recorded in `phase2/EXTERNAL_MODEL_REVIEW.md`

External systems explicitly reviewed include davidsasser.com, nfelo, Open Source Football/nflverse and score/drive-process research. Final Sasser search found useful score/line/market product separation but no reproducible current methodology/archive sufficient for scientific validation.

Compatibility sync #521 merged concurrent adaptive-weekly-learning main state into the Phase 2 branch. After main advanced again, compatibility sync #528 preserved Sunday Signal contextual output refresh commit `032289d5b62b226b242e4b4c202935f7fb0ef61a`. Neither concurrent workstream was used to select Spread & Points challengers.

### Phase 3 — planned

- challenger registry — TBD
- feature/provenance contracts — TBD
- implementation/test index — TBD

### Phase 4 — planned

- frozen historical validation report — TBD
- holdout report — TBD
- ablation report — TBD
- statistical uncertainty report — TBD

### Phase 5 — planned

- prospective receipt index — TBD
- prospective grading report — TBD
- operational-hardening report — TBD

### Phase 6 — planned

- final synthesis — TBD
- promotion package — TBD
- migration/rollback plan — TBD
- monitoring plan — TBD

## 10. Index maintenance rule

Every substantive future chat must update this file when it creates a durable artifact that another chat should be able to find without broad repository search.

Do not add every temporary output. Index the smallest set of artifacts needed to reconstruct decisions, reproduce evidence, and continue the program safely.